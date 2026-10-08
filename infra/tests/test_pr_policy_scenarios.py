"""Binds tests/features/pr_policy.feature (CI-POLICY-BASE; ST-003; NFR-077, NFR-078).

Each scenario rebuilds a pull request with real git the way GitHub presents it to the
`pr-policy` job (pr_checkout.py) and runs that job's steps from `.github/workflows/ci.yml`
verbatim. Bound here, not under backend/tests, because the policy is CI tooling (SRE lane) and
needs PyYAML, which the backend does not depend on. Unit and integration tests:
test_pr_change_set.py and test_pr_policy_merge_base.py next to this file.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pr_checkout import (
    E2E_SPEC,
    IMMUTABILITY_STEP,
    SIZE_STEP,
    UNIT_TEST,
    PullRequest,
    lines,
    pr_policy_steps,
    run_step,
)
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration

scenarios("pr_policy.feature")

Results = dict[str, subprocess.CompletedProcess[str]]


@given("a pull request opened against main", target_fixture="pr")
def pull_request(tmp_path: Path) -> PullRequest:
    return PullRequest.opened_against_main(tmp_path)


def pr_changes(pr: PullRequest, rel: str, text: str) -> None:
    pr.change_in_pr(rel, text)
    pr.open_event()


@given("the pull request changes only documentation")
def pr_docs_only(pr: PullRequest) -> None:
    pr_changes(pr, "docs/notes.md", "# notes\n\nmore\n")


@given(parsers.parse("the pull request changes {n:d} lines"))
def pr_changes_lines(pr: PullRequest, n: int) -> None:
    pr_changes(pr, "backend/src/change.py", lines(n))


@given("the pull request edits an accepted unit test")
def pr_edits_unit_test(pr: PullRequest) -> None:
    pr_changes(pr, UNIT_TEST, "def test_a():\n    pass\n")


@given("another pull request changes an accepted end-to-end test on main after the event")
def main_changes_e2e(pr: PullRequest) -> None:
    pr.main_moves(E2E_SPEC, "test('resume', () => { /* hold */ })\n")


@given(parsers.parse("another pull request adds {n:d} lines on main after the event"))
def main_adds_lines(pr: PullRequest, n: int) -> None:
    pr.main_moves("backend/src/other.py", lines(n))


@when("the PR policy checks run on the merge ref", target_fixture="results")
def run_policy(pr: PullRequest) -> Results:
    pr.checkout_merge_ref()
    return {s["name"]: run_step(s["name"], pr) for s in pr_policy_steps() if "run" in s}


@then("the test immutability check passes")
def immutability_passes(results: Results) -> None:
    res = results[IMMUTABILITY_STEP]
    assert res.returncode == 0, res.stdout + res.stderr


@then("it does not name the end-to-end test changed on main")
def e2e_not_named(results: Results) -> None:
    assert E2E_SPEC not in results[IMMUTABILITY_STEP].stdout


@then("the test immutability check fails naming only the edited unit test")
def immutability_fails(results: Results) -> None:
    res = results[IMMUTABILITY_STEP]
    assert res.returncode == 1, res.stdout + res.stderr
    assert f"modified: {UNIT_TEST}" in res.stdout
    assert E2E_SPEC not in res.stdout


@then(parsers.parse("the PR size check passes and counts {n:d} changed lines"))
def size_passes(results: Results, n: int) -> None:
    res = results[SIZE_STEP]
    assert res.returncode == 0, res.stdout + res.stderr
    assert f"pr-size: {n} changed lines" in res.stdout


@then(parsers.parse("the PR size check fails and counts {n:d} changed lines"))
def size_fails(results: Results, n: int) -> None:
    res = results[SIZE_STEP]
    assert res.returncode == 1, res.stdout + res.stderr
    assert f"pr-size: {n} changed lines" in res.stdout
