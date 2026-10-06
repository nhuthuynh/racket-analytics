"""Regression guards for CI run 37298471332 on sprint-01 (head 2390e9a, QA-R1-06).

* The domain unit suite (NFR-073, < 10 s) was killed at its budget on a fresh runner: the
  first ~7 s went to compiling bytecode for the dependencies, the source and pytest's
  rewritten test modules, not to running tests. Locally, with an empty bytecode cache the
  same suite takes 11.1 s wall; after `pytest --collect-only` it takes 6.8 s. The job warms
  the bytecode cache with an unbudgeted collect-only step before the first budgeted step,
  so the budget measures the warm feedback loop a developer sees (decision-log row).
"""

from __future__ import annotations

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def unit_steps() -> list[dict]:
    return yaml.safe_load(CI.read_text())["jobs"]["python-unit"]["steps"]


def _index(steps: list[dict], needle: str) -> int:
    for i, step in enumerate(steps):
        if needle in step.get("run", ""):
            return i
    return -1


# ---------------------------------------------------------------- negative cases first
def test_first_budgeted_step_never_pays_the_cold_bytecode_cost() -> None:
    steps = unit_steps()
    first_budget = _index(steps, "run_with_budget.py")
    assert first_budget >= 0, "no budgeted step in python-unit"
    warm = _index(steps, "--collect-only")
    assert 0 <= warm < first_budget, "python-unit needs a collect-only warm-up before the budget"


def test_warm_up_is_not_itself_budgeted_and_covers_every_unit_test() -> None:
    steps = unit_steps()
    run = steps[_index(steps, "--collect-only")]["run"]
    assert "run_with_budget.py" not in run
    assert "-m unit" in run
    # whole backend unit set, so the 60 s backend step is warm too
    assert "$DOMAIN_TEST_PATHS" not in run


# The integration job of the same run: 44 failed, 14 errors. Two causes are the CI
# environment, not the code: no `ffprobe` on the runner ("ffprobe binary not found",
# probe stage FAILED -> "We could not read this video") and no `MAILPIT_API_URL`
# ("MAILPIT_API_URL is not set in CI", every IT-01-01 magic-link test).
BACKEND_SUITE_JOBS = ("integration", "flaky-report")


def _job_runs(job: str) -> str:
    steps = yaml.safe_load(CI.read_text())["jobs"][job]["steps"]
    return "\n".join(step.get("run", "") for step in steps)


@pytest.mark.parametrize("job", BACKEND_SUITE_JOBS)
def test_backend_suite_jobs_never_run_without_ffprobe(job: str) -> None:
    runs = _job_runs(job)
    assert "apt-get install" in runs, f"{job}: ffprobe not installed"
    assert "ffmpeg" in runs, f"{job}: ffprobe not installed"
    assert "ffprobe -version" in runs, f"{job}: ffprobe presence not checked"


@pytest.mark.parametrize("job", BACKEND_SUITE_JOBS)
def test_backend_suite_jobs_point_tests_at_mailpit(job: str) -> None:
    runs = _job_runs(job).replace('"', "")
    assert "MAILPIT_API_URL=http://127.0.0.1:${MAILPIT_UI_HOST_PORT}" in runs, job
    assert "MAIL_SMTP_URL=smtp://127.0.0.1:${MAILPIT_SMTP_HOST_PORT}" in runs, job
