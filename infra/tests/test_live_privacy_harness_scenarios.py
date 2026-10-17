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
FLAG_ROUTES = {
    "GET /me/retention",
    "PUT /me/retention",
    "GET /me/training-consent",
    "PUT /me/training-consent",
    "GET /me/quota",
    "POST /me/age-confirmation",
}


class Stack:
    """Stub of both flag states: sessions, age gate, match limit, storage quota, video, consent.

    With `flags_on` False the flag routes answer 404 (unless listed in `still_served`), the
    features are off, no limit applies and no field the flags add is served (api-sprint-04 §1).
    """

    def __init__(self, tmp: Path, mail: FakeMailpit) -> None:
        self.psql, self.under18_row, self.per_hour, self.store_refused = "", False, 10, False
        self.created: dict[str, int] = {}
        self.declared, self.sessions = 0, set()
        self.video, self.labels, self.stored = tmp / "video", tmp / "labels", tmp / "stored"
        self.video.write_text("x")
        self.stored.write_text("0\n")
        self.labels.write_text("")
        self.label_always, self.match_id = False, str(uuid.uuid4())
        self.flags_on, self.still_served = True, set()
        self.refuse_matches = self.over_500 = self.me_leaks = False
        self.features_on: set[str] = set()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_: Any) -> None:
                return

            def _reply(self, status: int, body: Any = None, headers: Any = None) -> None:
                data = json.dumps(body).encode() if body is not None else b""
                self.send_response(status)
                for k, v in (headers or {}).items():
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

            do_GET = do_POST = do_PUT = _route

        self.mail = mail
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def _account_row(self) -> None:
        if self.psql:  # only the age scenarios have a database
            lp.psql(self.psql, f"INSERT INTO accounts VALUES ('{uuid.uuid4()}')")  # noqa: S608

    def answer(self, method: str, path: str, body: Any, cookie: str, length: int) -> tuple:
        route = f"{method} {re.sub(r'/[0-9a-f-]{36}', '/{id}', path)}"
        if not self.flags_on and route in FLAG_ROUTES - self.still_served:
            return 404, {"code": "not_found"}
        if route == "GET /config/public":
            names = ("age_gate", "retention", "training_consent", "quotas")
            return 200, {"features": {n: self.flags_on or n in self.features_on for n in names}}
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
            me = {"id": cookie, **({"age_confirmed_at": "2026-10-17"} if self.me_leaks else {})}
            return (200, me) if cookie in self.sessions else (401, {})
        if route == "POST /matches":
            if self.refuse_matches:
                return 503, {"code": "unavailable"}
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
            if self.declared + n > LIMIT and self.over_500:
                return 500, {"code": "internal"}
            if self.declared + n > LIMIT and self.flags_on:
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
            match = {"id": self.match_id, "review_video_delete_at": "2026-11-16T00:00:00Z"}
            return 200, match if self.flags_on else {"id": self.match_id}
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
            quota_bytes=LIMIT,
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


@given("a flags-off stack")
def flags_off(stack: Stack, world: dict[str, Any]) -> None:
    stack.flags_on, stack.per_hour = False, 10**6
    world["args"].flags = "off"


@given(parsers.parse('a flags-off stack that still serves "{path}"'))
def flags_off_serving(stack: Stack, world: dict[str, Any], path: str) -> None:
    flags_off(stack, world)
    stack.still_served = {f"GET {path}"}


@given(parsers.parse('a flags-off stack that lists the "{name}" feature as on'))
def flags_off_feature_on(stack: Stack, world: dict[str, Any], name: str) -> None:
    flags_off(stack, world)
    stack.features_on = {name}


@given("a flags-off stack whose GET /me carries age_confirmed_at")
def flags_off_me_leaks(stack: Stack, world: dict[str, Any]) -> None:
    flags_off(stack, world)
    stack.me_leaks = True


