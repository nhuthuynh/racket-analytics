"""Planted-break fixture set for CI-DOC-CHECK (PRC-3.1-3.4): a small git repository in a temp dir
with the files scripts/ci/check_docs.py reads (the ASB register, an agent file, a sprint plan, a
flows file with its checker), one commit as the PR base; each test then plants one break on top."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "ci" / "check_docs.py"
FLOWS_TOOL = REPO_ROOT / "docs" / "design" / "tools" / "check_flows.py"
REGISTER = "docs/research/agentic-sdlc-best-practices.md"

REGISTER_TEXT = """# Register

### 3.1 ANT

| ID | Title | Publisher | URL | Official? | Status | Live check 2026-11-03 |
|---|---|---|---|---|---|---|
| ASB/ANT-01 | Subagents | Anthropic | https://x.invalid/a | yes | Confirmed | 200 |
| ASB/ANT-03 | Hooks | Anthropic | https://x.invalid/b | yes | Not confirmed: partly | 200 |
| ASB/AGL-20 | Flow | Someone | https://x.invalid/c | no | Unverified: blocked | 403 |
"""

AGENT_OK = """---
name: sre-devops-engineer
description: SRE / DevOps Engineer.
tools: Read, Grep, Bash
model: sonnet
---

<role>CI owner [ASB/ANT-01].</role>
"""


def flows_text(cell: str, sprint: str = "05") -> str:
    return (
        f"# Flows sprint {sprint}\n\n## 14. Design review record (DR-{sprint})\n\n"
        "| Role | Items | Opened | Due | Cell |\n|---|---|---|---|---|\n"
        f"| product-manager | R5-1 | 2026-11-03 | 2026-11-05 | {cell} |\n\n## 15. Next\n"
    )


def git(root: Path, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
    }
    env["GIT_COMMITTER_EMAIL"] = "t@t"
    out = subprocess.run(
        ["git", *args], cwd=root, env=env, capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_repo(root: Path) -> str:
    """Create the base repository; return the base commit SHA."""
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q", "-b", "main")
    write(root, REGISTER, REGISTER_TEXT)
    write(root, ".claude/agents/sre-devops-engineer.md", AGENT_OK)
    write(root, ".gitignore", "/.local/\ninfra/.env\n")
    write(root, "backend/tests/unit/test_x.py", "def test_x():\n    pass\n")
    write(root, "scripts/ci/tool.py", "print('x')\n")
    write(
        root,
        "docs/sprints/sprint-05.md",
        "# Sprint 5\n\nOld line: `scripts/ci/gone.py` was removed.\n",
    )
    write(root, "docs/notes.md", "# Notes\n\nSee `scripts/ci/tool.py`.\n")
    (root / "docs/design/tools").mkdir(parents=True, exist_ok=True)
    shutil.copy(FLOWS_TOOL, root / "docs/design/tools/check_flows.py")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    return git(root, "rev-parse", "HEAD")


def commit(root: Path, message: str = "planted") -> str:
    git(root, "add", "-A")
    git(root, "commit", "-q", "--allow-empty", "-m", message)
    return git(root, "rev-parse", "HEAD")


def run_check(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )
