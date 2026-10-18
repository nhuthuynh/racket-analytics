"""Binds tests/features/goal_method_g04_03.feature (FIX-04-1c; QA-V04R1-01; G04-03 a, c).

Each scenario runs the real backend pytest selection and the real junit_rate.py, with the
commands taken from the Sprint 4 goal scorecard as written. Bound in infra/tests, beside the
other goal-method guards (test_goal_scorecard_fast_tests.py).
"""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import Any

import pytest
from domain_budget import run_in_backend
from goal_g04_03 import (
    EXTRA_GOLDEN,
    PROPERTY_TEST,
    SCORECARD_COMPARISONS,
    check_argv,
    check_line,
    matches,
    method_text,
    pytest_line,
    requires_of,
    run_check,
)
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("goal_method_g04_03.feature")


@pytest.fixture
def world(tmp_path: Path) -> dict[str, Any]:
    return {"goal": tmp_path}


def _run_marker(world: dict[str, Any], marker: str) -> None:
    """The scorecard's pytest line for ``marker``, run in backend/ with $GOAL set."""
    line = pytest_line(world.get("method", method_text()), marker)
    cmd = shlex.split(line.replace("$GOAL", str(world["goal"])).replace('"', ""))
    res = run_in_backend([*cmd, "-p", "no:cacheprovider"])
    assert res.returncode == 0, res.stdout[-2000:] + res.stderr[-2000:]
    world["line"] = check_line(world.get("method", method_text()), marker)


@given("the JUnit report of the real weakness_golden run")
def golden_report(world: dict[str, Any]) -> None:
    report = world["goal"] / "weakness-golden.xml"
    res = run_in_backend(
        ["uv", "run", "pytest", "-q", "-m", "weakness_golden", "-p", "no:cacheprovider",
         "--junitxml", str(report)]
    )  # fmt: skip
    assert res.returncode == 0, res.stdout[-2000:]
    world["report"] = report


@when(parsers.parse('junit_rate.py checks it with "{args}"'))
def check_with(world: dict[str, Any], args: str) -> None:
    line = (
        f"python3 scripts/measure/junit_rate.py --include '.' {args} \"$GOAL/weakness-golden.xml\""
    )
    world["result"] = run_check(line, world["goal"])


@then(parsers.parse('junit_rate.py exits 1 and reports "{name}" missing'))
def exits_1(world: dict[str, Any], name: str) -> None:
    res, out = world["result"]
    assert res.returncode == 1
    assert out["passed"] == out["selected"] == 9
    assert out["missing"] == [name]


@given("the G04-03 method in the Sprint 4 goal scorecard")
def the_method(world: dict[str, Any]) -> None:
    world["method"] = method_text()


@when("its weakness_golden pytest run and its golden junit_rate.py check run as written")
def run_golden(world: dict[str, Any]) -> None:
    _run_marker(world, "weakness_golden")
    world["result"] = run_check(world["line"], world["goal"])


@when("its plan_property pytest run and its property junit_rate.py check run as written")
def run_property(world: dict[str, Any]) -> None:
    _run_marker(world, "plan_property")
    world["result"] = run_check(world["line"], world["goal"])


@then("the check exits 0 with nothing missing")
def exits_0(world: dict[str, Any]) -> None:
    res, out = world["result"]
    assert res.returncode == 0, res.stdout + res.stderr
    assert (out["missing"], out["failed"], out["skipped"], out["rate"]) == ([], 0, 0, 1.0)


@then("each of the 7 scorecard comparisons is required by its own pattern")
def seven(world: dict[str, Any]) -> None:
    hits = matches(requires_of(check_argv(world["line"], world["goal"])),
                   (*SCORECARD_COMPARISONS, *EXTRA_GOLDEN))  # fmt: skip
    assert len(hits) == 7, hits
    assert all(len(ids) == 1 for ids in hits.values()), hits
    assert world["result"][1]["passed"] == 9


@then("the property test is required by its JUnit name")
def property_named(world: dict[str, Any]) -> None:
    hits = matches(requires_of(check_argv(world["line"], world["goal"])), (PROPERTY_TEST,))
    assert hits, "no --require in the property check"
    assert all(ids == [PROPERTY_TEST] for ids in hits.values()), hits
    assert world["result"][1]["passed"] == 1
