"""Binds tests/features/ci_domain_budget.feature (CI-DOMAIN-BUDGET; NFR-073; ADR 0049).

The scenario runs the real backend domain suite twice: once with the budgeted command
read from ci.yml, once in one process, and compares the junit results test by test. Bound in
infra/tests: the step is CI tooling (SRE lane) and reading ci.yml needs PyYAML.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from domain_budget import (
    ci_env,
    command,
    junit_outcomes,
    option,
    positionals,
    pytest_args,
    run_in_backend,
)
from pytest_bdd import given, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("ci_domain_budget.feature")


@pytest.fixture
def world() -> dict[str, Any]:
    return {}


@given("the backend unit suite on CI's DOMAIN_TEST_PATHS")
def the_suite() -> None:
    assert "tests/unit/analytics" in ci_env()["DOMAIN_TEST_PATHS"].split()


@when("the budgeted domain step's command from ci.yml runs")
def run_ci_command(world: dict[str, Any], tmp_path: Path) -> None:
    junit = tmp_path / "ci.xml"
    # `-v` after the step's `-q` restores the default verbosity, where xdist names its workers.
    extra = ["-v", "-p", "no:cacheprovider", f"--junitxml={junit}"]
    res = run_in_backend([*command(), *extra])
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
    m = re.search(r"\bcreated: (\d+)/\d+ workers", res.stdout)
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
