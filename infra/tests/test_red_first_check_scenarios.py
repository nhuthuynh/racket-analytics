"""Binds tests/features/red_first_check.feature (C4-RED): real git, the real `pr-policy` steps
of ci.yml run verbatim on the PR merge ref (pr_checkout.py), commits planted with their bodies."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pr_checkout import PullRequest, git
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("red_first_check.feature")
TEST = "backend/tests/unit/test_rule.py"
RED_FIRST_STEP = "Red first (R3-IN-1, C4-RED)"
Q = r'"(?P<%s>[^"]+)"'  # one quoted value; never spans two quotes


def plant(pr: PullRequest, subject: str, files: list[str], body: str = "") -> None:
    for rel in files:
        path = pr.dev / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {subject}\n")
    git(pr.dev, "add", "-A")
    git(pr.dev, "commit", "-q", "-m", subject, *(["-m", body] if body else []))
    git(pr.dev, "push", "-q", "origin", "pr")
    pr.base_sha = git(pr.dev, "rev-parse", "origin/main")
    pr.head_sha = git(pr.dev, "rev-parse", "pr")


@given("a pull request opened against main", target_fixture="pr")
def pull_request(tmp_path: Path) -> PullRequest:
    return PullRequest.opened_against_main(tmp_path)


@given(
    parsers.re(
        rf"the pull request has a (?:test-only )?commit {Q % 'subject'} changing {Q % 'path'}"
        rf"(?P<with_test> and its unit test together)?(?: with the body line {Q % 'body'})?$"
    )
)
def a_commit(pr: PullRequest, subject: str, path: str, with_test: str, body: str) -> None:
    plant(pr, subject, [path, *([TEST] if with_test else [])], body or "")


@when("the PR policy checks run on the merge ref", target_fixture="red_first")
def run_policy(pr: PullRequest) -> subprocess.CompletedProcess[str]:
    pr.checkout_merge_ref()
    return pr.run_policy()[RED_FIRST_STEP]


@then(parsers.parse("the red-first check {verdict}"))
def verdict(red_first: subprocess.CompletedProcess[str], verdict: str) -> None:
    rc, says = {"fails": (1, "red-first: FAIL"), "passes": (0, "red-first: ok")}[verdict]
    assert red_first.returncode == rc, red_first.stdout + red_first.stderr
    assert says in red_first.stdout


@then(parsers.parse('it names the commit "{subject}" and the path "{path}"'))
def names(red_first: subprocess.CompletedProcess[str], subject: str, path: str) -> None:
    assert f" {subject}: changes {path}\n" in red_first.stdout, red_first.stdout
