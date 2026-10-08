"""Sprint 3 CI changes (sre-devops-engineer lane).

ST-054 (SRE half, NFR-073): the 10 s "rules + domain" unit budget also measures the new
``analytics`` domain code (sprint-03 §3.2; TCR row 2026-10-06, accepted 2026-10-07).

ST-053 (c), G03-09 (c): the drill library lint (FR-140) is a merge gate. The ``drill-lint`` job
runs ``racket-drill-lint ../content/drills`` from ``backend`` and is part of ``ci-gate``
(blockers.md 2026-10-07, senior-ml-cv-engineer request).
"""

from __future__ import annotations

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit  # CI selects -m "unit or integration" (PE-R1S3-07)

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def jobs() -> dict:
    return yaml.safe_load(CI.read_text())["jobs"]


def drill_lint_runs() -> list[str]:
    return [step.get("run", "") for step in jobs()["drill-lint"]["steps"]]


def domain_paths() -> list[str]:
    return yaml.safe_load(CI.read_text())["env"]["DOMAIN_TEST_PATHS"].split()


# ---------------------------------------------------------------- negative cases first
def test_the_domain_budget_does_not_fall_back_to_the_whole_unit_suite() -> None:
    assert "tests/unit" not in domain_paths()
    assert "tests/unit/platform" not in domain_paths()  # infrastructure, 60 s budget


def test_the_drill_lint_job_can_not_pass_while_the_lint_fails() -> None:
    job = jobs()["drill-lint"]
    assert not job.get("continue-on-error", False)
    lint = [r for r in drill_lint_runs() if "racket-drill-lint" in r]
    assert len(lint) == 1, lint
    assert "|| true" not in lint[0] and ";" not in lint[0], lint[0]


# ---------------------------------------------------------------- positive cases
def test_the_domain_budget_covers_the_analytics_domain() -> None:
    assert "tests/unit/analytics" in domain_paths()
    assert (REPO_ROOT / "backend" / "tests" / "unit" / "analytics").is_dir()


def test_the_drill_lint_job_lints_the_library_with_the_locked_environment() -> None:
    job = jobs()["drill-lint"]
    assert job["runs-on"] == "ubuntu-24.04"
    assert job["timeout-minutes"] <= 5
    assert job["defaults"]["run"]["working-directory"] == "backend"
    runs = drill_lint_runs()
    assert "uv sync --locked" in runs
    assert "uv run --no-sync racket-drill-lint ../content/drills" in runs
    assert (REPO_ROOT / "content" / "drills").is_dir()


def test_the_drill_lint_job_is_a_merge_gate() -> None:
    assert "drill-lint" in jobs()["ci-gate"]["needs"]


# ---------------------------------------------------------------- CI run 37715576115 (PR #4)
# E2E-03-05 (ST-052) makes a labeller with the labeller-admin CLI of the stack under test
# (`web/e2e/helpers/sprint-03.ts` admin()): "E2E_ADMIN_CMD is not set" in Chromium and WebKit.
# The CLI runs in the api container of the job's own Compose stack, with absolute paths because
# the Playwright step runs in `web/`.
def test_the_gated_playwright_step_can_run_the_labeller_admin_cli() -> None:
    step = next(
        s for s in jobs()["e2e"]["steps"] if s.get("name", "").startswith("Playwright journeys")
    )
    cmd = step.get("env", {}).get("E2E_ADMIN_CMD", "")
    assert cmd, "E2E_ADMIN_CMD missing on the gated Playwright step"
    assert cmd.split()[:2] == ["docker", "compose"], cmd
    assert "-f ${{ github.workspace }}/infra/compose.yaml" in cmd
    assert "--env-file ${{ github.workspace }}/infra/env.example" in cmd
    assert cmd.endswith("exec -T api python -m racket.dataset.admin"), cmd
    # The helper splits on spaces and runs no shell, so quotes would reach docker verbatim.
    assert "'" not in cmd
    assert '"' not in cmd
