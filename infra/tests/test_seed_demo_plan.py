"""IT-04-11 (ST-064): `make demo` creates one plan for Ivy; running it again keeps it.

Binds tests/features/demo_seed_plan.feature too. The real scripts/demo/seed_demo.py over HTTP,
always against the loopback fake of the public API (demo_fake_api.py), and against the live
Compose stack named by RA_DEMO_BASE_URL (and RA_DEMO_CACERT) when set. Negative cases first.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from demo_fake_api import FakeApi, fake_api
from demo_live import live_stack, run_demo
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("demo_seed_plan.feature")

PLAN_LINE = re.compile(r"^Plan ([A-Za-z0-9_-]+):", re.MULTILINE)
DEMO_PREFERENCES = {"minutes_per_session": 30, "sessions_per_week": 3, "players_available": 1,
                    "equipment": ["wall"], "level": "intermediate"}  # fmt: skip


def plan_id_in(output: str) -> str | None:
    found = PLAN_LINE.search(output)
    return found.group(1) if found else None


@dataclass
class Stack:
    fake: FakeApi
    env: Path
    runs: list[subprocess.CompletedProcess[str]] = field(default_factory=list)

    def demo(self) -> subprocess.CompletedProcess[str]:
        self.runs.append(run_demo("--base-url", self.fake.url, "--env-file", str(self.env)))
        return self.runs[-1]

    def paths(self) -> list[str]:
        return [f"{method} {path}" for method, path, _ in self.fake.requests]


@pytest.fixture
def stack(tmp_path: Path) -> Iterator[Stack]:
    (tmp_path / "env").write_text("APP_ENV=dev\nDEV_IDENTITY_ENABLED=true\n")
    with fake_api() as fake:
        yield Stack(fake, tmp_path / "env")


# ---------------------------------------------------------------- IT-04-11 (fake API)
def test_it_04_11_a_stack_without_the_plan_api_fails_reading_the_plan_and_generates_none(
    stack: Stack,
) -> None:
    stack.fake.plan_api = False
    res = stack.demo()
    assert (res.returncode, "make demo failed: read the plan:" in res.stderr) == (1, True), res
    assert stack.fake.plan_posts() == [], stack.paths()


def test_it_04_11_an_existing_plan_is_kept_and_no_plan_is_generated(stack: Stack) -> None:
    stack.fake.plans.append({"id": "plan-kept", "preferences": {"players_available": 4}})
    res = stack.demo()
    assert res.returncode == 0, (res.stdout, res.stderr)
    assert stack.fake.plan_posts() == [], stack.paths()
    assert plan_id_in(res.stdout) == "plan-kept", res.stdout


def test_it_04_11_the_plan_is_generated_after_the_match_and_its_stats(stack: Stack) -> None:
    res = stack.demo()
    assert res.returncode == 0, res.stderr
    paths = stack.paths()
    assert paths.index("POST /api/me/plan") > paths.index("GET /api/matches/m-demo-1/stats")
    assert res.stdout.index("/stats") < res.stdout.index("/plan"), res.stdout


# ---------------------------------------------------------------- IT-04-11 (live stack)
def test_it_04_11_live_stack_one_plan_and_a_rerun_keeps_its_id() -> None:
    live = live_stack()
    first, again = run_demo(*live.demo_args()), run_demo(*live.demo_args())
    assert (first.returncode, again.returncode) == (0, 0), (first.stderr[-2000:], again.stderr)
    plan_id = plan_id_in(first.stdout)
    assert plan_id, first.stdout
    assert plan_id_in(again.stdout) == plan_id, again.stdout
    assert f"Open {live.base_url}/plan" in first.stdout
    r = live.client().request("GET", "/me/plan")
    assert (r.status, r.json()["id"], bool(r.json()["sessions"])) == (200, plan_id, True)
    for a in (a for s in r.json()["sessions"] for a in s["assignments"]):
        assert {"metric_id", "value", "n", "rally_ids"} <= set(a["citation"]), a


# ---------------------------------------------------------------- demo_seed_plan.feature
@given("a dev stack where Ivy has a complete demo match", target_fixture="world")
def dev_stack(stack: Stack) -> Stack:
    return stack


@given(parsers.parse('the plan API refuses to generate a plan with "{code}"'))
def plan_refused(world: Stack, code: str) -> None:
    world.fake.refuse_plan = code


@when("the developer runs the demo")
@when("the developer runs the demo again")
def run(world: Stack) -> None:
    world.demo()


@then(parsers.parse('the demo fails with exit code 1 naming the step "{step}"'))
def fails_naming_step(world: Stack, step: str) -> None:
    res = world.runs[-1]
    assert res.returncode == 1, (res.returncode, res.stdout, res.stderr)
    assert f"make demo failed: {step}:" in res.stderr, res.stderr


@then("the demo prints no plan page")
def no_plan_page(world: Stack) -> None:
    assert "/plan" not in world.runs[-1].stdout, world.runs[-1].stdout


@then("the demo exits 0 and prints the stack's plan page")
def prints_plan_page(world: Stack) -> None:
    res = world.runs[-1]
    assert res.returncode == 0, (res.returncode, res.stdout, res.stderr)
    assert f"Open {world.fake.url}/plan\n" in res.stdout, res.stdout
    assert plan_id_in(res.stdout) == world.fake.plans[-1]["id"], res.stdout


@then(parsers.parse("the plan was generated once with {preferences}"))
def generated_once(world: Stack, preferences: str) -> None:
    assert preferences == "solo, 30 min, 3 sessions a week, no ball machine, intermediate"
    assert world.fake.plan_posts() == [DEMO_PREFERENCES], world.paths()


@then("both runs name the same plan id")
def same_plan_id(world: Stack) -> None:
    assert [r.returncode for r in world.runs] == [0, 0], [r.stderr for r in world.runs]
    ids = [plan_id_in(r.stdout) for r in world.runs]
    assert ids[0] is not None, world.runs[0].stdout
    assert ids == [ids[0], ids[0]], ids
    assert "already generated" in world.runs[-1].stdout, world.runs[-1].stdout
