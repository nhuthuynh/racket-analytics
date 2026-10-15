"""Binds tests/features/merged_verdict.feature (FIX-03-2b, G03-12-PE-PR24-01): the post-merge
verdict check run as the verifier runs it, over HTTP against the local GitHub API stub."""

from __future__ import annotations

import subprocess

import pytest
from github_stub import HEAD_SHA, OLD_SHA, GitHubStub, review, serve
from pytest_bdd import given, parsers, scenarios, then, when
from test_merged_verdict import LATER, PE, merged_pr, pending, run_script

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("merged_verdict.feature")


@pytest.fixture
def stub() -> GitHubStub:
    return GitHubStub(reviews=[])


@given("a pull request merged at its head")
def merged(stub: GitHubStub) -> None:
    stub.pr = merged_pr()


@given("a pull request that is still open")
def still_open(stub: GitHubStub) -> None:
    stub.pr = merged_pr(merged=False)


@given("the principal-engineer's latest verdict is CHANGES REQUESTED on an earlier commit")
def changes_earlier(stub: GitHubStub) -> None:
    stub.reviews.append(review(PE, "CHANGES REQUESTED", OLD_SHA, 1))


@given("a pending review by the repository owner on another commit")
def owner_pending(stub: GitHubStub) -> None:
    stub.reviews.append(pending())


@given("the principal-engineer approved its head")
def approved_head(stub: GitHubStub) -> None:
    stub.reviews.append(review(PE, "APPROVE", HEAD_SHA, 2))


@given("the principal-engineer later approved the merged head")
def approved_after_merge(stub: GitHubStub) -> None:
    stub.reviews.append(review(PE, "APPROVE", HEAD_SHA, 3, LATER))


@when(
    "the principal-engineer verdict on the merged head is checked",
    target_fixture="result",
)
def check(stub: GitHubStub) -> subprocess.CompletedProcess[str]:
    with serve(stub):
        return run_script(stub)


@then(parsers.parse('it is not met, naming "{text}"'))
def not_met(result: subprocess.CompletedProcess[str], text: str) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert "merged-verdict: not met" in result.stdout
    assert text in result.stdout


@then("it is met")
def met(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert "merged-verdict: met" in result.stdout
