"""CI-DOMAIN-BUDGET guards (sre-devops-engineer; NFR-073; ADR 0049).

Main runs 37882972340 and 37918385248 stopped the domain unit suite at its 10 s budget (exit
124) with every test passing (8.97 s of pytest time plus start-up and collection). cProfile of
the suite: Hypothesis example generation is about 80% of it (some 30 property tests on the
default profile), in one process. The step now runs pytest-xdist workers. These guards keep
the fix from becoming a weaker gate: same budget, same selection, same profile, nothing skipped.
"""

from __future__ import annotations

import re

import pytest
from domain_budget import (
    BACKEND,
    budget_argv,
    ci_env,
    command,
    domain_step,
    narrowing,
    option,
    positionals,
    profile_set,
    pytest_args,
    unit_steps,
    warm_command,
    warm_step,
)

pytestmark = pytest.mark.unit

SELECTION = "unit and not red_until"


# ---------------------------------------------------------------- negative cases first
def test_the_domain_budget_is_not_raised() -> None:
    assert ci_env()["DOMAIN_UNIT_BUDGET_S"] == "10"
    assert budget_argv()[0] == "10"


def test_the_domain_step_narrows_nothing_by_itself() -> None:
    # `-k`, `-x`, `-p no:hypothesispytest` or `-o addopts=` would change what runs, not how fast.
    assert narrowing(pytest_args()) == []
    assert narrowing(["-k", "rules", "-p", "no:xdist", "-o", "addopts=", "--maxfail=1"]) == [
        "-k", "-p", "-o", "--maxfail=1"]  # fmt: skip
    assert "|| true" not in domain_step()["run"]
    assert "continue-on-error" not in domain_step()


def test_the_domain_step_keeps_the_default_hypothesis_profile() -> None:
    assert not profile_set()


def test_parallel_workers_are_not_the_hypothesis_ci_property_step() -> None:
    # The property step (>= 1,000 examples) keeps its own 90 s budget and its own command.
    prop = [s for s in unit_steps() if s.get("env", {}).get("HYPOTHESIS_PROFILE") == "ci"]
    assert len(prop) == 1
    assert '"$PROPERTY_BUDGET_S"' in prop[0]["run"]


def test_a_serial_domain_command_is_rejected_by_the_guard() -> None:
    serial = ('python3 ../scripts/ci/run_with_budget.py "$DOMAIN_UNIT_BUDGET_S" -- uv run '
              '--no-sync pytest -q -m "unit and not red_until" $DOMAIN_TEST_PATHS')  # fmt: skip
    assert option(pytest_args(serial), "-n") is None


def test_the_hypothesis_cache_warm_up_is_outside_every_budget() -> None:
    # PE-R1-DB-01: a cold .hypothesis/constants cost each CI worker ~1.3 s of AST parsing.
    # Warming it is not test time, like the bytecode warm-up; it must not run inside a budget.
    assert "run_with_budget.py" not in warm_step()["run"]
    assert "HYPOTHESIS_PROFILE" not in warm_step()["run"]
    assert "env" not in warm_step()


# ---------------------------------------------------------------- positive cases
def test_the_domain_step_selects_ci_domain_paths_and_the_unit_marker_only() -> None:
    args = pytest_args()
    assert option(args, "-m") == SELECTION
    assert positionals(args) == ci_env()["DOMAIN_TEST_PATHS"].split()
    assert "tests/unit/analytics" in positionals(args)


def test_the_domain_step_runs_on_parallel_workers() -> None:
    args = pytest_args()
    workers = option(args, "-n")
    assert workers == "auto", args  # one worker per runner core (ubuntu-24.04: 4)
    assert option(args, "--dist") == "worksteal", args  # long property tests finish early


def test_the_domain_step_still_times_start_up_and_collection() -> None:
    # The budget wraps the whole `uv run pytest` (interpreter, plugins, collection, workers).
    cmd = command()
    assert cmd[:4] == ["uv", "run", "--no-sync", "pytest"], cmd


def test_the_domain_step_keeps_its_wall_time_as_evidence() -> None:
    record = option(budget_argv(), "--json")
    assert record == "../reports/budget/domain-unit.json", budget_argv()
    uploads = [s for s in unit_steps() if s.get("uses", "").startswith("actions/upload-artifact@")]
    assert len(uploads) == 1, uploads
    upload = uploads[0]
    assert "reports/budget/domain-unit.json" in upload["with"]["path"].split()
    assert upload.get("if") == "always()"


def test_pytest_xdist_is_locked_for_the_backend() -> None:
    lock = (BACKEND / "uv.lock").read_text()
    assert re.search(r'^name = "pytest-xdist"$', lock, re.M)
    assert '"pytest-xdist' in (BACKEND / "pyproject.toml").read_text()


def test_the_hypothesis_cache_is_warmed_before_the_domain_step_on_its_selection() -> None:
    steps, cmd = unit_steps(), warm_command()
    assert steps.index(warm_step()) < steps.index(domain_step())
    assert cmd[:4] == ["uv", "run", "--no-sync", "python"], cmd
    assert cmd[4] == "../scripts/ci/warm_hypothesis_constants.py", cmd
    assert option(cmd, "-m") == SELECTION
    assert positionals(cmd[5:]) == positionals(pytest_args())
