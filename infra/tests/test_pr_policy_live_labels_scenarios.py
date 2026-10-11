"""Binds tests/features/pr_policy_live_labels.feature (CI-POLICY-LIVE-LABELS; NFR-077, NFR-078).

Real git and the real `pr-policy` steps of ci.yml (pr_checkout.py); the PR's current labels come
from github_stub over a real socket, the frozen event labels from the step's `PR_LABELS`.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from github_stub import GitHubStub, serve
from pr_checkout import IMMUTABILITY_STEP, SIZE_STEP, UNIT_TEST, PullRequest, lines
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("pr_policy_live_labels.feature")
Results = dict[str, subprocess.CompletedProcess[str]]


@pytest.fixture
def github() -> Iterator[GitHubStub]:
    with serve(GitHubStub(page_size=1)) as stub:
        yield stub


@pytest.fixture
def frozen() -> list[str]:
    return []


@given("a pull request opened against main", target_fixture="pr")
def pull_request(tmp_path: Path) -> PullRequest:
    return PullRequest.opened_against_main(tmp_path)


@given(parsers.parse("the pull request changes {n:d} lines"))
def pr_changes_lines(pr: PullRequest, n: int) -> None:
    pr.open_event("backend/src/change.py", lines(n))


@given("the pull request edits an accepted unit test")
def pr_edits_unit_test(pr: PullRequest) -> None:
    pr.open_event(UNIT_TEST, "def test_a():\n    pass\n")


@given(parsers.re(r'the event froze (no labels|the labels "(?P<names>[^"]+)")'))
def event_froze(frozen: list[str], names: str | None) -> None:
    frozen[:] = names.split(",") if names else []


@given(parsers.parse('the pull request now carries the label "{name}"'))
def now_carries(github: GitHubStub, name: str) -> None:
    github.labels = ["triage", name]  # two pages at page_size=1: pagination is followed


@given("the pull request now carries no labels")
def now_carries_none(github: GitHubStub) -> None:
    github.labels = []


@given("the GitHub labels endpoint fails")
def labels_down(github: GitHubStub) -> None:
    github.labels_status = 500


@when("the PR policy checks run again without a new push", target_fixture="results")
def run_again(pr: PullRequest, github: GitHubStub, frozen: list[str]) -> Results:
    pr.checkout_merge_ref()
    return pr.run_policy(payload_labels=frozen, api=github.url)


@then(parsers.parse("the PR size check {verdict} and counts {n:d} changed lines"))
def size_verdict(results: Results, verdict: str, n: int) -> None:
    out = results[SIZE_STEP]
    assert out.returncode == {"passes": 0, "fails": 1}[verdict], out.stdout
    assert f"pr-size: {n} changed lines" in out.stdout


@then(parsers.parse("the test immutability check {verdict}"))
def immutability_verdict(results: Results, verdict: str) -> None:
    out = results[IMMUTABILITY_STEP]
    assert out.returncode == {"passes": 0, "fails": 1}[verdict], out.stdout


@then(parsers.parse("the labels were read from the {source}"))
def labels_source(results: Results, github: GitHubStub, source: str) -> None:
    for out in results.values():
        assert f"labels from the {source}" in out.stdout, out.stdout
    asked = [auth for path, auth in github.requests if "/labels" in path]
    assert asked, github.requests
    assert set(asked) == {"Bearer stub-token"}
