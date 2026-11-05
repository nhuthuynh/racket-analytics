"""Planted-break helpers for ST-082 (REL-1.1, FR-055.R1): run scripts/ci/check_release_notes.py
as a process and plant one break in a copy of a release-notes text."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "ci" / "check_release_notes.py"
NOTES = REPO_ROOT / "docs" / "releases" / "r1-rc.md"


def run_check(*args: str, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=cwd,
    )


def drop_notice(text: str) -> str:
    """Remove every line that carries the phrase "unofficial scoring" (any case)."""
    kept = [ln for ln in text.splitlines() if "unofficial scoring" not in ln.lower()]
    return "\n".join(kept) + "\n"


def drop_row(text: str, first_cell: str) -> str:
    """Remove the table row(s) whose first cell is `first_cell` (backticks ignored)."""
    out = []
    for ln in text.splitlines():
        cells = [c.strip().strip("`") for c in ln.strip().strip("|").split("|")]
        if ln.lstrip().startswith("|") and cells and cells[0] == first_cell:
            continue
        out.append(ln)
    return "\n".join(out) + "\n"


def set_flag_default(text: str, flag: str, value: str) -> str:
    """Rewrite the Default cell (second cell) of the flag row `flag`."""
    out = []
    for ln in text.splitlines():
        cells = ln.strip().strip("|").split("|")
        if ln.lstrip().startswith("|") and cells[0].strip().strip("`") == flag:
            cells[1] = f" `{value}` "
            ln = "|" + "|".join(cells) + "|"
        out.append(ln)
    return "\n".join(out) + "\n"


def strip_pn(text: str, row_id: str) -> str:
    """Remove every P-n reference (P7, P15, ...) from the row whose first cell is `row_id`."""
    out = []
    for ln in text.splitlines():
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if ln.lstrip().startswith("|") and cells and cells[0] == row_id:
            ln = re.sub(r"\bP\d+\b", "the PO", ln)
        out.append(ln)
    return "\n".join(out) + "\n"
