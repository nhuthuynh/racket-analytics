"""CI-POLICY-BASE unit tests: given the base *branch*, each policy script judges only the PR's
change set (merge base .. PR head), never what reached the base branch later, and fails closed
when the base branch is missing. Ubiquitous language: docs/process/ci-cd.md §3.1.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR
from pr_checkout import commit, git, lines

pytestmark = pytest.mark.unit
SCRIPTS = ["check_test_immutability.py", "check_pr_size.py"]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """`pr` forks from main; then main moves on (a test edit and 450 lines from another PR)."""
    git(tmp_path, "init", "-q", "-b", "main")
    commit(tmp_path, "web/e2e/journey.spec.ts", "test('x', () => {})\n")
    git(tmp_path, "checkout", "-q", "-b", "pr")
    commit(tmp_path, "docs/notes.md", "# notes\n")
    git(tmp_path, "checkout", "-q", "main")
    commit(tmp_path, "web/e2e/journey.spec.ts", "test('x', () => { /* fixed on main */ })\n")
    commit(tmp_path, "backend/src/big.py", lines(450))
    git(tmp_path, "checkout", "-q", "pr")
    return tmp_path


def run(script: str, repo: Path, base: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "ci" / script), "--base", base, "--head", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        env={**os.environ, "PR_LABELS": "[]"},
        timeout=60,
        check=False,
    )


@pytest.mark.parametrize("script", SCRIPTS)
def test_an_unknown_base_branch_fails_closed(repo: Path, script: str) -> None:
    assert run(script, repo, "origin/nope").returncode == 2


@pytest.mark.parametrize("script", SCRIPTS)
def test_changes_that_reached_the_base_branch_later_are_not_judged(repo: Path, script: str) -> None:
    res = run(script, repo, "main")
    assert res.returncode == 0, res.stdout
    assert "journey.spec.ts" not in res.stdout


def test_the_size_counts_only_the_pr_change_set(repo: Path) -> None:
    assert "pr-size: 1 changed lines" in run("check_pr_size.py", repo, "main").stdout
