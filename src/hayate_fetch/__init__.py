"""hayate-fetch: client-side WHATWG fetch on hayate's Request/Response."""

from __future__ import annotations

from typing import Any

from hayate import Request, Response

from .backends import FetchBackend, UrllibBackend, WorkersBackend, default_backend

__version__ = "0.1.3"

__all__ = [
    "FetchBackend",
    "UrllibBackend",
    "WorkersBackend",
    "__version__",
    "default_backend",
    "fetch",
]

_default: FetchBackend | None = None


async def fetch(
    input: str | Request,
    *,
    method: str = "GET",
    headers: Any = None,
    body: Any = None,
    backend: FetchBackend | None = None,
) -> Response:
    """WHATWG-shaped fetch: pass a URL (plus init) or a prebuilt Request.

    HTTP error statuses resolve to a Response; network failures raise
    OSError. The documented subset excludes browser-only init fields
    (mode / credentials / cache — DESIGN §2).
    """
    request = (
        input
        if isinstance(input, Request)
        else Request(input, method=method, headers=headers, body=body)
    )
    global _default
    if backend is None:
        if _default is None:
            _default = default_backend()
        backend = _default
    return await backend.send(request)
