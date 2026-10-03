"""ST-003: .claude/settings.json wires every hook; each hook command points at a real script."""

from __future__ import annotations

import json
import re

import pytest
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

SETTINGS = REPO_ROOT / ".claude" / "settings.json"


def load() -> dict:
    return json.loads(SETTINGS.read_text())


def commands(event: str) -> list[tuple[str, str, int]]:
    out = []
    for group in load()["hooks"].get(event, []):
        for hook in group["hooks"]:
            out.append((group.get("matcher", ""), hook["command"], hook.get("timeout", 60)))
    return out


def test_pre_tool_use_covers_write_tools_and_bash() -> None:
    matchers = " ".join(m for m, _, _ in commands("PreToolUse"))
    for tool in ("Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"):
        assert re.search(rf"\b{tool}\b", matchers), tool


def test_post_tool_use_covers_edits() -> None:
    matchers = " ".join(m for m, _, _ in commands("PostToolUse"))
    for tool in ("Write", "Edit", "MultiEdit"):
        assert re.search(rf"\b{tool}\b", matchers), tool


def test_stop_hook_present_with_enough_time_for_the_unit_suite() -> None:
    stops = commands("Stop")
    assert stops
    assert all(timeout >= 200 for _, _, timeout in stops)


@pytest.mark.parametrize("event", ["PreToolUse", "PostToolUse", "Stop"])
def test_every_hook_command_points_at_an_existing_script(event: str) -> None:
    for _, cmd, _ in commands(event):
        m = re.search(r"\$CLAUDE_PROJECT_DIR\"?/([^\"\s]+)", cmd)
        assert m, cmd
        assert (REPO_ROOT / m.group(1)).is_file(), cmd


def test_secret_paths_are_also_denied_for_reads() -> None:
    deny = load()["permissions"]["deny"]
    assert any(".env" in rule and rule.startswith("Read(") for rule in deny)
    assert any("infra/secrets" in rule for rule in deny)
