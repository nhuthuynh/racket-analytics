"""Binds tests/features/merge_ready_cancelled.feature (CI-MERGE-READY-CANCELLED): the merge
check run as the orchestrator runs it, over HTTP against a local GitHub API stub."""

from __future__ import annotations

import subprocess

import pytest
from github_stub import GitHubStub, check_run, green_runs, review, serve, workflow_run
from pytest_bdd import given, parsers, scenarios, then, when
from test_merge_ready import red_suite, run_script

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("merge_ready_cancelled.feature")

NEWER_SUITE = 2


@pytest.fixture
def stub() -> GitHubStub:
    return GitHubStub(reviews=[], check_runs=[], workflow_runs=[])


@given("a pull request into main whose CI run failed on the head")
def older_failed(stub: GitHubStub) -> None:
    stub.check_runs = red_suite()
    stub.workflow_runs = [workflow_run(1, 1, conclusion="failure")]


@given("a pull request into main whose CI run was green on the head")
def older_green(stub: GitHubStub) -> None:
    stub.check_runs = green_runs()
    stub.workflow_runs = [workflow_run(1, 1, conclusion="success")]


@given("a pull request into main whose CI run was cancelled on the head")
def older_cancelled(stub: GitHubStub) -> None:
    stub.check_runs = []
    stub.workflow_runs = [workflow_run(1, 1, conclusion="cancelled")]


@given("a newer CI run of the same workflow was cancelled by the concurrency group")
def newer_cancelled(stub: GitHubStub) -> None:
    # cancelled before any job started: its check suite has no check runs (PR #49)
    stub.workflow_runs.append(workflow_run(NEWER_SUITE, 2, conclusion="cancelled"))


@given("a later CI run of the same workflow was cancelled by hand and nothing ran after it")
def later_cancelled_by_hand(stub: GitHubStub) -> None:
    # e.g. the run that removed a label; the older green run saw the old label set (PE-1)
    stub.workflow_runs[0]["created_at"] = "2026-10-09T13:00:00Z"
    stub.workflow_runs.append(
        workflow_run(NEWER_SUITE, 2, conclusion="cancelled", created_at="2026-10-09T13:05:00Z")
    )


@given("a newer CI run of the same workflow is still in progress on the head")
def newer_in_progress(stub: GitHubStub) -> None:
    stub.check_runs += [
        check_run("ci-gate", None, "queued", run_id=200, suite_id=NEWER_SUITE),
    ]
    stub.workflow_runs.append(workflow_run(NEWER_SUITE, 2, status="in_progress"))


@given("the principal-engineer and the senior-qa-engineer approved the head")
def both_approved(stub: GitHubStub) -> None:
    stub.reviews += [
        review("principal-engineer", "APPROVE", review_id=1),
        review("senior-qa-engineer", "APPROVE", review_id=2),
    ]


@when("the orchestrator runs the merge check on the head", target_fixture="result")
def run_check(stub: GitHubStub) -> subprocess.CompletedProcess[str]:
    with serve(stub):
        return run_script(stub)


@then(parsers.parse('the merge is refused naming "{word}"'))
def refused(result: subprocess.CompletedProcess[str], word: str) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert "merge-ready: no" in result.stdout
    assert word in result.stdout


@then("the merge is allowed")
def allowed(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert "merge-ready: yes" in result.stdout
