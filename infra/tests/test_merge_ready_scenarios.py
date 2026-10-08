"""Binds tests/features/merge_ready.feature (CI-PR-GATE): the merge check run as the
orchestrator runs it, over HTTP against a local GitHub API stub."""

from __future__ import annotations

import subprocess

import pytest
from github_stub import OLD_SHA, GitHubStub, check_run, green_runs, review, serve
from pytest_bdd import given, parsers, scenarios, then, when
from test_merge_ready import run_script

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("merge_ready.feature")


@pytest.fixture
def stub() -> GitHubStub:
    return GitHubStub(reviews=[])


@given(parsers.parse('a pull request into main whose CI job "{name}" failed on the head'))
def failed_job(stub: GitHubStub, name: str) -> None:
    stub.check_runs = [*green_runs(), check_run(name, "failure", run_id=40)]


@given("a pull request into main whose CI is green on the head")
def green(stub: GitHubStub) -> None:
    stub.check_runs = green_runs()


@given("a pull request into main whose ci-gate is still running on the head")
def gate_running(stub: GitHubStub) -> None:
    stub.check_runs = [r for r in green_runs() if r["name"] != "ci-gate"] + [
        check_run("ci-gate", None, "in_progress", run_id=41)
    ]


@given("the principal-engineer and the senior-qa-engineer approved the head")
def both_approved(stub: GitHubStub) -> None:
    stub.reviews += [
        review("principal-engineer", "APPROVE", review_id=1),
        review("senior-qa-engineer", "APPROVE", review_id=2),
    ]


@given("the principal-engineer approved the head")
def principal_approved(stub: GitHubStub) -> None:
    stub.reviews.append(review("principal-engineer", "APPROVE", review_id=1))


@given("the senior-qa-engineer approved only an older commit")
def senior_stale(stub: GitHubStub) -> None:
    stub.reviews.append(review("senior-qa-engineer", "APPROVE", OLD_SHA, review_id=2))


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
