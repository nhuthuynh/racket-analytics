"""CI-POLICY-BASE unit tests: the PR change set is what the PR head adds on top of its merge base
with the base branch, never what reached the base branch afterwards.

Ubiquitous language (docs/process/ci-cd.md, PR policy): *base branch* (e.g. `origin/main`),
*PR head*, *merge base* (newest commit both share), *change set* (merge base .. PR head).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR

pytestmark = pytest.mark.unit

CI = SCRIPTS_DIR / "ci"
sys.path.insert(0, str(CI))

import pr_change_set  # noqa: E402

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **GIT_ENV},
    ).stdout.strip()


def commit(repo: Path, rel: str, text: str) -> str:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", rel)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """main forks into `pr`; afterwards main moves on (another PR merged)."""
    r = tmp_path / "r"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    commit(r, "web/e2e/journey.spec.ts", "test('x', () => {})\n")
    git(r, "checkout", "-q", "-b", "pr")
    commit(r, "docs/notes.md", "# notes\n")
    git(r, "checkout", "-q", "main")
    commit(r, "web/e2e/journey.spec.ts", "test('x', () => { /* fixed on main */ })\n")
    git(r, "checkout", "-q", "pr")
    return r


def run(script: str, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CI / script), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        env={**os.environ, "PR_LABELS": "[]"},
        timeout=60,
        check=False,
    )


# ---------------------------------------------------------------- negative cases first
def test_an_unknown_base_branch_is_an_error_naming_it(repo: Path) -> None:
    with pytest.raises(pr_change_set.ChangeSetError, match="origin/nope"):
        pr_change_set.merge_base("origin/nope", "HEAD", cwd=repo)


def test_histories_with_nothing_in_common_are_an_error(repo: Path) -> None:
    git(repo, "checkout", "-q", "--orphan", "stranger")
    commit(repo, "other.txt", "x\n")
    with pytest.raises(pr_change_set.ChangeSetError, match="merge base"):
        pr_change_set.merge_base("main", "pr", cwd=repo)


def test_changes_that_reached_the_base_branch_later_are_not_in_the_change_set(
    repo: Path,
) -> None:
    out = pr_change_set.diff("main", "pr", "--name-only", cwd=repo)
    assert out.changes.split() == ["docs/notes.md"]


# ---------------------------------------------------------------- positive behaviour
def test_the_merge_base_is_the_fork_point_not_the_moved_base_branch(repo: Path) -> None:
    fork = git(repo, "rev-parse", "pr~1")
    assert pr_change_set.merge_base("main", "pr", cwd=repo) == fork
    assert git(repo, "rev-parse", "main") != fork


def test_the_change_set_names_the_commits_it_compared(repo: Path) -> None:
    out = pr_change_set.diff("main", "HEAD", "--name-only", cwd=repo)
    assert out.merge_base == git(repo, "rev-parse", "pr~1")
    assert out.head == git(repo, "rev-parse", "pr")
    assert out.describe("main", "HEAD") == (
        f"change set {out.merge_base[:12]}..{out.head[:12]} (merge base of main and HEAD)"
    )


@pytest.mark.parametrize("script", ["check_test_immutability.py", "check_pr_size.py"])
def test_each_policy_script_logs_the_change_set_it_judged(repo: Path, script: str) -> None:
    res = run(script, repo, "--base", "main", "--head", "HEAD")
    assert res.returncode == 0, res.stdout + res.stderr
    assert f"change set {git(repo, 'rev-parse', 'pr~1')[:12]}.." in res.stdout


@pytest.mark.parametrize("script", ["check_test_immutability.py", "check_pr_size.py"])
def test_each_policy_script_fails_closed_on_an_unknown_base_branch(
    repo: Path, script: str
) -> None:
    res = run(script, repo, "--base", "origin/nope", "--head", "HEAD")
    assert res.returncode == 2, res.stdout + res.stderr
    assert "origin/nope" in res.stdout
