"""Sprint 3 CI changes (sre-devops-engineer lane).

ST-054 (SRE half, NFR-073): the 10 s "rules + domain" unit budget also measures the new
``analytics`` domain code (sprint-03 §3.2; TCR row 2026-10-06, accepted 2026-10-07).

ST-054 (PR #37, CI run 37867886176): the E2E job's 30 min timeout cancelled the listed
red-until step. The gated step took 14.8 min, and the 20 red-until tests (ST-054 adds 8, whose
failures run to their own 240-300 s timeouts while ST-047/ST-048 are not on main) need more
than the 30 min left. The listed step runs on 2 workers and the job has 45 min; the gated
step keeps CI's single worker (playwright.config.ts).
"""

from __future__ import annotations

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit  # CI selects -m "unit or integration" (PE-R1S3-07)

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def e2e_job() -> dict:
    return yaml.safe_load(CI.read_text())["jobs"]["e2e"]


def e2e_run(needle: str) -> str:
    runs = [s["run"] for s in e2e_job()["steps"] if needle in s.get("run", "")]
    assert len(runs) == 1, runs
    return runs[0]


def domain_paths() -> list[str]:
    return yaml.safe_load(CI.read_text())["env"]["DOMAIN_TEST_PATHS"].split()


# ---------------------------------------------------------------- negative cases first
def test_the_domain_budget_does_not_fall_back_to_the_whole_unit_suite() -> None:
    assert "tests/unit" not in domain_paths()
    assert "tests/unit/platform" not in domain_paths()  # infrastructure, 60 s budget


def test_the_gated_e2e_step_keeps_the_single_ci_worker() -> None:
    gated = e2e_run('--grep-invert "@red-until-"')
    assert "--workers" not in gated
    assert "-j " not in gated


def test_the_e2e_job_timeout_is_not_unbounded() -> None:
    assert e2e_job()["timeout-minutes"] <= 45


# ---------------------------------------------------------------- positive cases
def test_the_domain_budget_covers_the_analytics_domain() -> None:
    assert "tests/unit/analytics" in domain_paths()
    assert (REPO_ROOT / "backend" / "tests" / "unit" / "analytics").is_dir()


def test_the_listed_red_until_step_runs_on_two_workers() -> None:
    assert "--workers=2" in e2e_run('--grep "@red-until-"')


def test_the_e2e_job_leaves_room_for_the_listed_step_after_the_gated_one() -> None:
    # Run 37867886176: setup 2.5 min + gated 14.8 min left < 13 min of the 30 for the listed step.
    assert e2e_job()["timeout-minutes"] >= 45
