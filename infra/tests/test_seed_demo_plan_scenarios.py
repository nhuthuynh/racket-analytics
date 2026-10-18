"""Binds tests/features/demo_seed_plan.feature (ST-064; QD §7; goal G04-06).

The real scripts/demo/seed_demo.py, run as `make demo` runs it, against the loopback fake of the
public HTTP API (demo_fake_api.py) in which Ivy already has a complete demo match.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from demo_fake_api import FakeApi, fake_api
from demo_live import run_demo
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("demo_seed_plan.feature")

PLAN_LINE = re.compile(r"^Plan ([A-Za-z0-9_-]+):", re.MULTILINE)
DEMO_PREFERENCES = {
    "minutes_per_session": 30,
    "sessions_per_week": 3,
    "players_available": 1,
    "equipment": ["wall"],
    "level": "intermediate",
}


@dataclass
class World:
    fake: FakeApi
    args: list[str]
    runs: list[subprocess.CompletedProcess[str]] = field(default_factory=list)


def plan_id_in(output: str) -> str | None:
    found = PLAN_LINE.search(output)
    return found.group(1) if found else None


@pytest.fixture
def fake() -> Any:
    with fake_api() as f:
        yield f


@given("a dev stack where Ivy has a complete demo match", target_fixture="world")
def dev_stack(fake: FakeApi, tmp_path: Path) -> World:
    env = tmp_path / "env"
    env.write_text("APP_ENV=dev\nDEV_IDENTITY_ENABLED=true\n")
    return World(fake, ["--base-url", fake.url, "--env-file", str(env)])


@given(parsers.parse('the plan API refuses to generate a plan with "{code}"'))
def plan_refused(world: World, code: str) -> None:
    world.fake.refuse_plan = code


@when("the developer runs the demo")
@when("the developer runs the demo again")
def run(world: World) -> None:
    world.runs.append(run_demo(*world.args, timeout=60))


@then(parsers.parse('the demo fails with exit code 1 naming the step "{step}"'))
def fails_naming_step(world: World, step: str) -> None:
    res = world.runs[-1]
    assert res.returncode == 1, (res.returncode, res.stdout, res.stderr)
    assert f"make demo failed: {step}:" in res.stderr, res.stderr


@then("the demo prints no plan page")
def no_plan_page(world: World) -> None:
    assert "/plan" not in world.runs[-1].stdout, world.runs[-1].stdout


@then("the demo exits 0 and prints the stack's plan page")
def prints_plan_page(world: World) -> None:
    res = world.runs[-1]
    assert res.returncode == 0, (res.returncode, res.stdout, res.stderr)
    assert f"Open {world.fake.url}/plan\n" in res.stdout, res.stdout
    assert plan_id_in(res.stdout) == world.fake.plans[-1]["id"], res.stdout


@then(parsers.parse("the plan was generated once with {preferences}"))
def generated_once(world: World, preferences: str) -> None:
    assert preferences == "solo, 30 min, 3 sessions a week, no ball machine, intermediate"
    assert world.fake.plan_posts() == [DEMO_PREFERENCES], world.fake.requests
    assert "ball_machine" not in DEMO_PREFERENCES["equipment"]


@then("both runs name the same plan id")
def same_plan_id(world: World) -> None:
    assert [r.returncode for r in world.runs] == [0, 0], [r.stderr for r in world.runs]
    ids = [plan_id_in(r.stdout) for r in world.runs]
    assert ids[0] is not None, world.runs[0].stdout
    assert ids == [ids[0], ids[0]], ids
    assert "already generated" in world.runs[-1].stdout, world.runs[-1].stdout
