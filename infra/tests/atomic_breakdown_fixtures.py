"""Planted-row helpers for QA-DOR-CHECK (PRC-7.1): run scripts/ci/check_atomic_breakdown.py as a
process, find the current sprint's breakdown, and plant one break in a copy of a breakdown text."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "ci" / "check_atomic_breakdown.py"


def run_check(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=cwd,
    )


def current_breakdown(root: Path = REPO_ROOT) -> Path:
    plans = sorted((root / "docs" / "sprints").glob("sprint-[0-9][0-9].md"))
    sprint = plans[-1].stem.split("-")[1]
    return root / "docs" / "sprints" / sprint / "requirements-breakdown.md"


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def blank_cell(text: str, row_id: str, column: str) -> str:
    """Empty the `column` cell of the table row whose first cell is `row_id`."""
    lines = text.splitlines()
    header: list[str] = []
    for i, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            header = []
            continue
        cells = _cells(line)
        if not header:
            header = cells
            continue
        if cells[0] == row_id:
            cells[header.index(column)] = ""
            lines[i] = "| " + " | ".join(cells) + " |"
            return "\n".join(lines) + "\n"
    raise AssertionError(f"row {row_id} not found")


def drop_negative_examples(text: str, rule_id: str) -> str:
    """Remove every negative Example line under the Gherkin `Rule: <rule_id>` line."""
    out: list[str] = []
    inside = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Rule:"):
            inside = stripped.split()[1] == rule_id
        if inside and stripped.startswith("Example:") and "negative" in stripped:
            continue
        out.append(line)
    return "\n".join(out) + "\n"


def rename_id(text: str, old: str, new: str) -> str:
    planted, count = re.subn(rf"^\| {re.escape(old)} \|", f"| {new} |", text, flags=re.M)
    assert count == 1, (old, count)
    return planted
