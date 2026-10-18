"""Binds tests/features/live_plan_request_body.feature (FIX-04-1b; G04-02 a and c).

`live_plan.main` runs over real TLS against the QA-HARNESS-4a stub (test_live_plan_harness.Stub,
reused unchanged), made strict: POST /me/plan answers 422 with the contract's field codes
(plan_contract, read from api-sprint-04 §2.1) unless the body keeps the table, as the API does.
"""

from __future__ import annotations

import http.client
import json
import ssl
from typing import Any

import plan_contract as pc
import pytest
import test_live_plan_harness as harness
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]
scenarios("live_plan_request_body.feature")
Stub, live = harness.Stub, harness.live
tls, world = harness.tls, harness.world  # the QA-HARNESS-4a fixtures, reused unchanged


class StrictStub(Stub):
    """The QA-HARNESS-4a stub whose POST /me/plan validates the closed body like the API."""

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        self.generate_problems: list[list] = []
        outer, base = self, self.server.RequestHandlerClass

        class Strict(base):  # type: ignore[misc, valid-type]
            def route(self) -> None:
                raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                self.body = raw  # parsed only where the contract says JSON (POST /me/plan)
                outer.seen += 1
                outer.answer(self, self.path.removeprefix("/api").split("?")[0])

            do_GET = do_POST = do_PATCH = do_HEAD = route

        self.server.RequestHandlerClass = Strict

    def answer(self, h: Any, p: str) -> None:
        if p == "/me/plan" and h.command == "POST":
            try:
                found = pc.problems(json.loads(h.body or b"null"))
            except ValueError:
                found = [(None, "invalid")]
            self.generate_problems.append(found)
            if found:
                fields = [{"field": f, "code": c} for f, c in found]
                return h.reply(422, {"error": {"code": "validation_failed", "fields": fields}})
        return super().answer(h, p)


@given("a strict stub stack whose plan keeps every rule")
def _strict(world):
    world["stub"] = StrictStub(world["tls"], world["mailpit"], "keeps every rule")
    world["base"] = world["stub"].base


@when("a client posts a generate body without equipment and level")
def _post_partial(world):
    ctx = ssl.create_default_context(cafile=world["tls"][1])
    port = int(world["base"].rsplit(":", 1)[1])
    conn = http.client.HTTPSConnection("localhost", port, context=ctx, timeout=10)
    body = {k: v for k, v in live.PREFS.items() if k not in ("equipment", "level")}
    conn.request("POST", "/api/me/plan", json.dumps(body), {"Content-Type": "application/json"})
    r = conn.getresponse()
    world["reply"] = (r.status, json.loads(r.read() or b"null"))
    conn.close()


def _main(world, *extra: str) -> None:
    world["rc"] = live.main(["--base-url", world["base"], *world["args"], *extra])
    out = world["tmp"] / "out.json"
    world["report"] = json.loads(out.read_text()) if out.exists() else None


@when(parsers.parse("the plan harness runs {runs:d} run with determinism {k:d}"))
def _runs(world, runs, k):
    _main(world, "--runs", str(runs), "--determinism", str(k))


@when(parsers.parse("the plan harness runs the load mode at {rps:d} RPS for 1 second"))
def _load(world, rps):
    _main(world, "--load", "--rps", str(rps), "--duration", "1")


@then(parsers.parse('the stack answers 422 naming "{a}" and "{b}" as required'))
def _refused(world, a, b):
    status, body = world["reply"]
    assert status == 422
    assert body["error"]["fields"] == [
        {"field": a, "code": "required"},
        {"field": b, "code": "required"},
    ]


@then(parsers.parse("it exits {rc:d}"))
def _rc(world, rc):
    assert world["rc"] == rc, json.dumps(world["report"], indent=1)[:3000]


@then("every generate body the stack saw was accepted")
def _accepted(world):
    seen = world["stub"].generate_problems
    assert seen
    assert seen == [[]] * len(seen)


@then(parsers.parse("the summary times {g:d} generations and {d:d} done"))
def _timed(world, g, d):
    summary = world["report"]["summary"]
    assert (summary["generate"]["n"], summary["done_visible"]["n"]) == (g, d)


@then("the load summary counts 20 requests and none unexpected")
def _load_summary(world):
    summary = world["report"]["summary"]
    assert (summary["requests"], summary["status_unexpected"], summary["ok"]) == (20, 0, True)
