"""BE-GR1-01: `livehttp.mailpit_token` never hands back a sign-in link it already returned.

G03-01 step 8 signs in a second time with the same address after `DELETE /me`. Mailpit's search
lists the newest message first, and the second email arrives about 1 s after the request, so a
read at once returns the first (spent) link and the exchange is refused. The helper must wait for
a message it has not returned before (fail closed: None when no new one arrives in time).

A fake Mailpit on 127.0.0.1 serves `/api/v1/search` and `/api/v1/message/{id}`.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit

MEASURE = SCRIPTS_DIR / "measure"
if str(MEASURE) not in sys.path:
    sys.path.insert(0, str(MEASURE))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, MEASURE / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lh = _load("livehttp")

# 43-character tokens, the shape `measurelib.SIGN_IN_TOKEN` reads from a real link.
TOK_A, TOK_B, TOK_C, TOK_D = ("a" * 43, "b" * 43, "c" * 43, "d" * 43)


class FakeMailpit:
    """Messages per address, newest first, as Mailpit's search answers."""

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []
        self.lock = threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_: Any) -> None:
                return

            def _send(self, body: Any) -> None:
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self) -> None:  # noqa: N802
                with outer.lock:
                    msgs = list(outer.messages)
                if self.path.startswith("/api/v1/search"):
                    self._send({"messages": [{"ID": m["ID"]} for m in reversed(msgs)]})
                    return
                mid = self.path.rsplit("/", 1)[-1]
                for m in msgs:
                    if m["ID"] == mid:
                        self._send({"Text": m["Text"], "HTML": ""})
                        return
                self.send_error(404)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def deliver(self, token: str) -> None:
        with self.lock:
            n = len(self.messages) + 1
            self.messages.append(
                {"ID": f"m{n}", "Text": f"Sign in: https://x/auth/callback#token={token}\n"}
            )

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def mailpit():
    fake = FakeMailpit()
    yield fake
    fake.close()


def test_a_spent_link_is_not_returned_again(mailpit: FakeMailpit) -> None:
    address = "be-gr1-01-a@example.com"
    mailpit.deliver(TOK_A)
    assert lh.mailpit_token(mailpit.url, address, timeout_s=2) == TOK_A
    # No new mail: the old link must not come back (fail closed).
    assert lh.mailpit_token(mailpit.url, address, timeout_s=0.6) is None


def test_the_second_sign_in_waits_for_the_new_mail(mailpit: FakeMailpit) -> None:
    address = "be-gr1-01-b@example.com"
    mailpit.deliver(TOK_B)
    assert lh.mailpit_token(mailpit.url, address, timeout_s=2) == TOK_B
    timer = threading.Timer(0.8, mailpit.deliver, args=(TOK_C,))
    timer.start()
    t0 = time.monotonic()
    try:
        got = lh.mailpit_token(mailpit.url, address, timeout_s=5)
    finally:
        timer.cancel()
    assert got == TOK_C
    assert time.monotonic() - t0 >= 0.7


def test_the_first_sign_in_still_reads_the_newest_mail(mailpit: FakeMailpit) -> None:
    address = "be-gr1-01-c@example.com"
    mailpit.deliver(TOK_D)
    assert lh.mailpit_token(mailpit.url, address, timeout_s=2) == TOK_D
