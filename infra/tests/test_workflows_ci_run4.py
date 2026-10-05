"""Regression guard for CI run 37376048821 on PR #1 (sprint-01 head 7de88fb).

The integration job selects `-m "unit or integration or scenario or regression"`. The
`@nightly @slow` scenario "Nightly differential check" (100,000 sequences, NFR-002b) is also
a `scenario`, so the per-PR job ran it and pytest-timeout killed it at 120 s
("Failed: Timeout (>120.0s)"). By its tags it belongs to the nightly quality job (ST-024),
which runs the same 100,000-sequence comparison (`python -m tests.oracle.differential
--sequences 100000`). The per-PR selections exclude `nightly`, as the local goal-scorecard
method G01-09 already does. The nightly workflow must keep running the 100,000 sequences.
"""

from __future__ import annotations

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

WORKFLOWS = REPO_ROOT / ".github" / "workflows"
PER_PR_BACKEND_JOBS = ("integration", "flaky-report")


def _job_runs(workflow: str, job: str) -> str:
    steps = yaml.safe_load((WORKFLOWS / workflow).read_text())["jobs"][job]["steps"]
    return "\n".join(step.get("run", "") for step in steps)


# ---------------------------------------------------------------- negative cases first
@pytest.mark.parametrize("job", PER_PR_BACKEND_JOBS)
def test_per_pr_backend_selection_never_runs_nightly_tests(job: str) -> None:
    runs = _job_runs("ci.yml", job)
    selections = [line for line in runs.splitlines() if "pytest" in line and " -m " in line]
    assert selections, f"{job}: no marker-selected pytest call"
    for line in selections:
        assert "not nightly" in line, f"{job} runs @nightly tests per PR: {line.strip()}"


def test_nightly_workflow_still_runs_the_full_differential_oracle() -> None:
    runs = _job_runs("nightly-quality.yml", "oracle")
    assert "tests.oracle.differential" in runs
    assert "--sequences 100000" in runs
