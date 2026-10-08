"""Binds tests/features/ci_integ_budget.feature (CI-INTEG-BUDGET; NFR-073; ADR 0048).

Real Postgres clusters (scripts/dev-postgres.sh), the real migration chain plus one fixture
revision in the 0012 pattern, the real ci.yml. Bound in infra/tests: the integration job is CI
tooling (SRE lane) and the wiring checks need PyYAML, which the backend does not depend on.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from cluster import (
    BUDGET_MARK,
    CI,
    fresh_cluster,
    integration_steps,
    migrate_module,
    run_helper,
    step_index,
    unique_role,
)
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("ci_integ_budget.feature")

DUPLICATE_ROLE = "pg_authid_rolname_index"


@pytest.fixture
def world() -> dict[str, Any]:
    return {}


@given("a fresh Postgres cluster", target_fixture="base_url")
def base_url(tmp_path: Path):
    with fresh_cluster(tmp_path / "pg") as url:
        yield url


@given("a migration that creates a role for the whole cluster if it is missing")
def cluster_role(world: dict[str, Any]) -> None:
    world["role"] = unique_role()


@when("the integration job's migrate step runs on the base database")
def migrate_step_runs(base_url: str, world: dict[str, Any]) -> None:
    world["step"] = run_helper("step", base_url, world["role"], migrate_module())


@when(
    parsers.parse("{n:d} test workers each migrate their own session database at the same moment")
)
def workers_migrate(base_url: str, world: dict[str, Any], n: int) -> None:
    world["workers"] = run_helper("workers", base_url, world["role"], str(n))


@then("at least one worker fails on the duplicate role")
def a_worker_fails(world: dict[str, Any]) -> None:
    out = world["workers"]
    assert out["failed"], out
    assert all(DUPLICATE_ROLE in f for f in out["failed"]), out
    assert out["at_head"] == out["workers"] - len(out["failed"])


@then("every worker's database reaches the migration head")
def every_worker_at_head(world: dict[str, Any]) -> None:
    assert world["step"]["rc"] == 0, world["step"]
    assert world["step"]["base_version"] == "ci_cluster_role", world["step"]
    out = world["workers"]
    assert out["failed"] == [], out
    assert out["at_head"] == out["workers"]


# ---------------------------------------------------------------- the workflow
@given("the CI workflow", target_fixture="steps")
def ci_workflow() -> list[dict[str, Any]]:
    return integration_steps()


def _selection(run: str) -> list[str]:
    """The pytest selection of a backend-suite command: marker expression and ignores."""
    words = run.replace("\\\n", " ").split()
    sel = [w for w in words if w.startswith("--ignore=")]
    m = run.index('-m "')
    sel.append(run[m : run.index('"', m + 4) + 1])
    return sorted(sel)


@then("the budgeted step runs the nightly flaky-report selection with branch coverage")
def same_selection(steps: list[dict[str, Any]]) -> None:
    budgeted = steps[step_index(steps, BUDGET_MARK)]["run"]
    flaky = next(s["run"] for s in yaml.safe_load(CI.read_text())["jobs"]["flaky-report"]["steps"]
                 if '-m "(unit or integration' in s.get("run", ""))  # fmt: skip
    assert _selection(budgeted) == _selection(flaky)
    assert " --cov " in budgeted.replace("\\\n", " ")
    assert "--cov-report=xml:../reports/coverage-backend.xml" in budgeted
    pyproject = (Path(CI).parents[2] / "backend" / "pyproject.toml").read_text()
    assert "branch = true" in pyproject.split("[tool.coverage.run]", 1)[1].split("[", 1)[0]


@then("the integration budget is 600 seconds")
def budget_is_600() -> None:
    assert yaml.safe_load(CI.read_text())["env"]["INTEGRATION_BUDGET_S"] == "600"


@then("the migrate step runs before the budgeted step and outside the budget")
def migrate_before_budget(steps: list[dict[str, Any]]) -> None:
    from cluster import MIGRATE_MODULE

    migrate = step_index(steps, MIGRATE_MODULE)
    budgeted = step_index(steps, BUDGET_MARK)
    assert 0 <= migrate < budgeted, "the base database must be migrated before the workers start"
    assert "run_with_budget.py" not in steps[migrate]["run"]
