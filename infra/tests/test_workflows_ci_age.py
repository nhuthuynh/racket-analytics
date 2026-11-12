"""ST-077: the backend suite jobs install ``age`` (IT-05-05; NFR-063.1; PE-PLAN05-06).

IT-05-05 (``backend/tests/integration/test_it_05_data_classification.py``) takes a real backup
set with the ST-076a service (``pg_dump`` streamed through ``age``) and fails, never skips,
when ``age`` is missing. So every job that runs the backend integration suite installs it and
checks it is there, as ``test_workflows_ci_run2.py`` does for ffprobe.
"""

from __future__ import annotations

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
BACKEND_SUITE_JOBS = ("integration", "flaky-report")


def _job_runs(job: str) -> str:
    steps = yaml.safe_load(CI.read_text())["jobs"][job]["steps"]
    return "\n".join(step.get("run", "") for step in steps)


@pytest.mark.parametrize("job", BACKEND_SUITE_JOBS)
def test_backend_suite_jobs_install_and_check_age(job: str) -> None:
    runs = _job_runs(job)
    installs = [line for line in runs.splitlines() if "apt-get install" in line]
    assert any(" age" in line.split("--no-install-recommends", 1)[-1] for line in installs), job
    assert "age --version" in runs, f"{job}: age presence not checked"
