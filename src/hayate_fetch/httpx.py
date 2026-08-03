"""Optional HTTPX backend for pooled asynchronous CPython requests."""

from __future__ import annotations

import httpx
from hayate import Headers, Request, Response


class HttpxBackend:
    """Use an application-owned ``httpx.AsyncClient`` as a Fetch backend.

    The caller owns the client lifecycle, connection limits, timeouts, TLS,
    proxies, and optional HTTP/2 configuration. Responses remain buffered to
    preserve the public hayate-fetch 0.1 contract.
    """

    def __init__(self, client: httpx.AsyncClient, *, redirect: str = "follow") -> None:
        if redirect not in ("follow", "manual"):
            raise ValueError("redirect must be 'follow' or 'manual'")
        self.client = client
        self.redirect = redirect

    async def send(self, request: Request) -> Response:
        body = await request.bytes() if request.method not in ("GET", "HEAD") else None
        try:
            raw = await self.client.request(
                request.method,
                request.url.href,
                headers=list(request.headers),
                content=body if body else None,
                follow_redirects=self.redirect == "follow",
            )
        except httpx.HTTPError as error:
            raise OSError(str(error)) from error

        return Response(
            raw.content,
            status=raw.status_code,
            headers=Headers(raw.headers.multi_items()),
        )


__all__ = ["HttpxBackend"]
