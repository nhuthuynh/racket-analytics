"""Binding of tests/features/goal_metric_markers.feature (FIX-04-2c; G04-03 a and c): a real
pytest run of the coaching unit suites with ``--junitxml``, read by ``junit_rate.py`` as the
scorecard §4 runs it. Written red first."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.integration.test_goal_metric_g04_03_report import marker_run, rate

scenarios("goal_metric_markers.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given(parsers.parse('the JUnit report of a run of "-m {marker}" on the coaching unit suites'))
def report_of(ctx: dict[str, Any], marker: str, tmp_path: Path) -> None:
    ctx["report"] = marker_run(marker, tmp_path / f"{marker}.xml")


@when(parsers.parse('the pass rate is read requiring the marker "{marker}"'))
def read_rate(ctx: dict[str, Any], marker: str) -> None:
    ctx["rc"], ctx["result"] = rate(ctx["report"], "--require-marker", marker)


@then("the pass rate check fails")
def check_fails(ctx: dict[str, Any]) -> None:
    assert ctx["rc"] == 1, ctx["result"]
    assert ctx["result"]["ok"] is False


@then("the pass rate check passes")
def check_passes(ctx: dict[str, Any]) -> None:
    assert ctx["rc"] == 0, ctx["result"]
    assert ctx["result"]["ok"] is True


@then(parsers.parse('it names the missing marker "{marker}"'))
def names_missing(ctx: dict[str, Any], marker: str) -> None:
    assert ctx["result"]["missing"] == [f"marker:{marker}"]


@then(parsers.re(r"(?P<n>\d+) tests? (is|are) selected, every one passed and none skipped"))
def counts(ctx: dict[str, Any], n: str) -> None:
    r = ctx["result"]
    assert (r["selected"], r["passed"], r["failed"], r["skipped"]) == (int(n), int(n), 0, 0)
