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
    option,
    positionals,
    pytest_args,
    unit_steps,
)

pytestmark = pytest.mark.unit

SELECTION = "unit and not red_until"
NARROWING = ("-k", "--deselect", "--ignore", "--ignore-glob", "--lf", "--last-failed", "--sw",
             "--stepwise", "-x", "--exitfirst", "--maxfail", "--co", "--collect-only")  # fmt: skip


# ---------------------------------------------------------------- negative cases first
def test_the_domain_budget_is_not_raised() -> None:
    assert ci_env()["DOMAIN_UNIT_BUDGET_S"] == "10"
    assert budget_argv()[0] == "10"


def test_the_domain_step_narrows_nothing_by_itself() -> None:
    args = pytest_args()
    for flag in NARROWING:
        assert not any(a == flag or a.startswith(flag + "=") for a in args), (flag, args)
    run = domain_step()["run"]
    assert "|| true" not in run
    assert "continue-on-error" not in domain_step()


def test_the_domain_step_does_not_disable_plugins_or_override_ini() -> None:
    # `-p no:hypothesispytest` or `-o addopts=` would change what runs, not how fast.
    args = pytest_args()
    assert "-o" not in args, args
    assert not any(a.startswith("-p") for a in args), args


def test_the_domain_step_keeps_the_default_hypothesis_profile() -> None:
    step = domain_step()
    assert "HYPOTHESIS_PROFILE" not in step["run"]
    assert "HYPOTHESIS_PROFILE" not in step.get("env", {})


def test_parallel_workers_are_not_the_hypothesis_ci_property_step() -> None:
    # The property step (>= 1,000 examples) keeps its own 90 s budget and its own command.
    prop = [s for s in unit_steps() if s.get("env", {}).get("HYPOTHESIS_PROFILE") == "ci"]
    assert len(prop) == 1
    assert '"$PROPERTY_BUDGET_S"' in prop[0]["run"]


def test_a_serial_domain_command_is_rejected_by_the_guard() -> None:
    serial = ('python3 ../scripts/ci/run_with_budget.py "$DOMAIN_UNIT_BUDGET_S" -- uv run '
              '--no-sync pytest -q -m "unit and not red_until" $DOMAIN_TEST_PATHS')  # fmt: skip
    assert option(pytest_args(serial), "-n") is None


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
