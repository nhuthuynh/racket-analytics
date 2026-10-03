"""Review round 1 CI guards (QA-R1-03, QA-R1-07).

* IT-00-10 needs the Compose ``worker`` container, which only the e2e job starts. It runs
  there, with Compose reading ``infra/env.example`` (``COMPOSE_ENV_FILES``); the jobs that
  start only backing services leave it out instead of failing by construction.
* ST-004 asks for the Hypothesis ``ci`` profile (>= 1,000 examples) in CI. It gets its own
  budgeted step; the NFR-073 10 s domain budget keeps applying to the default profile.
"""

from __future__ import annotations

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
IT_00_10 = "tests/integration/test_it_00_10_worker_sandbox.py"


def jobs() -> dict:
    return yaml.safe_load(CI.read_text())["jobs"]


def runs(job: str) -> list[dict]:
    return [s for s in jobs()[job]["steps"] if "run" in s]


def backend_suite_steps(job: str) -> list[dict]:
    return [s for s in runs(job) if "integration or scenario or regression" in s["run"]]


# ---------------------------------------------------------------- negative cases first
@pytest.mark.parametrize("job", ["integration", "flaky-report"])
def test_jobs_without_the_worker_container_do_not_run_it_00_10(job: str) -> None:
    steps = backend_suite_steps(job)
    assert steps, f"{job}: backend suite step not found"
    for step in steps:
        assert f"--ignore={IT_00_10}" in step["run"], step["run"]


def test_the_domain_budget_step_runs_the_default_hypothesis_profile() -> None:
    step = next(s for s in runs("python-unit") if "DOMAIN_UNIT_BUDGET_S" in s["run"])
    assert "HYPOTHESIS_PROFILE" not in step["run"]
    assert "HYPOTHESIS_PROFILE" not in step.get("env", {})


# ---------------------------------------------------------------- positive cases
def test_it_00_10_runs_in_the_e2e_job_after_the_full_stack_is_up() -> None:
    steps = jobs()["e2e"]["steps"]
    names = [s.get("name", "") for s in steps]
    start = names.index("Start the full stack")
    it = next(i for i, s in enumerate(steps) if IT_00_10 in s.get("run", ""))
    assert it > start
    env = steps[it].get("env", {})
    assert env.get("COMPOSE_ENV_FILES", "").endswith("infra/env.example")
    assert env.get("CI") in (None, "true")  # a missing stack must fail, never skip


def test_property_tests_run_with_the_ci_profile_under_their_own_budget() -> None:
    step = next(s for s in runs("python-unit") if s.get("env", {}).get("HYPOTHESIS_PROFILE"))
    assert step["env"]["HYPOTHESIS_PROFILE"] == "ci"
    assert "PROPERTY_BUDGET_S" in step["run"]
    assert "run_with_budget.py" in step["run"]
    assert int(yaml.safe_load(CI.read_text())["env"]["PROPERTY_BUDGET_S"]) <= 120
