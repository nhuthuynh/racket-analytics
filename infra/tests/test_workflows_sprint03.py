"""Sprint 3 CI guards (sre-devops-engineer): CI-INTEG-BUDGET (NFR-073; ADR 0048).

The integration suite runs in parallel workers (pytest-xdist), each on its own session database
of the one Compose Postgres. Migration 0012 creates the cluster-wide role racket_media_worker
with check-then-create; four workers migrating at once on a fresh cluster collide on it (4 of 5
trials locally). The job migrates the base database once, before the workers and outside the
budget, the same way Compose's ``migrate`` service does, so the role exists before they start.
"""

from __future__ import annotations

import pytest
import yaml
from cluster import BUDGET_MARK, CI, MIGRATE_MODULE, integration_steps, migrate_step, step_index

pytestmark = pytest.mark.unit


def _index(needle: str) -> int:
    return step_index(integration_steps(), needle)


# ---------------------------------------------------------------- negative cases first
def test_the_integration_job_migrates_the_base_database() -> None:
    assert step_index(integration_steps(), MIGRATE_MODULE) >= 0, (
        "parallel workers on a fresh cluster race on cluster-wide roles without a migrate step"
    )


def test_the_migrate_step_is_not_inside_the_time_budget() -> None:
    assert "run_with_budget.py" not in migrate_step()["run"]


def test_the_migrate_step_runs_after_the_services_and_before_the_budgeted_suite() -> None:
    steps = integration_steps()
    migrate = step_index(steps, MIGRATE_MODULE)
    services = _index("up -d --wait postgres")
    endpoints = next(i for i, s in enumerate(steps) if "DATABASE_URL=" in s.get("run", ""))
    budgeted = _index(BUDGET_MARK)
    assert 0 <= services < endpoints < migrate < budgeted


def test_the_migrate_step_uses_the_locked_backend_environment_and_the_base_url() -> None:
    step = migrate_step()
    assert step.get("working-directory") == "backend"
    assert "uv run --no-sync python -m racket.platform.migrate" in step["run"]
    # the base DATABASE_URL from GITHUB_ENV; never a per-step override to another database
    assert "DATABASE_URL" not in step.get("env", {})
    assert "DATABASE_URL=" not in step["run"]


def test_the_migrate_step_is_the_one_compose_runs() -> None:
    compose = yaml.safe_load((CI.parents[2] / "infra" / "compose.yaml").read_text())
    assert compose["services"]["migrate"]["command"] == ["python", "-m", "racket.platform.migrate"]


def test_the_budget_and_parallel_workers_are_unchanged() -> None:
    run = integration_steps()[_index(BUDGET_MARK)]["run"]
    assert yaml.safe_load(CI.read_text())["env"]["INTEGRATION_BUDGET_S"] == "600"
    assert " -n auto" in run
    assert "--cov " in run
