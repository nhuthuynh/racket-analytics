"""A loopback fake of the public API `make demo` uses (ST-064): the MVP-03 reuse path (Ivy has a
complete demo match) and ``GET``/``POST /me/plan`` as api-sprint-04 §2 (200 / 404 ``no_plan``;
201 / 409). Every request is recorded with its JSON body; anything else is 404."""

from __future__ import annotations

import http.server
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

MATCH = "/api/matches/m-demo-1"
ROUTES: dict[tuple[str, str], tuple[int, Any]] = {
    ("GET", "/api/dev/users"): (200, {"items": [{"username": "ivy"}]}),
    ("POST", "/api/dev/sign-in"): (204, None),
    ("GET", "/api/matches?limit=50"): (
        200, {"items": [{"id": "m-demo-1", "title": "Demo match", "status": "video_received"}]}),
    ("GET", f"{MATCH}/score-sheet"): (200, {"rows": [{}] * 12}),
    ("GET", f"{MATCH}/stats"): (200, {"metrics": {"winners": {"A": {"n": 4}, "B": {"n": 3}}}}),
}  # fmt: skip


def _error(code: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": code}}


@dataclass
class FakeApi:
    url: str = ""
    refuse_plan: str | None = None  # a 409 code for POST /me/plan, e.g. "no_plan_fits"
    plan_api: bool = True  # False: a stack older than ST-061b, /me/plan is a plain 404
    plans: list[dict[str, Any]] = field(default_factory=list)  # generated, newest last
    requests: list[tuple[str, str, Any]] = field(default_factory=list)  # method, path, body

    def plan_posts(self) -> list[Any]:
        return [b for m, path, b in self.requests if (m, path) == ("POST", "/api/me/plan")]

    def answer(self, method: str, path: str, body: Any) -> tuple[int, Any]:
        if (method, path) in ROUTES:
            return ROUTES[(method, path)]
        if not self.plan_api or path != "/api/me/plan":
            return 404, _error("not_found")
        if method == "GET":
            return (200, self.plans[-1]) if self.plans else (404, _error("no_plan"))
        if self.refuse_plan:
            return 409, _error(self.refuse_plan)
        self.plans.append({"id": f"plan-{len(self.plans) + 1}", "preferences": body})
        return 201, self.plans[-1]


@contextmanager
def fake_api() -> Iterator[FakeApi]:
    fake = FakeApi()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length)) if length else None
            fake.requests.append((self.command, self.path, body))
            status, reply = fake.answer(self.command, self.path, body)
            data = b"" if reply is None else json.dumps(reply).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_POST = do_GET

        def log_message(self, *_: object) -> None:
            return

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    fake.url = f"http://127.0.0.1:{server.server_address[1]}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield fake
    finally:
        server.shutdown()
        server.server_close()
