"""Binds tests/features/red_first_check.feature (C4-RED; R3-IN-1, retro 3 B5).

Real git and the real `pr-policy` steps of ci.yml run verbatim on the PR merge ref
(pr_checkout.py); the commits are planted with their own subjects and bodies.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pr_checkout import PullRequest, git
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("red_first_check.feature")
UNIT_TEST_OF_RULE = "backend/tests/unit/test_rule.py"
RED_FIRST_STEP = "Red first (R3-IN-1, C4-RED)"
Q = r'"(?P<%s>[^"]+)"'  # one quoted value; never spans two quotes


def plant(pr: PullRequest, subject: str, files: list[str], body: str = "") -> None:
    for rel in files:
        path = pr.dev / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {subject}\n")
    git(pr.dev, "add", "-A")
    message = ["-m", subject] + (["-m", body] if body else [])
    git(pr.dev, "commit", "-q", *message)
    git(pr.dev, "push", "-q", "origin", "pr")
    pr.base_sha = git(pr.dev, "rev-parse", "origin/main")
    pr.head_sha = git(pr.dev, "rev-parse", "pr")


@given("a pull request opened against main", target_fixture="pr")
def pull_request(tmp_path: Path) -> PullRequest:
    return PullRequest.opened_against_main(tmp_path)


@given(
    parsers.re(
        rf"the pull request has a commit {Q % 'subject'} changing {Q % 'path'} and its unit test"
        rf" together with the body line {Q % 'body'}$"
    )
)
def code_and_test_with_body(pr: PullRequest, subject: str, path: str, body: str) -> None:
    plant(pr, subject, [path, UNIT_TEST_OF_RULE], body)


@given(
    parsers.re(
        rf"the pull request has a commit {Q % 'subject'} changing {Q % 'path'} and its unit test"
        r" together$"
    )
)
def code_and_test(pr: PullRequest, subject: str, path: str) -> None:
    plant(pr, subject, [path, UNIT_TEST_OF_RULE])


@given(
    parsers.re(rf"the pull request has a test-only commit {Q % 'subject'} changing {Q % 'path'}$")
)
def a_test_only_commit(pr: PullRequest, subject: str, path: str) -> None:
    plant(pr, subject, [path])


@given(parsers.re(rf"the pull request has a commit {Q % 'subject'} changing {Q % 'path'}$"))
def one_file(pr: PullRequest, subject: str, path: str) -> None:
    plant(pr, subject, [path])


@when("the PR policy checks run on the merge ref", target_fixture="red_first")
def run_policy(pr: PullRequest) -> subprocess.CompletedProcess[str]:
    pr.checkout_merge_ref()
    return pr.run_policy()[RED_FIRST_STEP]


@then("the red-first check fails")
def fails(red_first: subprocess.CompletedProcess[str]) -> None:
    assert red_first.returncode == 1, red_first.stdout + red_first.stderr
    assert "red-first: FAIL" in red_first.stdout


@then("the red-first check passes")
def passes(red_first: subprocess.CompletedProcess[str]) -> None:
    assert red_first.returncode == 0, red_first.stdout + red_first.stderr
    assert "red-first: ok" in red_first.stdout


@then(parsers.parse('it names the commit "{subject}" and the path "{path}"'))
def names(red_first: subprocess.CompletedProcess[str], subject: str, path: str) -> None:
    offending = [line for line in red_first.stdout.splitlines() if subject in line]
    assert offending, red_first.stdout
    assert path in offending[0], red_first.stdout
