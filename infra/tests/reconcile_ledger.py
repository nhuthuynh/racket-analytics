"""Test support for FIX-03-1a: a throwaway review-rounds ledger, ticket plan and decisions dir."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT, SCRIPTS_DIR

SCRIPT = SCRIPTS_DIR / "measure" / "reconcile_due.py"
SPRINT_03 = REPO_ROOT / "docs" / "sprints" / "03"
PLAN_0039 = next((REPO_ROOT / "docs" / "decisions").glob("0039-*.md"))

LEDGER_HEAD = "| Finding | Severity | Disposition | Owner |\n|---|---|---|---|\n"
PR_TABLE_HEAD = (
    "| Ticket | PR | Commits | Branch (base `main`) | Head reviewed | Merged into `main` as "
    "| Latest verdicts |\n|---|---|---|---|---|---|---|\n"
)
COMMIT_TABLE_HEAD = "| # | Commit | Subject scope | Ticket (PR) |\n|---|---|---|---|\n"


def ledger_section(heading: str, rows: list[tuple[str, str, str]]) -> str:
    body = "".join(f"| {f} | {sev} | {disp} | owner |\n" for f, sev, disp in rows)
    return f"## {heading}\n\n{LEDGER_HEAD}{body}\n"


def plan(prs: list[tuple[str, str, str]], commits: list[tuple[str, str, str]]) -> str:
    """``prs``: (ticket, "#n", merge sha); ``commits``: (sha, subject scope, "TICKET (#n)")."""
    pr_rows = "".join(f"| {t} | {n} | 1 | `b` | `h` | `{m}` | APPROVE |\n" for t, n, m in prs)
    commit_rows = "".join(
        f"| {i} | `{sha}` | {subj} | {tick} |\n" for i, (sha, subj, tick) in enumerate(commits, 1)
    )
    return f"# ADR\n\n{PR_TABLE_HEAD}{pr_rows}\n{COMMIT_TABLE_HEAD}{commit_rows}"


def run_check(
    ledger: Path, plan_file: Path | None = None, decisions: Path | None = None
) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), str(ledger)]
    if plan_file is not None:
        cmd += ["--plan", str(plan_file)]
    if decisions is not None:
        cmd += ["--decisions", str(decisions)]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)
