"""Shared helpers for the sre-devops-engineer lane tests (ST-001..ST-003)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
SCRIPTS_DIR = REPO_ROOT / "scripts"


def run_hook(
    name: str,
    payload: object,
    project_dir: Path,
    extra_env: dict[str, str] | None = None,
    timeout: float = 60,
) -> subprocess.CompletedProcess[str]:
    """Invoke a hook script exactly as Claude Code does: JSON on stdin, project dir in env."""
    # Hermetic: the runner's own RA_* and GITHUB_ACTIONS must not leak into the hook (on a
    # GitHub runner GITHUB_ACTIONS=true makes stop.py a no-op). Tests that need either pass
    # it in `extra_env` (CI run 37277549983, decision-log 2026-10-05).
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("RA_") and k not in {"GITHUB_ACTIONS", "CI"}
    }
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    if extra_env:
        env.update(extra_env)
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(
        [sys.executable, str(HOOKS_DIR / name)],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
        check=False,
    )


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A throwaway project directory with a git repo, standing in for the real checkout."""
    proj = tmp_path / "proj"
    proj.mkdir()
    subprocess.run(["git", "init", "-q", str(proj)], check=True)
    return proj


def pytest_bdd_apply_tag(tag: str, function: object) -> bool:
    """Gherkin tags become `bdd_tag(name=...)` markers, so `--strict-markers` stays on."""
    pytest.mark.bdd_tag(name=tag)(function)
    return True
