"""Binds tests/features/live_privacy_harness.feature (QA-HARNESS-4b; G04-09, G04-10).

The harness steps run over real HTTP against `Stack`, a local stub of the api-sprint-04 §4-§7
routes; account rows live in a real Postgres (scripts/dev-postgres.sh) written and counted
through real psql; the purge job, label-set build and stored-bytes count are real commands
over files the stub reads and writes. Standard library plus pytest-bdd; no product imports.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
import threading
import uuid
from argparse import Namespace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from cluster import fresh_cluster
from conftest import SCRIPTS_DIR
from pytest_bdd import given, parsers, scenarios, then, when
from test_livehttp_mailpit import FakeMailpit

pytestmark = pytest.mark.integration
scenarios("live_privacy_harness.feature")
sys.path.insert(0, str(SCRIPTS_DIR / "measure"))
import live_privacy as lp  # noqa: E402
from livehttp import Client, ssl_context  # noqa: E402

LIMIT, MAX_UPLOAD = 1000, 400


class Stack:
    """Flags-on stub: sessions, age gate, match-creation limit, storage quota, video, consent."""

    def __init__(self, tmp: Path, mail: FakeMailpit) -> None:
        self.psql, self.under18_row, self.per_hour, self.store_refused = "", False, 10, False
        self.created: dict[str, int] = {}
        self.declared, self.sessions = 0, set()
        self.video, self.labels, self.stored = tmp / "video", tmp / "labels", tmp / "stored"
        self.video.write_text("x")
        self.stored.write_text("0\n")
        self.labels.write_text("")
        self.label_always, self.match_id = False, str(uuid.uuid4())
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_: Any) -> None:
                return

            def _reply(self, status: int, body: Any = None, **headers: str) -> None:
                data = json.dumps(body).encode() if body is not None else b""
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k.replace("_", "-"), v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _route(self) -> None:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"null")
                cookie = (self.headers.get("Cookie") or "=").split("=", 1)[1]
                length = int(self.headers.get("Upload-Length") or 0)
                self._reply(*outer.answer(self.command, self.path, body, cookie, length))

            do_GET = do_POST = do_PUT = _route  # noqa: N815

        self.mail = mail
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def _account_row(self) -> None:
        lp.psql(self.psql, f"INSERT INTO accounts VALUES ('{uuid.uuid4()}')")  # noqa: S608

    def answer(self, method: str, path: str, body: Any, cookie: str, length: int) -> tuple:
        route = f"{method} {re.sub(r'/[0-9a-f-]{36}', '/{id}', path)}"
        if route == "POST /auth/links":
            self.mail.deliver(uuid.uuid4().hex + uuid.uuid4().hex[:11])
            return (202,)
        if route == "POST /auth/exchange":
            token = uuid.uuid4().hex
            self.sessions.add(token)
            return 200, {}, {"Set_Cookie": f"racket_session={token}; Path=/"}
        if route == "POST /me/age-confirmation":
            if body["is_adult"] or self.under18_row:
                self._account_row()
            if body["is_adult"]:
                return 200, {"age_confirmed_at": "2026-10-17T00:00:00Z"}
            self.sessions.discard(cookie)
            return 403, {"code": "under_age", "message": "You must be 18 or over."}
        if route == "GET /me":
            return (200, {"id": cookie}) if cookie in self.sessions else (401, {})
        if route == "POST /matches":
            self.created[cookie] = self.created.get(cookie, 0) + 1
            if self.created[cookie] <= self.per_hour:
                return 201, {"id": str(uuid.uuid4())}
            return 429, {"code": "rate_limited", "retry_at": "2026-10-17T01:00:00Z"}
        if route == "GET /me/quota":
            return 200, {"storage": {"used_bytes": 0, "limit_bytes": LIMIT}}
        if route == "GET /upload-policy":
            return 200, {"max_bytes": MAX_UPLOAD}
        return self._privacy(route, body, length)

    def _privacy(self, route: str, body: Any, n: int) -> tuple:
        if route == "POST /matches/{id}/uploads":
            if self.declared + n > LIMIT:
                if self.store_refused:
                    self.stored.write_text(f"{n}\n")
                quota = {"used_bytes": self.declared, "limit_bytes": LIMIT, "requested_bytes": n}
                return 429, {"code": "storage_quota_exceeded", "retry_at": None, "quota": quota}
            self.declared += n
            return 201, None, {"Location": f"/uploads/{uuid.uuid4()}"}
        if route == "PUT /me/training-consent":
            on = body["opt_in"]
            self.labels.write_text(self.match_id if on or self.label_always else "")
            return 200, {"opt_in": on}
        if route == "GET /me/training-consent":
            return 200, {"opt_in": False, "changed_at": None}
        if route == "GET /matches/{id}":
            return 200, {"id": self.match_id, "review_video_delete_at": "2026-11-16T00:00:00Z"}
        if route == "GET /matches/{id}/video":
            return 200, {"url": f"{self.url}/objects/video", "expires_in_s": 600}
        if route == "GET /objects/video":
            return (206, {}) if self.video.exists() else (404, {})
        return 200, {}  # PUT /me/retention, stats, score sheet, plan

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def stack(tmp_path: Path):
    mail = FakeMailpit()
    s = Stack(tmp_path, mail)
    yield s
    s.close()
    mail.close()


@pytest.fixture
def world(stack: Stack) -> dict[str, Any]:
    return {
        "args": Namespace(
            api=stack.url,
            origin="https://localhost:3000",
            mailpit=stack.mail.url,
            cacert=None,
            insecure_loopback=False,
            flags="on",
            purge_cmd=f"rm -f {shlex.quote(str(stack.video))}",
            label_set_cmd=f"cat {shlex.quote(str(stack.labels))}",
            stored_bytes_cmd=f"cat {shlex.quote(str(stack.stored))}",
            result_timeout=5.0,
        )
    }


def _client(stack: Stack) -> Client:
    return Client(stack.url, "https://localhost:3000", ssl_context(None, False))


@pytest.fixture
def db(tmp_path: Path, stack: Stack, world: dict[str, Any]):
    with fresh_cluster(tmp_path / "pg") as url:
        stack.psql = world["args"].psql = f"psql {shlex.quote(url)} -v ON_ERROR_STOP=1"
        lp.psql(stack.psql, "CREATE TABLE accounts (id uuid PRIMARY KEY)")
        yield url


@given("a stack that writes an account row when the answer is under 18")
def under18_writes(db: str, stack: Stack) -> None:
    stack.under18_row = True


@given("a stack that refuses under-18 answers without writing a row")
def under18_refused(db: str) -> None:
    return


@given("a psql command that cannot reach the database")
def broken_psql(world: dict[str, Any]) -> None:
    world["args"].psql = "psql postgresql://nobody@127.0.0.1:1/none"


@given("a label-set build that lists the match whatever the consent")
def label_always(stack: Stack) -> None:
    stack.label_always = True


@given("a label-set build that lists the match only while consent is on")
def label_follows(stack: Stack) -> None:
    stack.label_always = False


@given("a purge job that leaves the review video")
def purge_leaks(world: dict[str, Any]) -> None:
    world["args"].purge_cmd = "true"


@given("a purge job that deletes the review video")
def purge_deletes() -> None:
    return


@given("a stack that accepts 11 matches an hour")
def eleven(stack: Stack) -> None:
    stack.per_hour = 11


@given("a stack that refuses the over-quota upload but stores its bytes")
def stores_bytes(stack: Stack) -> None:
    stack.store_refused = True


@given("a stack that accepts 10 matches an hour and refuses uploads past the quota")
def exact(stack: Stack) -> None:
    stack.per_hour = 10


@when("the age step runs")
def age_runs(world: dict[str, Any]) -> None:
    world["steps"] = [lp.age_step(world["args"])[0]]


def _run(world: dict[str, Any], stack: Stack, names: str) -> None:
    args, c, m = world["args"], _client(stack), stack.match_id
    steps = {
        "consent": lambda: lp.consent_step(c, args, m),
        "retention": lambda: lp.retention_step(c, args, m),
        "burst": lambda: lp.burst_step(args),
        "quota": lambda: lp.quota_step(args),
    }
    world["steps"] = [steps[n]() for n in names.split()]


@when(parsers.re(r"the (?P<a>\w+) step runs and the (?P<b>\w+) step runs"))
def two_run(world: dict[str, Any], stack: Stack, a: str, b: str) -> None:
    _run(world, stack, f"{a} {b}")


@when(parsers.re(r"the (?P<a>consent|retention|burst|quota) step runs$"))
def one_runs(world: dict[str, Any], stack: Stack, a: str) -> None:
    _run(world, stack, a)


@when(parsers.parse('the harness starts with "{args}"'))
def starts(world: dict[str, Any], args: str, capsys: pytest.CaptureFixture[str]) -> None:
    world["rc"] = lp.main(shlex.split(args))
    world["err"] = capsys.readouterr().err


@then(parsers.parse('the step fails, naming "{text}"'))
def step_fails(world: dict[str, Any], text: str) -> None:
    (step,) = world["steps"]
    assert step["ok"] is False, step
    assert any(text in p for p in step["problems"]), step


@then("the step passes")
@then("both steps pass")
def steps_pass(world: dict[str, Any]) -> None:
    assert world["steps"], world
    for step in world["steps"]:
        assert step["ok"] is True, step
        assert step["problems"] == [], step


@then(parsers.parse('it exits 2, naming "{option}"'))
def exits_2(world: dict[str, Any], option: str) -> None:
    assert world["rc"] == 2, world
    assert option in world["err"], world["err"]
