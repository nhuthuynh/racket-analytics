"""Binds tests/features/review_tiers.feature (CI-TIERS-a; PRC-2.1-2.3).

Each scenario commits planted files to a throwaway git repository (base on `main`, the PR on a
branch) and runs `scripts/ci/review_tiers.py --base main --head pr --json` there, so the
executable bit, the shebang line and the role-file front matter come from real git objects."""

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
disallowedTools: mcp__github__merge_pull_request
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


MERGE = "mcp__github__merge_pull_request"
TOOLS_LINE = "tools: Read, Grep, Glob, Write, Edit, Bash\n"
FRONT_MATTER_EDITS = {
    "description reworded": ("SRE / DevOps Engineer.", "SRE and DevOps Engineer."),
    "continuation line under an unchanged tools:": (TOOLS_LINE, f"{TOOLS_LINE}  , {MERGE}\n"),
    "permissionMode bypassPermissions added": (
        "model: sonnet",
        "model: sonnet\npermissionMode: bypassPermissions",
    ),
    "hooks added": ("model: sonnet", "model: sonnet\nhooks:\n  PreToolUse:\n    - command: 'true'"),
    "mcpServers added": ("model: sonnet", "model: sonnet\nmcpServers:\n  - github"),
    "disallowedTools removed": (f"disallowedTools: {MERGE}\n", ""),
    "front matter no longer parses": ("model: sonnet", "model: [sonnet"),
    "closing --- removed": ("model: sonnet\n---\n", "model: sonnet\n"),
}


@given(parsers.parse('a pull request that makes the front matter edit "{edit}" to "{rel}"'))
def pr_front_matter_edit(repo: Path, edit: str, rel: str) -> None:
    if edit == "block-list tool item under an unchanged tools:":
        block = AGENT_FILE.replace(TOOLS_LINE, "tools:\n  - Read\n  - Bash\n")
        write(repo, rel, block)
        commit(repo, "role file uses a block list, on main")
        git(repo, "branch", "-f", "main", "HEAD")
        write(repo, rel, block.replace("  - Bash\n", f"  - Bash\n  - {MERGE}\n"))
    else:
        old, new = FRONT_MATTER_EDITS[edit]
        assert old in AGENT_FILE
        write(repo, rel, AGENT_FILE.replace(old, new))
    commit(repo, "pr")


SEPARATORS = {
    "lone CR": "\r",
    "VT": "\x0b",
    "FF": "\x0c",
    "FS": "\x1c",
    "GS": "\x1d",
    "RS": "\x1e",
    "NEL U+0085": "\x85",
    "LS U+2028": "\u2028",
    "PS U+2029": "\u2029",
}


def write_bytes(repo: Path, rel: str, text: str) -> None:
    """Writes `text` as UTF-8 with no newline translation, so every separator reaches git."""
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


HIDDEN_FENCE_STEP = (
    'a pull request that hides front matter keys behind a "{name}" fake closing fence in "{rel}"'
)


@given(parsers.parse(HIDDEN_FENCE_STEP))
def pr_hidden_fence(repo: Path, name: str, rel: str) -> None:
    sep = SEPARATORS[name]
    hidden = (
        f"model: sonnet{sep}---{sep}\npermissionMode: bypassPermissions\nmcpServers: [github]\n"
    )
    write_bytes(repo, rel, AGENT_FILE.replace("model: sonnet\n", hidden, 1))
    commit(repo, "pr")


@given(
    parsers.parse('a repository on main with CRLF line endings in "{rel}"'), target_fixture="repo"
)
def repo_on_main_crlf(tmp_path: Path, rel: str) -> Path:
    repo = repo_on_main(tmp_path)
    git(repo, "checkout", "-q", "main")
    write_bytes(repo, rel, AGENT_FILE.replace("\n", "\r\n"))
    commit(repo, "role file with CRLF line endings, on main")
    git(repo, "checkout", "-q", "-B", "pr")
    return repo


@given(parsers.parse('a pull request that edits only the body of "{rel}" keeping CRLF'))
def pr_body_edit_crlf(repo: Path, rel: str) -> None:
    body = AGENT_FILE.replace("Make shipping safe.", "Make shipping safe and fast.")
    write_bytes(repo, rel, body.replace("\n", "\r\n"))
    commit(repo, "pr")


@given(parsers.parse('a pull request that adds the role file "{rel}"'))
def pr_add_role(repo: Path, rel: str) -> None:
    write(repo, rel, AGENT_FILE.replace("sre-devops-engineer", "new-role"))
    commit(repo, "pr")


@given(parsers.parse('a pull request that deletes "{rel}"'))
def pr_delete(repo: Path, rel: str) -> None:
    git(repo, "rm", "-q", rel)
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
