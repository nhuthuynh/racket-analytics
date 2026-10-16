"""Binds tests/features/demo_seed.feature (MVP-03; PO MVP goal 2026-10-15).

The real scripts/demo/seed_demo.py, run as `make demo` runs it. Refusals: against a loopback
stub API that records every request. Seeding: against the live Compose stack named by
RA_DEMO_BASE_URL (skipped without it; CI web-checks sets it after its Playwright journeys).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from demo_live import LiveStack, StubApi, live_stack, match_id_in, run_demo, stub_api
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("demo_seed.feature")


@dataclass
class World:
    args: list[str] = field(default_factory=list)
    stub: StubApi | None = None
    stack: LiveStack | None = None
    runs: list[subprocess.CompletedProcess[str]] = field(default_factory=list)


@pytest.fixture
def stub() -> Any:
    with stub_api() as s:
        yield s


def _env_file(tmp_path: Path, text: str) -> str:
    f = tmp_path / "env"
    f.write_text(text)
    return str(f)


@given(parsers.parse('a stack whose profile is "{profile}"'), target_fixture="world")
def profile_stack(profile: str, stub: StubApi, tmp_path: Path) -> World:
    env = _env_file(tmp_path, f"APP_ENV={profile}\nDEV_IDENTITY_ENABLED=true\n")
    return World(args=["--base-url", stub.url, "--env-file", env], stub=stub)


@given('a stack whose profile is "dev" but whose dev sign-in is disabled', target_fixture="world")
def dev_sign_in_disabled(stub: StubApi, tmp_path: Path) -> World:
    # The env file says dev and enabled; the API itself has no /dev/* routes (404): the live
    # check decides, so a stale env file cannot let the demo through.
    env = _env_file(tmp_path, "APP_ENV=dev\nDEV_IDENTITY_ENABLED=true\n")
    return World(args=["--base-url", stub.url, "--env-file", env], stub=stub)


@given("a running dev stack", target_fixture="world")
def running_stack() -> World:
    stack = live_stack()
    return World(args=stack.demo_args(), stack=stack)


@when("the developer runs the demo")
@when("the developer runs the demo again")
def run(world: World) -> None:
    world.runs.append(run_demo(*world.args))


@then(parsers.parse('the demo is refused with "{message}"'))
def refused(world: World, message: str) -> None:
    res = world.runs[-1]
    assert res.returncode == 3, (res.returncode, res.stdout, res.stderr)
    assert message in res.stderr


@then("the stack received no request")
def no_request(world: World) -> None:
    assert world.stub is not None
    assert world.stub.requests == []


@then("no match was created")
def no_match(world: World) -> None:
    assert world.stub is not None
    assert world.stub.requests, "the live /dev/users check never ran"
    assert all(method == "GET" for method, _ in world.stub.requests), world.stub.requests


def _demo_match(world: World) -> str:
    res = world.runs[-1]
    assert res.returncode == 0, (res.returncode, res.stdout[-2000:], res.stderr[-2000:])
    match_id = match_id_in(res.stdout)
    assert match_id, res.stdout
    return match_id


@then(parsers.parse('the demo prints the match\'s stats page and "{hint}"'))
def prints_link(world: World, hint: str) -> None:
    assert world.stack is not None
    out = world.runs[-1].stdout
    match_id = _demo_match(world)
    assert f"{world.stack.base_url}/matches/{match_id}/stats" in out
    assert hint in out


@then(parsers.parse("the demo match has {count:d} tagged rallies"))
def rally_count(world: World, count: int) -> None:
    assert world.stack is not None
    c = world.stack.client()
    r = c.request("GET", f"/matches/{_demo_match(world)}/score-sheet")
    assert r.status == 200
    assert len(r.json()["rows"]) == count


@then("its stats show published metrics for both sides")
def stats_both_sides(world: World) -> None:
    assert world.stack is not None
    c = world.stack.client()
    r = c.request("GET", f"/matches/{_demo_match(world)}/stats")
    assert r.status == 200, r.status
    metrics = r.json()["metrics"]
    assert metrics, "no published metric"
    assert all(set(per) >= {"A", "B"} for per in metrics.values())
    assert any(per["A"].get("n") and per["B"].get("n") for per in metrics.values())


@then('"Show me" lists the rallies behind a metric')
def show_me(world: World) -> None:
    assert world.stack is not None
    c = world.stack.client()
    match_id = _demo_match(world)
    metrics = c.request("GET", f"/matches/{match_id}/stats").json()["metrics"]
    metric_id = next(m for m, v in metrics.items() if v["A"].get("n"))
    r = c.request("GET", f"/matches/{match_id}/stats/{metric_id}/evidence?side=A&limit=10")
    assert r.status == 200, (metric_id, r.status)
    assert r.json()["items"], metric_id


@then("both runs name the same demo match")
def same_match(world: World) -> None:
    ids = [match_id_in(r.stdout) for r in world.runs]
    assert all(r.returncode == 0 for r in world.runs), [r.stderr[-500:] for r in world.runs]
    assert ids[0] is not None, ids
    assert ids[-1] == ids[0], ids
    assert "already seeded" in world.runs[-1].stdout
