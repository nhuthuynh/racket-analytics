"""ST-003: PreToolUse blocks writes to secret paths and audits every Bash command [DPA/AI-10].

Exit code 2 denies the tool call; Claude sees stderr. Exit 0 allows it.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from conftest import run_hook

pytestmark = pytest.mark.unit

HOOK = "pre_tool_use.py"


def write_call(path: str, tool: str = "Write") -> dict[str, object]:
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    return {"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {key: path}}


def bash_call(command: str) -> dict[str, object]:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


# ---------------------------------------------------------------- negative cases first
@pytest.mark.parametrize(
    "rel",
    [
        ".env",
        ".env.local",
        ".env.production",
        "backend/.env",
        "web/.env.development.local",
        "certs/server.pem",
        "deep/dir/private.key",
        "infra/secrets/db-password.txt",
        "infra/secrets/nested/token",
        "web/../.env",
    ],
)
@pytest.mark.parametrize("tool", ["Write", "Edit", "MultiEdit", "NotebookEdit"])
def test_write_to_secret_path_is_denied(project: Path, rel: str, tool: str) -> None:
    result = run_hook(HOOK, write_call(rel, tool), project)
    assert result.returncode == 2, result.stderr
    assert "blocked" in result.stderr.lower()


def test_absolute_secret_path_inside_project_is_denied(project: Path) -> None:
    result = run_hook(HOOK, write_call(str(project / ".env")), project)
    assert result.returncode == 2


def test_symlink_into_secrets_dir_is_denied(project: Path) -> None:
    (project / "infra" / "secrets").mkdir(parents=True)
    (project / "innocent.txt").symlink_to(project / "infra" / "secrets" / "x")
    result = run_hook(HOOK, write_call("innocent.txt"), project)
    assert result.returncode == 2


@pytest.mark.parametrize(
    "command",
    [
        "echo DATABASE_URL=x > .env",
        "printf 'a' >> backend/.env.local",
        "cat key | tee infra/secrets/token",
        "cp /tmp/server.pem certs/server.pem",
        "mv /tmp/k deep/private.key",
    ],
)
def test_bash_write_to_secret_path_is_denied(project: Path, command: str) -> None:
    result = run_hook(HOOK, bash_call(command), project)
    assert result.returncode == 2, result.stderr


# ---------------------------------------------------------------- allowed cases
@pytest.mark.parametrize(
    "rel",
    [
        "backend/src/racket/platform/config.py",
        "infra/env.example",
        "docs/keyboard.md",
        "backend/src/racket/platform/environment.py",
        "infra/compose.yaml",
        "web/app/keys.ts",
    ],
)
def test_ordinary_write_is_allowed(project: Path, rel: str) -> None:
    result = run_hook(HOOK, write_call(rel), project)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "command",
    ["ls -la", "grep DATABASE_URL infra/env.example", "uv run pytest -m unit", "echo hi > out.txt"],
)
def test_ordinary_bash_is_allowed(project: Path, command: str) -> None:
    result = run_hook(HOOK, bash_call(command), project)
    assert result.returncode == 0, result.stderr


def test_bash_command_is_appended_to_audit_log(project: Path) -> None:
    run_hook(HOOK, bash_call("ls -la"), project)
    run_hook(HOOK, bash_call("echo two"), project)
    log = project / ".claude" / "logs" / "bash-audit.jsonl"
    lines = [json.loads(line) for line in log.read_text().splitlines()]
    assert [entry["command"] for entry in lines] == ["ls -la", "echo two"]
    assert all(entry["ts"].endswith("Z") for entry in lines)


def test_denied_bash_command_is_still_audited(project: Path) -> None:
    run_hook(HOOK, bash_call("echo x > .env"), project)
    log = project / ".claude" / "logs" / "bash-audit.jsonl"
    entry = json.loads(log.read_text().splitlines()[-1])
    assert entry["command"] == "echo x > .env"
    assert entry["decision"] == "deny"


# ---------------------------------------------------------------- defensive behaviour
def test_malformed_input_does_not_block_the_session(project: Path) -> None:
    result = run_hook(HOOK, "this is not json", project)
    assert result.returncode == 0
    assert "pre_tool_use" in result.stderr


def test_unknown_tool_is_allowed(project: Path) -> None:
    result = run_hook(HOOK, {"tool_name": "Read", "tool_input": {"file_path": ".env"}}, project)
    assert result.returncode == 0


def test_hook_is_fast(project: Path) -> None:
    start = time.monotonic()
    run_hook(HOOK, write_call("backend/src/a.py"), project)
    assert time.monotonic() - start < 1.5
