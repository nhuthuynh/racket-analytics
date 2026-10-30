"""FIX-04-4a (VERIFY04R4-01, G04-11 d): the scorecard times the integration suite as CI's gate does.

Unit level: the commands are read from the scorecards and ci.yml and compared as text.
Negative cases first: the Sprint 3 serial line and near misses are caught.
"""

from __future__ import annotations

import pytest
from integration_budget_method import (
    MIGRATE,
    ci_budgeted_run,
    ci_env,
    g03_11_integration_line,
    g04_11_integration_script,
    g04_11_section,
    integration_budget_problems,
    logical_lines,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------- negative cases first
def test_the_inherited_sprint_3_serial_line_is_not_cis_integration_gate() -> None:
    problems = integration_budget_problems(g03_11_integration_line())
    assert any("serial" in p for p in problems), problems
    assert any("selection" in p for p in problems), problems


def test_parallel_workers_alone_are_not_enough_the_selection_must_be_cis() -> None:
    line = (
        "python3 ../scripts/ci/run_with_budget.py 600 -- env -u APP_ENV uv run pytest -q -n auto "
        "-m integration tests/integration "
        "--ignore=tests/integration/test_it_00_10_worker_sandbox_strict.py; echo rc=$?"
    )
    problems = integration_budget_problems(line)
    assert not any("serial" in p for p in problems), problems
    assert any("selection" in p for p in problems), problems
    assert any("ignores" in p for p in problems), problems


def test_a_larger_budget_is_caught() -> None:
    line = ci_budgeted_run().replace("run_with_budget.py 600 ", "run_with_budget.py 900 ")
    assert integration_budget_problems(line) == [
        f"budget is not CI's INTEGRATION_BUDGET_S ({ci_env()['INTEGRATION_BUDGET_S']} s)"
    ]


def test_timing_without_the_coverage_ci_times_is_caught() -> None:
    line = ci_budgeted_run().replace(" --cov ", " ")
    assert integration_budget_problems(line) == ["coverage inside the budget differs from CI's"]


# ---------------------------------------------------------------- the gate itself and the fix
def test_cis_own_budgeted_step_has_no_problems() -> None:
    assert integration_budget_problems(ci_budgeted_run()) == []


def test_g04_11_d_times_the_integration_suite_as_cis_gate_does() -> None:
    budget = ci_env()["INTEGRATION_BUDGET_S"]
    lines = [
        ln
        for ln in logical_lines(g04_11_integration_script())
        if f"run_with_budget.py {budget} " in ln
    ]
    assert len(lines) == 1, lines
    assert integration_budget_problems(lines[0]) == []


def test_g04_11_d_migrates_the_base_database_first_outside_the_budget() -> None:
    lines = logical_lines(g04_11_integration_script())
    migrate = [i for i, ln in enumerate(lines) if MIGRATE in ln]
    budgeted = [i for i, ln in enumerate(lines) if "run_with_budget.py" in ln]
    assert len(migrate) == 1, lines
    assert len(budgeted) == 1, lines
    assert migrate[0] < budgeted[0]
    assert "run_with_budget.py" not in lines[migrate[0]]


def test_g04_11_names_the_decision_that_replaces_the_inherited_line() -> None:
    section = g04_11_section()
    assert "FIX-04-4a" in section
    assert "VERIFY04R4-01" in section
