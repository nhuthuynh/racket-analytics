"""Binds tests/features/reconcile_on_pr.feature (CI-RECON-ON-PR; PRC-4.1, PRC-4.2).

Real git and the real `pr-policy` steps of ci.yml (pr_checkout.py), on the merge ref of a PR
whose main carries a Sprint 5 ledger.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pr_checkout import PullRequest, git
from pytest_bdd import given, parsers, scenarios, then, when
from reconcile_on_pr import (
    DECISIONS_FILE,
    LEDGER_FILE,
    RECONCILE_STEP,
    decisions_text,
    ledger_text,
)

pytestmark = pytest.mark.integration
scenarios("reconcile_on_pr.feature")
Results = dict[str, subprocess.CompletedProcess[str]]


@given("a pull request opened against main with a Sprint 5 ledger", target_fixture="pr")
def pull_request(tmp_path: Path) -> PullRequest:
    pr = PullRequest.opened_against_main(tmp_path)
    pr.push("main", LEDGER_FILE, ledger_text([("PE-OLD05-01", "major", "**Fixed**")]))
    git(pr.dev, "merge", "-q", "--ff-only", "main")  # the PR branch starts from that main
    return pr


@given(parsers.parse('the pull request adds a decisions file naming "{declared}"'))
def adds_finding(pr: PullRequest, declared: str) -> None:
    pr.open_event(DECISIONS_FILE, decisions_text(f"**{declared}:** the drill library is thin"))


@given(parsers.parse('the pull request adds a decisions file line "{line}"'))
def adds_line(pr: PullRequest, line: str) -> None:
    pr.open_event(DECISIONS_FILE, decisions_text(line))


@given(parsers.parse("the pull request writes a ledger row for {finding}"))
def writes_row(pr: PullRequest, finding: str) -> None:
    rows = [("PE-OLD05-01", "major", "**Fixed**"), (finding, "major", "**Open.** author-found")]
    pr.open_event(LEDGER_FILE, ledger_text(rows))


@given("the pull request changes only documentation")
def docs_only(pr: PullRequest) -> None:
    pr.open_event("docs/notes.md", "# notes: a known gap in prose outside decisions files\n")


@when("the PR policy checks run on the merge ref", target_fixture="results")
def run_policy(pr: PullRequest) -> Results:
    pr.checkout_merge_ref()
    return pr.run_policy()


@then("the reconcile step fails")
def step_fails(results: Results) -> None:
    res = results[RECONCILE_STEP]
    assert res.returncode == 1, res.stdout + res.stderr


@then("the reconcile step passes")
def step_passes(results: Results) -> None:
    res = results[RECONCILE_STEP]
    assert res.returncode == 0, res.stdout + res.stderr


@then(parsers.parse("it names {finding} as a major with no ledger row"))
def names_major(results: Results, finding: str) -> None:
    out = results[RECONCILE_STEP].stdout
    assert f"{DECISIONS_FILE}:" in out
    assert f"{finding} (major) has no ledger row" in out


@then(parsers.parse('it names the "{phrase}" line as having no finding id'))
def names_gap(results: Results, phrase: str) -> None:
    out = results[RECONCILE_STEP].stdout
    assert f'"{phrase}" line names no finding id' in out
