"""CI-REDUNTIL-HANG: the integration job keeps the object store's whole log when it fails or is
cancelled. Run 37961668800 was cancelled, so ``Service logs on failure`` (``if: failure()``) did
not run, and CI-IT0213-HANG had only ``--tail=200``; neither shows why the store took writes at
about 64 KiB/s.
"""

from __future__ import annotations

from typing import Any

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _steps() -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = yaml.safe_load(CI.read_text())["jobs"]["integration"]["steps"]
    return steps


def _logs_step() -> dict[str, Any]:
    return next(s for s in _steps() if s.get("name", "").startswith("Service logs"))


def test_service_logs_run_when_the_job_fails_or_is_cancelled() -> None:
    cond = _logs_step()["if"].replace(" ", "")
    assert "failure()" in cond, cond
    assert "cancelled()" in cond, cond


def test_the_whole_object_store_log_goes_into_the_uploaded_reports() -> None:
    run = _logs_step()["run"]
    assert "logs --no-color objectstore > reports/objectstore.log" in run, run
    upload = next(s for s in _steps() if s.get("with", {}).get("name") == "integration-reports")
    assert upload["with"]["path"].strip() == "reports/"
    assert _steps().index(_logs_step()) < _steps().index(upload)
