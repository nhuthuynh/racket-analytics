"""Binds tests/features/review_tiers.feature (CI-TIERS-a; PRC-2.1-2.3).

Each scenario commits planted files to a throwaway git repository (base on `main`, the PR on a
branch) and runs `scripts/ci/review_tiers.py --base main --head pr --json` there, so the
executable bit, the shebang line and the role-file `tools:` diff come from real git objects."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from conftest import SCRIPTS_DIR
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("review_tiers.feature")

SCRIPT = SCRIPTS_DIR / "ci" / "review_tiers.py"
AGENT_FILE = """\
---
name: sre-devops-engineer
description: SRE / DevOps Engineer.
tools: Read, Grep, Glob, Write, Edit, Bash
model: sonnet
---

<mission>
Make shipping safe.
</mission>
"""


def git(repo: Path, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True, env=env
    ).stdout


def write(repo: Path, rel: str, text: str, executable: bool = False) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755 if executable else 0o644)


def commit(repo: Path, message: str) -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given("a repository on main", target_fixture="repo")
def repo_on_main(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "core.fileMode", "true")
    write(repo, ".claude/agents/sre-devops-engineer.md", AGENT_FILE)
    write(repo, "README.md", "# repo\n")
    commit(repo, "base")
    git(repo, "checkout", "-q", "-b", "pr")
    return repo


@given(parsers.parse('a pull request that changes "{paths}"'))
def pr_changes(repo: Path, paths: str) -> None:
    for item in (p.strip() for p in paths.split(",")):
        rel, _, note = item.partition(" (")
        if note.startswith("shebang"):
            write(repo, rel, "#!/usr/bin/env python3\nprint('check')\n")
        elif note.startswith("executable bit"):
            write(repo, rel, "echo check\n", executable=True)
        else:
            write(repo, rel, f"changed in the PR: {rel}\n")
    commit(repo, "pr")


@given(parsers.parse('a pull request that edits only the body of "{rel}"'))
def pr_body_edit(repo: Path, rel: str) -> None:
    write(repo, rel, AGENT_FILE.replace("Make shipping safe.", "Make shipping safe and fast."))
    commit(repo, "pr")


@given(parsers.parse('a pull request that changes the tools: line of "{rel}"'))
def pr_tools_edit(repo: Path, rel: str) -> None:
    write(
        repo, rel, AGENT_FILE.replace("Edit, Bash", "Edit, Bash, mcp__github__merge_pull_request")
    )
    commit(repo, "pr")


@when("the tier classifier runs on the pull request")
def run_classifier(repo: Path, ctx: dict[str, Any]) -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--base", "main", "--head", "pr", "--json"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    ctx["result"] = json.loads(proc.stdout)


@then(parsers.parse("the computed tier is {expected:d}"))
def computed_tier(ctx: dict[str, Any], expected: int) -> None:
    assert ctx["result"]["tier"] == expected, ctx["result"]


@then(parsers.parse('the flagged specialists include "{role}"'))
def flagged(ctx: dict[str, Any], role: str) -> None:
    assert role in ctx["result"]["specialists"], ctx["result"]
