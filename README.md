# hayate-fetch

Client-side WHATWG fetch for [hayate](https://github.com/hayatepy/hayate):
the same Request/Response types your server handles, pointed outward.

> **Status: alpha (0.1.x), typed.** `fetch()`, the `FetchBackend` protocol, and the
> CPython and Cloudflare Workers backends are implemented and used by
> hayate-auth for OAuth token exchange. The design memo (Japanese, per project
> convention) lives in [DESIGN.md](DESIGN.md); release history is in
> [CHANGELOG.md](CHANGELOG.md).

## Install

```sh
uv add hayate-fetch        # or: pip install hayate-fetch
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
Responses are buffered in the public 0.1 contract. Redirects follow by default,
or use `UrllibBackend(redirect="manual")` to surface the redirect response.

## Backends

- **CPython:** `UrllibBackend` uses the standard library through
  `asyncio.to_thread`, so the package adds no HTTP dependency.
- **Cloudflare Workers:** `WorkersBackend` passes through to the platform's
  JavaScript `fetch`.
- **Custom clients:** implement the async `FetchBackend.send(Request) ->
  Response` protocol and pass it as `backend=`.

The default backend is selected from the runtime. Browser-only Fetch fields
such as `mode`, `credentials`, and `cache` are intentionally outside the
server-side subset.

## License

MIT
