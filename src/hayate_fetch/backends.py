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
from importlib import import_module
from typing import Any, Protocol
from urllib.parse import urlsplit

from hayate import Headers, Request, Response


class FetchBackend(Protocol):
    async def send(self, request: Request) -> Response: ...


class UrllibBackend:
    """stdlib-only backend: ``urllib.request`` + ``asyncio.to_thread``.

    Fetch semantics: HTTP error statuses come back as Responses, not
    exceptions; only network/protocol failures raise (OSError). Responses
    are buffered (DESIGN §3, the current public contract).
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
        return urllib.request.build_opener(_FetchRedirect)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


class _FetchRedirect(urllib.request.HTTPRedirectHandler):
    """Fetch-compatible redirect methods without cross-origin credential leaks."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request:
        method = req.get_method()
        redirected_method = method
        data = req.data
        drop_body = code == 303 and method not in ("GET", "HEAD")
        drop_body = drop_body or (code in (301, 302) and method == "POST")
        if drop_body:
            redirected_method = "GET"
            data = None

        copied_headers = {
            name: value
            for name, value in req.headers.items()
            if name.lower() != "host"
            and (
                not drop_body
                or name.lower() not in ("content-encoding", "content-length", "content-type")
            )
        }
        if _origin(req.full_url) != _origin(newurl):
            copied_headers = {
                name: value
                for name, value in copied_headers.items()
                if name.lower() not in ("authorization", "cookie", "proxy-authorization")
            }

        return urllib.request.Request(
            newurl.replace(" ", "%20"),
            data=data,
            headers=copied_headers,
            method=redirected_method,
            origin_req_host=req.origin_req_host,
            unverifiable=True,
        )


def _origin(url: str) -> tuple[str, str | None, int | None]:
    parsed = urlsplit(url)
    default_port = 443 if parsed.scheme.lower() == "https" else 80
    return parsed.scheme.lower(), parsed.hostname, parsed.port or default_port


class WorkersBackend:
    """Cloudflare Workers backend: the JS global ``fetch`` (a subrequest)."""

    def __init__(self, *, redirect: str = "follow") -> None:
        if redirect not in ("follow", "manual"):
            raise ValueError("redirect must be 'follow' or 'manual'")
        self.redirect = redirect

    async def send(self, request: Request) -> Response:
        js = import_module("js")
        to_js = import_module("pyodide.ffi").to_js

        options: dict[str, Any] = {
            "method": request.method,
            "headers": list(request.headers),
            "redirect": self.redirect,
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


def default_backend(*, redirect: str = "follow") -> FetchBackend:
    if sys.platform == "emscripten":
        return WorkersBackend(redirect=redirect)
    return UrllibBackend(redirect=redirect)
