"""Review round 2 CI guard (QA-R2-02): the strict IT-00-10 probe (with its ``api`` positive
control) needs the full Compose stack, so it runs in the e2e job beside the first IT-00-10
file and is left out of the jobs that start only backing services."""

from __future__ import annotations

import pytest
from test_workflows_round1 import backend_suite_steps, jobs

pytestmark = pytest.mark.unit

IT_00_10_STRICT = "tests/integration/test_it_00_10_worker_sandbox_strict.py"


@pytest.mark.parametrize("job", ["integration", "flaky-report"])
def test_jobs_without_the_full_stack_do_not_run_the_strict_probe(job: str) -> None:
    steps = backend_suite_steps(job)
    assert steps
    for step in steps:
        assert f"--ignore={IT_00_10_STRICT}" in step["run"], step["run"]


def test_the_strict_probe_runs_in_the_e2e_job_after_the_full_stack_is_up() -> None:
    steps = jobs()["e2e"]["steps"]
    names = [s.get("name", "") for s in steps]
    start = names.index("Start the full stack")
    it = next(i for i, s in enumerate(steps) if IT_00_10_STRICT in s.get("run", ""))
    assert it > start
    env = steps[it].get("env", {})
    assert env.get("COMPOSE_ENV_FILES", "").endswith("infra/env.example")
    assert env.get("CI") in (None, "true")
