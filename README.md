# hayate-fetch

> **Hayate ecosystem:** [Start here](https://hayatepy.dev/)
> · [Production golden app](https://github.com/hayatepy/golden-app)
> · [Tested compatibility](https://hayatepy.dev/evidence/compatibility/)

Client-side WHATWG fetch for [hayate](https://github.com/hayatepy/hayate):
the same Request/Response types your server handles, pointed outward.

> **Status: alpha (0.x), typed.** `fetch()`, the `FetchBackend` protocol, and the
> CPython and Cloudflare Workers backends are implemented and used by
> hayate-auth for OAuth token exchange. The design memo (Japanese, per project
> convention) lives in [DESIGN.md](DESIGN.md); release history is in
> [CHANGELOG.md](CHANGELOG.md).

## Install

```sh
uv add hayate-fetch        # or: pip install hayate-fetch
```

For pooled asynchronous CPython requests, install the optional HTTPX backend:

```sh
uv add "hayate-fetch[httpx]"
```

## Use

```python
from hayate_fetch import fetch

response = await fetch(
    "https://api.example.com/books",
    method="POST",
    headers={"content-type": "application/json"},
    body='{"title":"Standards first"}',
)

if response.ok:
    book = await response.json()
```

Pass a prebuilt hayate `Request` when that is already the natural object:

```python
from hayate import Request
from hayate_fetch import fetch

response = await fetch(Request("https://api.example.com/health"))
```

HTTP error statuses resolve to a `Response`; network failures raise `OSError`.
Responses are buffered in the current public contract. Redirects follow by default,
or pass `default_backend(redirect="manual")` to surface redirects consistently
on CPython and Workers.

## Backends

- **CPython:** `UrllibBackend` uses the standard library through
  `asyncio.to_thread`, so the package adds no HTTP dependency.
- **Cloudflare Workers:** `WorkersBackend` passes through to the platform's
  JavaScript `fetch`.
- **HTTPX (optional, CPython):** `HttpxBackend` adapts an application-owned
  `httpx.AsyncClient`, preserving its connection pool, timeout, TLS, proxy,
  and optional HTTP/2 configuration.
- **Custom clients:** implement the async `FetchBackend.send(Request) ->
  Response` protocol and pass it as `backend=`.

Keep one HTTPX client for the application lifetime rather than constructing it
inside a hot request loop:

```python
import httpx

from hayate_fetch import fetch
from hayate_fetch.httpx import HttpxBackend

async with httpx.AsyncClient() as client:
    response = await fetch(
        "https://api.example.com/books",
        backend=HttpxBackend(client),
    )
```

The default backend is selected from the runtime. Browser-only Fetch fields
such as `mode`, `credentials`, and `cache` are intentionally outside the
server-side subset.

## License

MIT
