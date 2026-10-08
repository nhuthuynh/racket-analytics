"""CI-PR-GATE: `scripts/ci/merge_ready.py` refuses a merge into `main` unless every CI job
incl. ci-gate succeeded on the PR's head SHA and the principal-engineer and a senior reviewer
both posted "Verdict: APPROVE" on that SHA (PO rule 2026-10-07; user request 2026-10-08).

Unit tests drive the pure `evaluate()` rule (no I/O). Integration tests run the script as the
orchestrator does, over HTTP against a local GitHub API stub (`github_stub.py`).
Negative cases first.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from types import ModuleType
from typing import Any

import pytest
from conftest import SCRIPTS_DIR
from github_stub import (
    HEAD_SHA,
    OLD_SHA,
    PR_NUMBER,
    REPO,
    GitHubStub,
    approvals,
    check_run,
    green_runs,
    review,
    serve,
)

SCRIPT = SCRIPTS_DIR / "ci" / "merge_ready.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("merge_ready", SCRIPT)
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pr(sha: str = HEAD_SHA, state: str = "open", base: str = "main") -> dict[str, Any]:
    return {"number": PR_NUMBER, "state": state, "head": {"sha": sha}, "base": {"ref": base}}


def evaluate(
    runs: list[dict[str, Any]] | None = None,
    reviews: list[dict[str, Any]] | None = None,
    the_pr: dict[str, Any] | None = None,
    sha: str = HEAD_SHA,
) -> list[str]:
    return load().evaluate(
        the_pr or pr(),
        sha,
        green_runs() if runs is None else runs,
        approvals() if reviews is None else reviews,
    )


# ======================================================================= unit: refusals
@pytest.mark.unit
def test_a_failed_job_blocks_the_merge() -> None:
    runs = [
        *green_runs(),
        check_run("Integration, scenario and regression suites", "failure", run_id=20),
    ]
    reasons = evaluate(runs=runs)
    assert any(
        "Integration, scenario and regression suites" in r and "failure" in r for r in reasons
    )


@pytest.mark.unit
def test_an_approval_on_an_older_sha_does_not_count() -> None:
    reviews = [
        review("principal-engineer", "APPROVE", HEAD_SHA, 1),
        review("senior-qa-engineer", "APPROVE", OLD_SHA, 2),
    ]
    reasons = evaluate(reviews=reviews)
    assert any("senior" in r and "head" in r for r in reasons)


@pytest.mark.unit
def test_a_missing_senior_verdict_blocks_the_merge() -> None:
    reasons = evaluate(reviews=[review("principal-engineer", "APPROVE")])
    assert any("senior" in r for r in reasons)


@pytest.mark.unit
def test_a_missing_principal_verdict_blocks_the_merge() -> None:
    reasons = evaluate(reviews=[review("senior-backend-engineer", "APPROVE")])
    assert any("principal-engineer" in r for r in reasons)


@pytest.mark.unit
def test_a_pending_ci_gate_blocks_the_merge() -> None:
    runs = [r for r in green_runs() if r["name"] != "ci-gate"]
    runs.append(check_run("ci-gate", conclusion=None, status="in_progress", run_id=30))
    reasons = evaluate(runs=runs)
    assert any("ci-gate" in r and "in_progress" in r for r in reasons)


@pytest.mark.unit
def test_no_ci_gate_run_at_all_blocks_the_merge() -> None:
    reasons = evaluate(runs=[r for r in green_runs() if r["name"] != "ci-gate"])
    assert any("ci-gate" in r for r in reasons)


@pytest.mark.unit
def test_a_skipped_ci_gate_blocks_the_merge() -> None:
    runs = [r for r in green_runs() if r["name"] != "ci-gate"]
    runs.append(check_run("ci-gate", conclusion="skipped", run_id=31))
    assert any("ci-gate" in r for r in evaluate(runs=runs))


@pytest.mark.unit
def test_the_latest_verdict_of_a_role_wins_changes_requested_after_approve() -> None:
    reviews = [
        *approvals(),
        review("principal-engineer", "CHANGES REQUESTED", HEAD_SHA, 9, "2026-10-08T11:00:00Z"),
    ]
    assert any("principal-engineer" in r for r in evaluate(reviews=reviews))


@pytest.mark.unit
def test_changes_requested_by_any_senior_on_the_head_blocks() -> None:
    reviews = [*approvals(), review("senior-backend-engineer", "CHANGES REQUESTED", HEAD_SHA, 5)]
    assert any("senior-backend-engineer" in r for r in evaluate(reviews=reviews))


@pytest.mark.unit
def test_a_verdict_not_at_the_start_of_the_body_does_not_count() -> None:
    late = review("senior-qa-engineer", "APPROVE", HEAD_SHA, 2)
    late["body"] = "Looks fine.\n" + late["body"]
    reasons = evaluate(reviews=[review("principal-engineer", "APPROVE"), late])
    assert any("senior" in r for r in reasons)


@pytest.mark.unit
def test_a_rerun_that_failed_after_a_success_blocks() -> None:
    runs = [*green_runs(), check_run("ci-gate", "failure", run_id=99)]
    assert any("ci-gate" in r and "failure" in r for r in evaluate(runs=runs))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("the_pr", "word"),
    [(pr(sha=OLD_SHA), "head"), (pr(state="closed"), "open"), (pr(base="sprint-03"), "main")],
)
def test_the_sha_must_be_the_head_of_an_open_pr_into_main(
    the_pr: dict[str, Any], word: str
) -> None:
    assert any(word in r for r in evaluate(the_pr=the_pr))


# ======================================================================= unit: allowed
@pytest.mark.unit
def test_all_green_and_both_approvals_on_the_head_allow_the_merge() -> None:
    assert evaluate() == []


@pytest.mark.unit
def test_a_successful_rerun_replaces_an_earlier_failure() -> None:
    runs = [check_run("ci-gate", "failure", run_id=1)] + [
        r | {"id": r["id"] + 100} for r in green_runs()
    ]
    assert evaluate(runs=runs) == []


# ======================================================================= integration
def run_script(
    stub: GitHubStub, sha: str = HEAD_SHA, token: str | None = None
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in {"GITHUB_TOKEN", "GH_TOKEN"}}
    env["GITHUB_API_URL"] = stub.url
    if token:
        env["GITHUB_TOKEN"] = token
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", REPO, "--pr", str(PR_NUMBER), "--sha", sha],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )


@pytest.mark.integration
def test_script_refuses_a_failed_job_over_http_and_exits_1() -> None:
    stub = GitHubStub(check_runs=[*green_runs(), check_run("E2E", "failure", run_id=50)])
    with serve(stub):
        res = run_script(stub)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "E2E" in res.stdout
    assert "merge-ready: no" in res.stdout


@pytest.mark.integration
def test_script_refuses_a_stale_sha_over_http() -> None:
    with serve(GitHubStub()) as stub:
        res = run_script(stub, sha=OLD_SHA)
    assert res.returncode == 1
    assert "merge-ready: no" in res.stdout


@pytest.mark.integration
def test_script_exits_2_when_the_api_cannot_be_read() -> None:
    stub = GitHubStub(pr={"message": "x"})
    stub.url = "http://127.0.0.1:9"  # nothing listens on the discard port
    res = run_script(stub)
    assert res.returncode == 2
    assert "merge-ready: unknown" in res.stdout


@pytest.mark.integration
def test_script_allows_the_merge_following_every_page_and_sends_the_token() -> None:
    stub = GitHubStub(page_size=2)  # 5 check runs -> 3 pages; 2 reviews -> 1 page
    with serve(stub):
        res = run_script(stub, token="t0ken")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "merge-ready: yes" in res.stdout
    check_pages = [p for p, _ in stub.requests if "/check-runs" in p]
    assert len(check_pages) == 3
    assert {auth for _, auth in stub.requests} == {"Bearer t0ken"}
