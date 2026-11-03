"""Test support for CI-RECON-ON-PR: a throwaway Sprint 5 ledger and ticket decisions file."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from conftest import SCRIPTS_DIR

SCRIPT = SCRIPTS_DIR / "measure" / "reconcile_due.py"
RECONCILE_STEP = "Decisions findings joined to the ledger (PRC-4.1, PRC-4.2)"
LEDGER_FILE = "docs/sprints/05/review-rounds.md"
DECISIONS_FILE = "docs/sprints/05/decisions/ST-PLANT.md"
DECISIONS_HEAD = (
    "# ST-PLANT decisions\n\n| Date | Who | Decision | Evidence | Why |\n|---|---|---|---|---|\n"
)


def ledger_text(rows: list[tuple[str, str, str]]) -> str:
    body = "".join(f"| {f} | {sev} | {disp} | owner |\n" for f, sev, disp in rows)
    head = "| Finding | Severity | Disposition | Owner |\n|---|---|---|---|\n"
    return f"# Review rounds\n\n{head}{body}"


def decisions_text(*decisions: str) -> str:
    rows = "".join(f"| 2026-11-04 | sre | {d} | `cmd` → rc 0 | judgment |\n" for d in decisions)
    return DECISIONS_HEAD + rows


def run_pr_check(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """``reconcile_due.py --pr`` run from ``cwd`` (a repo root), as the pr-policy step runs it."""
    cmd = [sys.executable, str(SCRIPT), "--pr", *args]
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60)
