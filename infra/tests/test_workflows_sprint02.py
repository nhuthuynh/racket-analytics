"""Sprint 2 CI guards (sre-devops-engineer): ST-039 Locust job.

ST-039 slice 3 puts the Locust baseline (backend/tests/perf/locustfile_sprint02.py) in CI. It
runs per PR and is part of ci-gate: availability and the correction round trip are gates now
(sprint-02 §8, NFR-013, NFR-041); read latency is a recorded baseline (NFR-010).
"""

from __future__ import annotations

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
LOCUSTFILE = REPO_ROOT / "backend" / "tests" / "perf" / "locustfile_sprint02.py"


def jobs() -> dict:
    return yaml.safe_load(CI.read_text())["jobs"]


def runs(job: str) -> str:
    return "\n".join(s.get("run", "") for s in jobs()[job]["steps"])


# ---------------------------------------------------------------- negative cases first
def test_perf_job_is_a_merge_gate() -> None:
    assert "perf-baseline" in jobs()["ci-gate"]["needs"]


def test_perf_job_never_installs_an_unpinned_locust() -> None:
    text = runs("perf-baseline")
    assert "locust==2.46.7" in text
    assert "pip install locust\n" not in text
    assert "locust>=" not in text


def test_perf_verdict_decides_not_locusts_exit_code() -> None:
    # Locust exits 1 on any single failed request; the verdict owns the thresholds and fails
    # closed when the run produced no stats.
    text = runs("perf-baseline")
    assert "scripts/ci/perf_verdict.py" in text
    assert "--rps 50" in text
    assert '--summary "$GITHUB_STEP_SUMMARY"' in text


def test_perf_job_loads_the_api_port_and_seeds_through_the_https_origin() -> None:
    text = runs("perf-baseline")
    assert "--host http://127.0.0.1:8000" in text  # server-side, as NFR-010 defines it
    step_env = {
        k: v for s in jobs()["perf-baseline"]["steps"] for k, v in (s.get("env") or {}).items()
    }
    assert step_env.get("RA_ORIGIN") == "https://localhost:3000"
    assert "RA_CACERT" in step_env


def test_perf_job_runs_fifty_users_for_sixty_seconds() -> None:
    text = runs("perf-baseline")
    assert "-u 51 -r 51 -t 60s" in text  # 50 readers at 1 RPS + 1 correction user


def test_perf_job_keeps_its_reports_and_has_a_timeout() -> None:
    job = jobs()["perf-baseline"]
    assert job["timeout-minutes"] <= 20
    uploads = [s for s in job["steps"] if "upload-artifact" in s.get("uses", "")]
    assert uploads, "no artifact upload"
    assert uploads[0]["if"] == "always()"
    assert uploads[0]["with"]["path"] == "reports/perf/"


def test_locustfile_routes_come_from_the_harness_contract_only() -> None:
    text = LOCUSTFILE.read_text()
    assert "import tagcontract as k" in text
    assert "/score-sheet" not in text  # routes live only in scripts/measure/tagcontract.py
