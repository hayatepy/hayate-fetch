"""fetch() against a real local HTTP server (stdlib ThreadingHTTPServer)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from hayate_fetch import UrllibBackend, WorkersBackend, default_backend, fetch


class EchoHandler(BaseHTTPRequestHandler):
    def _reply(self) -> None:
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("location", "/target")
            self.end_headers()
            return
        if self.path in ("/redirect-303", "/redirect-307", "/redirect-308"):
            length = int(self.headers.get("content-length") or 0)
            if length:
                self.rfile.read(length)
            self.send_response(int(self.path.rsplit("-", 1)[1]))
            self.send_header("location", "/target")
            self.end_headers()
            return
        length = int(self.headers.get("content-length") or 0)
        if self.path == "/bytes":
            data = self.rfile.read(length)
            self.send_response(200)
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        payload = {
            "method": self.command,
            "path": self.path,
            "echo": self.rfile.read(length).decode() if length else None,
            "header": self.headers.get("x-probe"),
            "authorization": self.headers.get("authorization"),
        }
        status = 404 if self.path == "/missing" else 200
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = _reply

    def log_message(self, *args) -> None:  # keep pytest output clean
        pass


@pytest.fixture(scope="module")
def base_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), EchoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


async def test_get_json(base_url):
    res = await fetch(f"{base_url}/hello")
    assert res.status == 200
    data = await res.json()
    assert data["method"] == "GET" and data["path"] == "/hello"


async def test_post_body_and_headers(base_url):
    res = await fetch(
        f"{base_url}/submit",
        method="POST",
        headers={"x-probe": "42", "content-type": "text/plain"},
        body="payload",
    )
    data = await res.json()
    assert data == {
        "method": "POST",
        "path": "/submit",
        "echo": "payload",
        "header": "42",
        "authorization": None,
    }


async def test_error_status_is_a_response_not_an_exception(base_url):
    res = await fetch(f"{base_url}/missing")
    assert res.status == 404
    assert (await res.json())["path"] == "/missing"


async def test_redirects_follow_by_default(base_url):
    res = await fetch(f"{base_url}/redirect")
    assert res.status == 200
    assert (await res.json())["path"] == "/target"


async def test_manual_redirect_surfaces_the_302(base_url):
    res = await fetch(f"{base_url}/redirect", backend=UrllibBackend(redirect="manual"))
    assert res.status == 302
    assert res.headers.get("location") == "/target"


async def test_prebuilt_request_object(base_url):
    from hayate import Request

    res = await fetch(Request(f"{base_url}/prebuilt", method="PUT", body="x"))
    data = await res.json()
    assert data["method"] == "PUT" and data["echo"] == "x"


async def test_network_failure_raises_oserror():
    with pytest.raises(OSError):
        await fetch("http://127.0.0.1:1/unreachable")


def test_redirect_policy_is_validated_consistently_across_backends():
    assert isinstance(default_backend(redirect="manual"), UrllibBackend)
    assert default_backend(redirect="manual").redirect == "manual"
    assert WorkersBackend(redirect="manual").redirect == "manual"
    with pytest.raises(ValueError, match="redirect"):
        WorkersBackend(redirect="unsafe")


@pytest.mark.parametrize("status", [307, 308])
async def test_redirects_preserve_method_and_body_for_307_and_308(base_url, status):
    res = await fetch(f"{base_url}/redirect-{status}", method="PUT", body="preserved")
    data = await res.json()
    assert data["method"] == "PUT"
    assert data["path"] == "/target"
    assert data["echo"] == "preserved"


async def test_303_redirect_switches_non_get_to_get(base_url):
    res = await fetch(f"{base_url}/redirect-303", method="PATCH", body="discarded")
    data = await res.json()
    assert data["method"] == "GET"
    assert data["path"] == "/target"
    assert data["echo"] is None


async def test_cross_origin_redirect_drops_authorization_header(base_url):
    target = ThreadingHTTPServer(("127.0.0.1", 0), EchoHandler)
    target_thread = threading.Thread(target=target.serve_forever, daemon=True)
    target_thread.start()
    target_url = f"http://127.0.0.1:{target.server_address[1]}/target"

    class CrossOriginRedirect(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302)
            self.send_header("location", target_url)
            self.end_headers()

        def log_message(self, *args):
            pass

    source = ThreadingHTTPServer(("127.0.0.1", 0), CrossOriginRedirect)
    source_thread = threading.Thread(target=source.serve_forever, daemon=True)
    source_thread.start()
    try:
        response = await fetch(
            f"http://127.0.0.1:{source.server_address[1]}/redirect",
            headers={"authorization": "Bearer must-not-leak"},
        )
        assert (await response.json())["authorization"] is None
    finally:
        source.shutdown()
        target.shutdown()
