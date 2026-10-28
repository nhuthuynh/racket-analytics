"""Binds tests/features/pr_size_production_only.feature (CI-SIZE-PROD-ONLY; ST-003; NFR-077).

Real git, the real `PR size (EP/ENG-04)` step of ci.yml (pr_checkout.py). PO decision
2026-10-28: the 400-line limit counts production code only (ADR 0053).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pr_checkout import SIZE_STEP, PullRequest, lines
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]
scenarios("pr_size_production_only.feature")
Results = dict[str, subprocess.CompletedProcess[str]]


@given("a pull request opened against main", target_fixture="pr")
def pull_request(tmp_path: Path) -> PullRequest:
    return PullRequest.opened_against_main(tmp_path)


@given(parsers.parse('the pull request adds {n:d} lines to "{path}"'))
def pr_adds(pr: PullRequest, n: int, path: str) -> None:
    pr.open_event(path, lines(n))


@when("the PR policy checks run on the merge ref", target_fixture="results")
def run_policy(pr: PullRequest) -> Results:
    pr.checkout_merge_ref()
    return pr.run_policy()


@then(
    parsers.parse(
        "the PR size check {verdict}, counting {n:d} production lines and excluding {m:d} lines"
    )
)
def size_verdict(results: Results, verdict: str, n: int, m: int) -> None:
    out = results[SIZE_STEP]
    assert out.returncode == {"passes": 0, "fails": 1}[verdict], out.stdout
    assert f"pr-size: {n} changed lines of production code" in out.stdout
    assert f"{m} excluded lines (tests, docs, lockfiles, fixtures)" in out.stdout


def test_ci_size_step_reports_zero_production_lines_for_a_tests_only_pr(tmp_path: Path) -> None:
    """IT: the ci.yml step on a merge ref with tests only: nothing counted, all reported."""
    pr = PullRequest.opened_against_main(tmp_path)
    pr.open_event("infra/tests/test_x.py", lines(500))
    pr.open_event("web/e2e/journey.spec.ts", lines(5))
    pr.checkout_merge_ref()
    out = pr.run_policy()[SIZE_STEP]
    assert out.returncode == 0, out.stdout
    assert "pr-size: 0 changed lines of production code" in out.stdout
    assert "505 excluded lines" in out.stdout
    assert "::warning" not in out.stdout
