"""Binds tests/features/pr_policy.feature (CI-POLICY-BASE; ST-003; NFR-077, NFR-078).

Real git, real ci.yml steps (pr_checkout.py). Bound in infra/tests, not backend/tests: the policy
is CI tooling (SRE lane) and needs PyYAML, which the backend does not depend on.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pr_checkout import E2E_SPEC, IMMUTABILITY_STEP, SIZE_STEP, UNIT_TEST, PullRequest, lines
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("pr_policy.feature")
Results = dict[str, subprocess.CompletedProcess[str]]


@given("a pull request opened against main", target_fixture="pr")
def pull_request(tmp_path: Path) -> PullRequest:
    return PullRequest.opened_against_main(tmp_path)


@given("the pull request changes only documentation")
def pr_docs_only(pr: PullRequest) -> None:
    pr.open_event("docs/notes.md", "# notes\n")


@given(parsers.parse("the pull request changes {n:d} lines"))
def pr_changes_lines(pr: PullRequest, n: int) -> None:
    pr.open_event("backend/src/change.py", lines(n))


@given("the pull request edits an accepted unit test")
def pr_edits_unit_test(pr: PullRequest) -> None:
    pr.open_event(UNIT_TEST, "def test_a():\n    pass\n")


@given("another pull request changes an accepted end-to-end test on main after the event")
def main_changes_e2e(pr: PullRequest) -> None:
    pr.push("main", E2E_SPEC, "test('resume', () => { /* hold */ })\n")


@given(parsers.parse("another pull request adds {n:d} lines on main after the event"))
def main_adds_lines(pr: PullRequest, n: int) -> None:
    pr.push("main", "backend/src/other.py", lines(n))


@when("the PR policy checks run on the merge ref", target_fixture="results")
def run_policy(pr: PullRequest) -> Results:
    pr.checkout_merge_ref()
    return pr.run_policy()


@then("the test immutability check passes")
def immutability_passes(results: Results) -> None:
    assert results[IMMUTABILITY_STEP].returncode == 0, results[IMMUTABILITY_STEP].stdout


@then("it does not name the end-to-end test changed on main")
def e2e_not_named(results: Results) -> None:
    assert E2E_SPEC not in results[IMMUTABILITY_STEP].stdout


@then("the test immutability check fails naming only the edited unit test")
def immutability_fails(results: Results) -> None:
    out = results[IMMUTABILITY_STEP]
    assert out.returncode == 1, out.stdout
    assert f"modified: {UNIT_TEST}" in out.stdout
    assert E2E_SPEC not in out.stdout


@then(parsers.parse("the PR size check {verdict} and counts {n:d} changed lines"))
def size_verdict(results: Results, verdict: str, n: int) -> None:
    out = results[SIZE_STEP]
    assert out.returncode == {"passes": 0, "fails": 1}[verdict], out.stdout
    assert f"pr-size: {n} changed lines" in out.stdout
