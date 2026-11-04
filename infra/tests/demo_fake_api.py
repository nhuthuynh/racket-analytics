"""A loopback fake of the public API `make demo` uses (ST-064): the MVP-03 reuse path (Ivy has a
complete demo match) and ``GET``/``POST /me/plan`` as api-sprint-04 §2 (200 / 404 ``no_plan``;
201 / 409). Every request is recorded with its JSON body; anything else is 404.

With ``age_gate`` on (QA-VERIFY04R5-01; FR-003, api-sprint-04 §4), every route but the dev
sign-in answers 403 ``age_confirmation_required`` until ``POST /me/age-confirmation`` with
``{"is_adult": true}``; with it off that route is 404, as on the real API."""

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
    ("GET", "/api/me"): (200, {"id": "u-ivy", "display_name": "Ivy"}),
    ("GET", "/api/matches?limit=50"): (
        200, {"items": [{"id": "m-demo-1", "title": "Demo match", "status": "video_received"}]}),
    ("GET", f"{MATCH}/score-sheet"): (200, {"rows": [{}] * 12}),
    ("GET", f"{MATCH}/stats"): (200, {"metrics": {"winners": {"A": {"n": 4}, "B": {"n": 3}}}}),
}  # fmt: skip
AGE_CONFIRMATION = "/api/me/age-confirmation"
UNGATED = frozenset({"/api/dev/users", "/api/dev/sign-in", AGE_CONFIRMATION})


def _error(code: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": code}}


@dataclass
class FakeApi:
    url: str = ""
    refuse_plan: str | None = None  # a 409 code for POST /me/plan, e.g. "no_plan_fits"
    plan_api: bool = True  # False: a stack older than ST-061b, /me/plan is a plain 404
    plans: list[dict[str, Any]] = field(default_factory=list)  # generated, newest last
    requests: list[tuple[str, str, Any]] = field(default_factory=list)  # method, path, body
    age_gate: bool = False  # FEATURE_AGE_GATE on: 403 until Ivy answers the age question
    age_confirmed_at: str | None = None
    refuse_age: str | None = None  # a 403 code for POST /me/age-confirmation, e.g. "under_age"

    def plan_posts(self) -> list[Any]:
        return [b for m, path, b in self.requests if (m, path) == ("POST", "/api/me/plan")]

    def age_posts(self) -> list[Any]:
        return [b for m, path, b in self.requests if (m, path) == ("POST", AGE_CONFIRMATION)]

    def _confirm_age(self, body: Any) -> tuple[int, Any]:
        if not self.age_gate:
            return 404, _error("not_found")
        if self.refuse_age:
            return 403, _error(self.refuse_age)
        if body != {"is_adult": True}:
            return 422, _error("validation_failed")
        self.age_confirmed_at = self.age_confirmed_at or "2026-11-04T10:00:00Z"
        return 200, {"id": "u-ivy", "display_name": "Ivy", "age_confirmed_at": self.age_confirmed_at}

    def answer(self, method: str, path: str, body: Any) -> tuple[int, Any]:
        if (method, path) == ("POST", AGE_CONFIRMATION):
            return self._confirm_age(body)
        if self.age_gate and self.age_confirmed_at is None and path not in UNGATED:
            return 403, _error("age_confirmation_required")
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
