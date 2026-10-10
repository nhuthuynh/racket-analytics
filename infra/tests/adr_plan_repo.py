"""Test support for PE-R3S3-04: a throwaway git repository with a main and a sprint branch."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from conftest import SCRIPTS_DIR

SCRIPT = SCRIPTS_DIR / "ci" / "adr_commit_plan.py"

_GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, **_GIT_ENV}
    out = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True, env=env
    )
    return out.stdout.strip()


def make_repo(root: Path, sprint_commits: int = 3) -> tuple[Path, list[str]]:
    """A repo with one commit on main and ``sprint_commits`` more on branch ``sprint``.

    Returns the repo and the sprint commits' full SHAs, oldest first.
    """
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "commit", "-q", "--allow-empty", "-m", "base")
    git(repo, "switch", "-q", "-c", "sprint")
    shas = []
    for i in range(sprint_commits):
        git(repo, "commit", "-q", "--allow-empty", "-m", f"sprint commit {i + 1}")
        shas.append(git(repo, "rev-parse", "HEAD"))
    git(repo, "switch", "-q", "main")
    return repo, shas


def adr_naming(path: Path, shas: list[str]) -> Path:
    """An ADR whose plan table has one row per entry of ``shas`` (short form, as the ADR uses)."""
    rows = "\n".join(f"| {i} | `{s[:7]}` | T-{i} |" for i, s in enumerate(shas, 1))
    path.write_text(f"# ADR\n\n| # | Commit | Ticket |\n|---|---|---|\n{rows}\n")
    return path


def run_check(repo: Path, adr: Path, rng: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--adr", str(adr), "--range", rng],
        capture_output=True,
        text=True,
        check=False,
    )
