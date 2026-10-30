"""Binds tests/features/goal_method_integration_budget.feature (FIX-04-4a, VERIFY04R4-01).

Integration level: real bash runs the scorecard's G04-11 (d) block and CI's integration-job
steps as written, through the real scripts/ci/run_with_budget.py; only `uv` is a recorder, so
the comparison is of what each would execute, not of the text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from integration_budget_method import (
    MIGRATE,
    ci_budgeted_run,
    ci_script,
    g03_11_integration_line,
    g04_11_integration_script,
    integration_budget_problems,
    recorded_calls,
    uv_pytest_args,
)
from pytest_bdd import given, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("goal_method_integration_budget.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given("the integration budget line of the Sprint 3 method for G03-11")
def sprint_3_line(ctx: dict[str, Any]) -> None:
    ctx["line"] = g03_11_integration_line()


@when("it is compared with CI's budgeted backend-suites step")
def compare(ctx: dict[str, Any]) -> None:
    assert ci_budgeted_run()
    ctx["problems"] = integration_budget_problems(ctx["line"])


@then("the method is reported as timing one serial process")
def serial(ctx: dict[str, Any]) -> None:
    assert any("serial" in p for p in ctx["problems"]), ctx["problems"]


@then("the method is reported as timing another selection")
def other_selection(ctx: dict[str, Any]) -> None:
    assert any("selection" in p for p in ctx["problems"]), ctx["problems"]


@given("the integration budget block of the Sprint 4 method for G04-11")
def sprint_4_block(ctx: dict[str, Any]) -> None:
    ctx["block"] = g04_11_integration_script()


@when("the block and CI's migrate and budgeted steps run with the suite recorded, not run")
def run_both(ctx: dict[str, Any], tmp_path: Path) -> None:
    ctx["method"] = recorded_calls(ctx["block"], tmp_path, "method")
    ctx["ci"] = recorded_calls(ci_script(), tmp_path, "ci")


def budgeted(calls: list[list[str]]) -> tuple[int, list[str]]:
    """Index and pytest args of the budgeted run: the last pytest call that is not collect-only."""
    runs = [
        (i, args)
        for i, c in enumerate(calls)
        if (args := uv_pytest_args(c)) is not None and "--collect-only" not in args
    ]
    assert len(runs) == 1, calls
    return runs[0]


@then("the budgeted suite runs with the same pytest arguments as CI's, report paths aside")
def same_args(ctx: dict[str, Any]) -> None:
    assert budgeted(ctx["method"])[1] == budgeted(ctx["ci"])[1]


@then("the base database is migrated before the budgeted suite, outside the budget")
def migrated_first(ctx: dict[str, Any]) -> None:
    calls = ctx["method"]
    migrate = [i for i, c in enumerate(calls) if " ".join(c).endswith(MIGRATE)]
    assert len(migrate) == 1, calls
    assert migrate[0] < budgeted(calls)[0]
    assert "run_with_budget.py" not in " ".join(calls[migrate[0]])
