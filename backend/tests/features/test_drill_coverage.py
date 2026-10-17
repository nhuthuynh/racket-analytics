"""CLI binding of tests/features/drill_coverage.feature (ST-059; FR-141): ``racket-drill-coverage``
on IT-04-13's gap fixture (negative) and on ``content/drills``. Written red first."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.integration.test_it_04_13_drill_coverage_cli import (
    GAP,
    GAP_CELL,
    LIBRARY,
    matrix_rows,
    run,
)

scenarios("drill_coverage.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given("no reviewed drill targets AN-05 for beginners with 2 or fewer players")
def gap_library(ctx: dict[str, Any]) -> None:
    assert GAP.is_dir(), f"missing fixture {GAP}"
    ctx["path"] = GAP


@given("the starter drill library")
def starter_library(ctx: dict[str, Any]) -> None:
    ctx["path"] = LIBRARY


@when("the coverage check runs")
def check_runs(ctx: dict[str, Any], capsys: pytest.CaptureFixture[str]) -> None:
    ctx["rc"], ctx["out"] = run(capsys, ctx["path"])


@then("it fails and names the empty cell")
def fails_naming_cell(ctx: dict[str, Any]) -> None:
    assert ctx["rc"] == 1, ctx["out"]
    assert f"FAIL {GAP_CELL}" in ctx["out"].splitlines(), ctx["out"]


@then("it passes and prints the matrix")
def passes_with_matrix(ctx: dict[str, Any]) -> None:
    assert ctx["rc"] == 0, ctx["out"]
    assert matrix_rows(ctx["out"]) == 18, ctx["out"]
    assert "FAIL" not in ctx["out"]
