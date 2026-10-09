"""Binds tests/features/ci_domain_budget.feature (CI-DOMAIN-BUDGET; NFR-073; ADR 0049).

The second scenario runs the real backend domain suite twice: once with the budgeted command
read from ci.yml, once in one process, and compares the junit results test by test. Bound in
infra/tests: the step is CI tooling (SRE lane) and the wiring checks need PyYAML.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from domain_budget import (
    budget_argv,
    ci_env,
    command,
    domain_step,
    junit_outcomes,
    option,
    positionals,
    pytest_args,
    run_in_backend,
)
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("ci_domain_budget.feature")

NARROWING = ("-k", "--deselect", "--ignore", "--ignore-glob", "--lf", "--sw", "-x", "--maxfail")


@pytest.fixture
def world() -> dict[str, Any]:
    return {}


@given("the CI workflow")
def the_workflow() -> None:
    domain_step()  # exactly one budgeted domain step


@then(parsers.parse("the domain budget is {seconds:d} seconds"))
def the_budget(seconds: int) -> None:
    assert ci_env()["DOMAIN_UNIT_BUDGET_S"] == str(seconds)
    assert budget_argv()[0] == str(seconds)


@then(parsers.parse('the budgeted domain step selects "{marker}" on CI\'s DOMAIN_TEST_PATHS only'))
def the_selection(marker: str) -> None:
    args = pytest_args()
    assert option(args, "-m") == marker
    assert positionals(args) == ci_env()["DOMAIN_TEST_PATHS"].split()


@then("the budgeted domain step deselects, ignores and skips nothing by itself")
def nothing_narrowed() -> None:
    args = pytest_args()
    assert not [a for a in args if a.split("=", 1)[0] in NARROWING], args
    assert "-o" not in args, args
    assert not any(a.startswith("-p") for a in args), args


@then("the budgeted domain step uses the default Hypothesis profile")
def default_profile() -> None:
    assert "HYPOTHESIS_PROFILE" not in domain_step()["run"]
    assert "HYPOTHESIS_PROFILE" not in domain_step().get("env", {})


@given("the backend unit suite on CI's DOMAIN_TEST_PATHS")
def the_suite() -> None:
    assert "tests/unit/analytics" in ci_env()["DOMAIN_TEST_PATHS"].split()


@when("the budgeted domain step's command from ci.yml runs")
def run_ci_command(world: dict[str, Any], tmp_path: Path) -> None:
    junit = tmp_path / "ci.xml"
    res = run_in_backend([*command(), "-p", "no:cacheprovider", f"--junitxml={junit}"])
    world["ci"] = (res, junit)


@when("the same selection runs in one process")
def run_serial(world: dict[str, Any], tmp_path: Path) -> None:
    junit = tmp_path / "serial.xml"
    args = pytest_args()
    serial = ["uv", "run", "--no-sync", "pytest", "-q", "-m", option(args, "-m") or "",
              *positionals(args), "-p", "no:cacheprovider", f"--junitxml={junit}"]  # fmt: skip
    world["serial"] = (run_in_backend(serial), junit)


@then("the step ran on more than one worker")
def more_than_one_worker(world: dict[str, Any]) -> None:
    res, _ = world["ci"]
    m = re.search(r"\b(\d+) workers \[\d+ items\]", res.stdout)
    assert m, res.stdout[-2000:]
    assert int(m.group(1)) > 1, m.group(0)


@then("both runs executed the same test ids with the same outcomes and none failed")
def same_results(world: dict[str, Any]) -> None:
    (ci_res, ci_xml), (serial_res, serial_xml) = world["ci"], world["serial"]
    assert ci_res.returncode == 0, ci_res.stdout[-3000:]
    assert serial_res.returncode == 0, serial_res.stdout[-3000:]
    ci, serial = junit_outcomes(ci_xml), junit_outcomes(serial_xml)
    assert len(ci) > 1000, len(ci)
    assert set(ci) == set(serial), sorted(set(ci) ^ set(serial))[:20]
    assert ci == serial, {k: (ci[k], serial[k]) for k in ci if ci[k] != serial[k]}
    assert not [k for k, v in ci.items() if v in {"failed", "error"}]