@given("a flags-off stack that refuses new matches")
def flags_off_no_match(stack: Stack, world: dict[str, Any]) -> None:
    flags_off(stack, world)
    stack.refuse_matches = True


@given("a flags-off stack that answers the over-quota upload with 500")
def flags_off_500(stack: Stack, world: dict[str, Any]) -> None:
    flags_off(stack, world)
    stack.over_500 = True


@given(parsers.parse("an alert rules file with {n:d} rules"))
def alert_rules(world: dict[str, Any], tmp_path: Path, n: int) -> None:
    rules = tmp_path / "billing.rules.yml"
    rules.write_text("groups:\n  - rules:\n" + "      - alert: Billing\n" * n)
    world["args"].alert_rules, world["args"].alert_test_cmd = str(rules), "echo SUCCESS"


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
        "flags-off": lambda: lp.flags_off_step(args),
    }
    world["steps"] = [steps[n]() for n in names.split()]


@when(parsers.re(r"the (?P<a>\w+) step runs and the (?P<b>\w+) step runs"))
def two_run(world: dict[str, Any], stack: Stack, a: str, b: str) -> None:
    _run(world, stack, f"{a} {b}")


@when(parsers.re(r"the (?P<a>consent|retention|burst|quota) step runs$"))
def one_runs(world: dict[str, Any], stack: Stack, a: str) -> None:
    _run(world, stack, a)


@when(parsers.parse('the steps "{names}" run'))
def steps_run(world: dict[str, Any], stack: Stack, names: str) -> None:
    _run(world, stack, names)


@when("the quota steps run with the alert test")
def quota_steps_run(world: dict[str, Any]) -> None:
    world["quotas"] = lp.quota_steps(world["args"])


@when(parsers.parse('the harness runs against the stack with "{argv}"'))
def runs_against(
    world: dict[str, Any],
    stack: Stack,
    tmp_path: Path,
    argv: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    a, clip = world["args"], tmp_path / "clip.mp4"
    clip.write_bytes(b"0123456789")
    extra = ["--api", a.api, "--mailpit", a.mailpit, "--min-free-gb", "0", "--file", str(clip),
             "--result-timeout", "1", "--quota-bytes", str(LIMIT)]  # fmt: skip
    if "--flags on" in argv:
        extra += ["--psql", a.psql, "--purge-cmd", a.purge_cmd, "--label-set-cmd", a.label_set_cmd]
    world["rc"] = lp.main([*shlex.split(argv), *extra])
    world["out"] = json.loads(capsys.readouterr().out)


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


@then("every step passes")
def every_step_passes(world: dict[str, Any]) -> None:
    steps_pass(world)


@then(parsers.parse('the "{name}" step fails, naming "{text}"'))
def named_step_fails(world: dict[str, Any], name: str, text: str) -> None:
    step = world["quotas"][name]
    assert step["ok"] is False, world["quotas"]
    assert any(text in p for p in step["problems"]), step


@then("every quota step passes")
def every_quota_step_passes(world: dict[str, Any]) -> None:
    assert set(world["quotas"]) == {"burst", "quota", "alerts"}, world["quotas"]
    assert all(st["ok"] and not st["problems"] for st in world["quotas"].values()), world["quotas"]


@then(parsers.parse('it exits 1 with "{name}" failing'))
def exits_1(world: dict[str, Any], name: str) -> None:
    out = world["out"]
    assert world["rc"] == 1, out
    assert out["ok"] is False, out
    assert any(run[name]["ok"] is False for run in out["runs"]), out


@then("it exits 0 with every step passing")
def exits_0(world: dict[str, Any]) -> None:
    out = world["out"]
    assert world["rc"] == 0, out
    assert out["ok"] is True, out
    assert set(out["quotas"]) == {"burst", "quota"}, out
    steps = [st for run in out["runs"] for st in run.values()] + list(out["quotas"].values())
    assert len(steps) == 4, out
    assert all(st["ok"] for st in steps), out
