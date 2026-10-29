"""IT-04-15 (C4-RED): scripts/ci/check_red_first.py on a throwaway git repo with planted commits.

Real git, the real script, negative cases first; the scenario binding runs the ci.yml step."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR
from pr_checkout import GIT_ENV, git

pytestmark = pytest.mark.integration
B, T = "backend/src/racket/r.py", "backend/tests/t.py"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    plant(tmp_path, "chore: base", ["README.md", "backend/src/racket/app.py"])
    git(tmp_path, "checkout", "-q", "-b", "pr")
    return tmp_path


def plant(repo: Path, subject: str, paths: list[str], body: str = "") -> str:
    for rel in paths:
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(f"{subject}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", subject, *(["-m", body] if body else []))
    return git(repo, "rev-parse", "--short", "HEAD")


def check(repo: Path, base: str = "main", head: str = "HEAD") -> subprocess.CompletedProcess[str]:
    argv = [sys.executable, str(SCRIPTS_DIR / "ci" / "check_red_first.py"), "--base", base]
    env = {**os.environ, **GIT_ENV}
    return subprocess.run(
        [*argv, "--head", head], cwd=repo, capture_output=True, text=True, env=env
    )


@pytest.mark.parametrize(
    ("commits", "rc", "says"),
    [  # negative first
        ([("feat: rule", [B, T], "")], 1, "feat: rule: changes backend/src/racket/r.py\n"),
        ([("Red: in the subject", [B], ""), ("feat: b", ["web/src/b.ts"], "Red:")], 1,
         "red-first: FAIL, 2 code commit(s) without a red step"),
        ([("test: red", [T, "tests/features/r.feature"], ""), ("feat: rule", [B], ""),
          ("refactor: rule", [B], "")], 0, "red-first: ok, 3 commit(s) checked"),
        ([("feat: rule", [B, T], "Why.\n\nRed: pytest tests/t.py -> 1 failed")], 0, "ok, 1 commit"),
        ([], 0, "red-first: ok, 0 commit(s) checked"),
    ],
)  # fmt: skip
def test_it_04_15_planted_commits(repo: Path, commits: list, rc: int, says: str) -> None:
    shas = [plant(repo, subject, paths, body) for subject, paths, body in commits]
    out = check(repo)
    assert out.returncode == rc, out.stdout + out.stderr
    assert says in out.stdout
    if rc:
        assert f"  {shas[0]} " in out.stdout


def test_it_04_15_unknown_ref_fails_closed(repo: Path) -> None:
    out = check(repo, base="no-such-ref")
    assert out.returncode == 2
    assert "failing closed" in out.stdout


def test_it_04_15_deleting_production_code_alone_is_not_a_code_commit(repo: Path) -> None:
    git(repo, "rm", "-q", "backend/src/racket/app.py")
    git(repo, "commit", "-q", "-m", "chore: drop dead code")
    assert check(repo).returncode == 0


def test_it_04_15_merge_commits_and_mains_commits_are_not_judged(repo: Path) -> None:
    git(repo, "checkout", "-q", "main")
    plant(repo, "feat: on main", ["backend/src/racket/main_only.py"])
    git(repo, "checkout", "-q", "pr")
    plant(repo, "test: red", [T])
    git(repo, "merge", "-q", "--no-ff", "--no-edit", "main")  # main merged into the PR branch
    plant(repo, "feat: rule", [B])
    out = check(repo)
    assert out.returncode == 0, out.stdout
    assert "red-first: ok, 2 commit(s) checked" in out.stdout
