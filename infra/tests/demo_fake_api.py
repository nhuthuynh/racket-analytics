"""A loopback fake of the public HTTP API that `make demo` uses, for the ST-064 plan step.

It answers only the routes scripts/demo/seed_demo.py calls when Ivy already has a complete demo
match (the MVP-03 reuse path), plus ``GET``/``POST /me/plan`` as api-sprint-04 §2 says: ``GET``
is 200 with the current plan or 404 ``no_plan``; ``POST`` is 201 with a new plan id, or the
409 code a test sets in ``refuse_plan``. Every request is recorded with its JSON body, so a test
can count the plans generated and check the preferences sent. Anything else is 404.
"""

from __future__ import annotations

import http.server
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

MATCH_ID = "m-demo-1"
DEMO_MATCH = {"id": MATCH_ID, "title": "Demo match", "status": "video_received"}
METRICS = {"winners": {"A": {"n": 4}, "B": {"n": 3}}}


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
        routes: dict[tuple[str, str], Any] = {
            ("GET", "/api/dev/users"): (200, {"items": [{"username": "ivy"}]}),
            ("POST", "/api/dev/sign-in"): (204, None),
            ("GET", "/api/matches?limit=50"): (200, {"items": [DEMO_MATCH]}),
            ("GET", f"/api/matches/{MATCH_ID}/score-sheet"): (200, {"rows": [{}] * 12}),
            ("GET", f"/api/matches/{MATCH_ID}/stats"): (200, {"metrics": METRICS}),
        }
        if (method, path) in routes:
            return routes[(method, path)]
        if not self.plan_api:
            return 404, _error("not_found")
        if (method, path) == ("GET", "/api/me/plan"):
            return (200, self.plans[-1]) if self.plans else (404, _error("no_plan"))
        if (method, path) == ("POST", "/api/me/plan"):
            if self.refuse_plan:
                return 409, _error(self.refuse_plan)
            self.plans.append({"id": f"plan-{len(self.plans) + 1}", "preferences": body})
            return 201, self.plans[-1]
        return 404, _error("not_found")


def _error(code: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": code}}


@contextmanager
def fake_api() -> Iterator[FakeApi]:
    fake = FakeApi()

    class Handler(http.server.BaseHTTPRequestHandler):
        def _answer(self) -> None:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            body = json.loads(raw) if raw else None
            fake.requests.append((self.command, self.path, body))
            status, reply = fake.answer(self.command, self.path, body)
            data = b"" if reply is None else json.dumps(reply).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = do_PATCH = _answer

        def log_message(self, *_: object) -> None:
            return

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    fake.url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield fake
    finally:
        server.shutdown()
        server.server_close()
