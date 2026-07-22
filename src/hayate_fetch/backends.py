"""The two bundled FetchBackends (DESIGN §3).

CPython: stdlib urllib pushed off-loop. Workers: passthrough to the JS
global fetch (a subrequest — the platform's one true client). Both consume
and produce hayate's WHATWG Request/Response, so callers never see the seam.
"""

from __future__ import annotations

import asyncio
import sys
import urllib.error
import urllib.request
from typing import Any, Protocol

from hayate import Headers, Request, Response


class FetchBackend(Protocol):
    async def send(self, request: Request) -> Response: ...


class UrllibBackend:
    """stdlib-only backend: ``urllib.request`` + ``asyncio.to_thread``.

    Fetch semantics: HTTP error statuses come back as Responses, not
    exceptions; only network/protocol failures raise (OSError). Responses
    are buffered (DESIGN §3, the v0.1 contract).
    """

    def __init__(self, *, timeout: float = 30.0, redirect: str = "follow") -> None:
        if redirect not in ("follow", "manual"):
            raise ValueError("redirect must be 'follow' or 'manual'")
        self.timeout = timeout
        self.redirect = redirect

    async def send(self, request: Request) -> Response:
        body = await request.bytes() if request.method not in ("GET", "HEAD") else None
        headers = list(request.headers)
        url = request.url.href
        method = request.method

        def run() -> tuple[int, list[tuple[str, str]], bytes]:
            raw = urllib.request.Request(url, data=body or None, method=method)
            for name, value in headers:
                raw.add_header(name, value)
            opener = self._opener()
            try:
                with opener.open(raw, timeout=self.timeout) as res:
                    return res.status, list(res.headers.items()), res.read()
            except urllib.error.HTTPError as error:
                # An HTTP response, just not a 2xx: still a Response.
                return error.code, list(error.headers.items()), error.read()

        status, header_items, data = await asyncio.to_thread(run)
        return Response(data, status=status, headers=Headers(header_items))

    def _opener(self) -> urllib.request.OpenerDirector:
        if self.redirect == "manual":
            return urllib.request.build_opener(_NoRedirect)
        return urllib.request.build_opener()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


class WorkersBackend:
    """Cloudflare Workers backend: the JS global ``fetch`` (a subrequest)."""

    async def send(self, request: Request) -> Response:
        import js
        from pyodide.ffi import to_js

        options: dict[str, Any] = {
            "method": request.method,
            "headers": list(request.headers),
        }
        if request.method not in ("GET", "HEAD"):
            body = await request.bytes()
            if body:
                options["body"] = to_js(body)
        js_response = await js.fetch(
            request.url.href, to_js(options, dict_converter=js.Object.fromEntries)
        )
        buffer = await js_response.arrayBuffer()
        data = bytes(js.Uint8Array.new(buffer).to_py())
        headers = Headers([(k, v) for k, v in js_response.headers.entries()])
        return Response(data, status=int(js_response.status), headers=headers)


def default_backend() -> FetchBackend:
    if sys.platform == "emscripten":
        return WorkersBackend()
    return UrllibBackend()
