"""Sprint 3 CI changes (sre-devops-engineer lane).

ST-054 (SRE half, NFR-073): the 10 s "rules + domain" unit budget also measures the new
``analytics`` domain code (sprint-03 §3.2; TCR row 2026-10-06, accepted 2026-10-07).

ST-054 (PR #37, CI run 37867886176): the E2E job's 30 min timeout cancelled the listed
red-until step. The gated step took 14.8 min, and the 20 red-until tests (ST-054 adds 8, whose
failures run to their own 240-300 s timeouts while ST-047/ST-048 are not on main) need more
than the 30 min left. The listed step runs on 2 workers and the job has 45 min; the gated
step keeps CI's single worker (playwright.config.ts).

ST-053 (c), G03-09 (c): the drill library lint (FR-140) is a merge gate. The ``drill-lint`` job
runs ``racket-drill-lint ../content/drills`` from ``backend`` and is part of ``ci-gate``
(decisions/ST-053.md 2026-10-07, senior-ml-cv-engineer request).

ST-053 review round 1 (PE-R1-ST053-01): the lint also runs against the base branch's
``library.lock`` (``RACKET_DRILL_BASE_LOCK``), so a PR cannot delete or edit a locked drill
version by changing the lock with it. The base lock comes from the PR's base commit (the
previous commit on a push), fails closed on an unknown commit, and is an empty v1 lock only when
the base commit has no lock.
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


def jobs() -> dict:
    return yaml.safe_load(CI.read_text())["jobs"]


def drill_lint_step(needle: str) -> dict:
    steps = [s for s in jobs()["drill-lint"]["steps"] if needle in s.get("run", "")]
    assert len(steps) == 1, steps
    return steps[0]


def drill_lint_runs() -> list[str]:
    return [step.get("run", "") for step in jobs()["drill-lint"]["steps"]]


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


def test_the_drill_lint_job_can_not_pass_while_the_lint_fails() -> None:
    job = jobs()["drill-lint"]
    assert not job.get("continue-on-error", False)
    lint = [r for r in drill_lint_runs() if "racket-drill-lint" in r]
    assert len(lint) == 1, lint
    assert "|| true" not in lint[0] and ";" not in lint[0], lint[0]


def test_the_drill_lint_base_lock_step_fails_closed() -> None:
    step = drill_lint_step("git show")
    run = step["run"]
    assert "set -euo pipefail" in run
    assert "|| true" not in run
    # an unknown base commit is an error, not an empty lock
    assert 'git cat-file -e "${BASE_SHA}^{commit}"' in run
    assert not step.get("continue-on-error", False)


# ---------------------------------------------------------------- positive cases
def test_the_drill_lint_job_lints_against_the_base_branch_lock() -> None:
    job = jobs()["drill-lint"]
    checkout = job["steps"][0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"]["fetch-depth"] == 0  # the base commit is in the clone
    base = drill_lint_step("git show")
    sha = base["env"]["BASE_SHA"]
    assert "github.event.pull_request.base.sha" in sha
    assert "github.event.before" in sha
    path = base["env"]["RACKET_DRILL_BASE_LOCK"]
    assert 'git show "${BASE_SHA}:content/drills/library.lock"' in base["run"]
    assert '"drill-library-lock/v1"' in base["run"]
    lint = drill_lint_step("racket-drill-lint")
    assert lint["env"]["RACKET_DRILL_BASE_LOCK"] == path
    steps = job["steps"]
    assert steps.index(base) < steps.index(lint)


def test_the_domain_budget_covers_the_analytics_domain() -> None:
    assert "tests/unit/analytics" in domain_paths()
    assert (REPO_ROOT / "backend" / "tests" / "unit" / "analytics").is_dir()


def test_the_listed_red_until_step_runs_on_two_workers() -> None:
    assert "--workers=2" in e2e_run('--grep "@red-until-"')


def test_the_e2e_job_leaves_room_for_the_listed_step_after_the_gated_one() -> None:
    # Run 37867886176: setup 2.5 min + gated 14.8 min left < 13 min of the 30 for the listed step.
    assert e2e_job()["timeout-minutes"] >= 45


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
