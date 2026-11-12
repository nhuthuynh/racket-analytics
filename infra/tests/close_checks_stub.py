"""A local stand-in for the two GitHub REST endpoints the Sprint 5 close checks read
(EM-CLOSE-CHECKS, PRC-6.1-6.3): `pulls?state=all` and `issues/{n}`. Real HTTP on 127.0.0.1.
It pages with `?page=N` (two items a page, an empty page past the end) and sends no `Link`
header, as `flow_stub.py` does (the agent proxy refuses GitHub's `repositories/{id}` Link
form). Every request is recorded so a test can assert that only REST paths under `/repos/`
were read.
"""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

REPO = "nhuthuynh/racket-analytics"


def pr(
    number: int,
    ticket: str,
    *,
    merged: bool = True,
    state: str | None = None,
    base: str = "main",
    head: str | None = None,
) -> dict[str, Any]:
    """A pull request as `GET /repos/{repo}/pulls` lists it (only the fields the checks read)."""
    st = state or ("closed" if merged else "open")
    return {
        "number": number,
        "title": f"[{ticket}] work",
        "state": st,
        "merged_at": "2026-11-12T10:00:00Z" if merged else None,
        "base": {"ref": base},
        "head": {"ref": head or f"s05/{ticket.lower()}-work"},
    }


@dataclass
class CloseStub:
    pulls: list[dict[str, Any]] = field(default_factory=list)
    issues: dict[int, str] = field(default_factory=dict)  # number -> "open" | "closed"
    page_size: int = 2
    fail_status: int | None = None
    requests: list[str] = field(default_factory=list)
    url: str = ""


def _handler(stub: CloseStub) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

        def do_POST(self) -> None:  # GraphQL would be a POST; never allowed here
            stub.requests.append(f"POST {self.path}")
            self._send({"message": "GraphQL is not served by this stub"}, 403)

        def do_GET(self) -> None:
            parts = urlsplit(self.path)
            query = parse_qs(parts.query)
            stub.requests.append(self.path)
            if stub.fail_status:
                return self._send({"message": "boom"}, stub.fail_status)
            base = f"/repos/{REPO}"
            if parts.path == f"{base}/pulls":
                state = query.get("state", ["open"])[0]
                items = [p for p in stub.pulls if state == "all" or p["state"] == state]
                page = int(query.get("page", ["1"])[0])
                start = (page - 1) * stub.page_size
                return self._send(items[start : start + stub.page_size])
            m = re.fullmatch(rf"{base}/issues/(\d+)", parts.path)
            if m and int(m.group(1)) in stub.issues:
                n = int(m.group(1))
                return self._send({"number": n, "state": stub.issues[n]})
            self._send({"message": "Not Found"}, 404)

        def _send(self, body: object, status: int = 200) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


@contextmanager
def serve(stub: CloseStub) -> Iterator[CloseStub]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(stub))
    stub.url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield stub
    finally:
        server.shutdown()
        server.server_close()
