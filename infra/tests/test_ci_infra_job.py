"""PE-R1S3-07 / QA-R1S3-07 (review round 1): what CI run 37639459765 at 48988f4 showed about the
``infra-tests`` job.

1. The job selects tests with a marker expression, so an infra test module without a ``unit`` or
   ``integration`` mark never runs on CI (``test_workflows_sprint03.py`` and
   ``test_dev_chrome.py`` were deselected: 14 tests, green only locally).
2. ``test_gitleaks_ignore.py`` checks that each ignored fingerprint names a commit in the
   repository. A shallow checkout (the ``actions/checkout`` default, depth 1) has no history, so
   the check failed on CI for the real commit ``9ca52fe``. The job fetches the full history.
"""

from __future__ import annotations

import subprocess
import sys

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
INFRA = REPO_ROOT / "infra"


def infra_job() -> dict:
    return yaml.safe_load(CI.read_text())["jobs"]["infra-tests"]


def marker_expression() -> str:
    runs = [s["run"] for s in infra_job()["steps"] if "pytest" in s.get("run", "")]
    assert len(runs) == 1, runs
    return runs[0].split('-m "', 1)[1].split('"', 1)[0]


# ---------------------------------------------------------------- negative cases first
def test_ci_marker_expression_deselects_no_infra_test() -> None:
    expr = marker_expression()
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "--co", "-q", "-p", "no:cacheprovider", "-m", expr],
        cwd=INFRA,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "deselected" not in res.stdout.splitlines()[-1], res.stdout.splitlines()[-1]


def test_infra_job_checkout_is_not_shallow() -> None:
    steps = infra_job()["steps"]
    checkouts = [s for s in steps if s.get("uses", "").startswith("actions/checkout@")]
    assert len(checkouts) == 1
    assert checkouts[0]["with"].get("fetch-depth") == 0


# ---------------------------------------------------------------- positive case
def test_infra_job_still_runs_unit_and_integration() -> None:
    assert marker_expression() == "unit or integration"
    assert infra_job()["defaults"]["run"]["working-directory"] == "infra"
