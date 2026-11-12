#!/usr/bin/env python3
"""RETRO-05 trigger (EM-CLOSE-CHECKS, PRC-6.1; retro 4 F1, L22; ADR 0055 rule 1).

    python3 docs/sprints/05/close-checks/retro_ready.py --repo nhuthuynh/racket-analytics \
        --ledger docs/sprints/05/review-rounds.md

The orchestrator runs this before it briefs RETRO-05. Ready only when a VERIFY-05 PR is merged
into main, no VERIFY-05 PR is open, and the latest ledger row of every VERIFY-05 finding
(`<ROLE>-VERIFY05R<n>-<nn>`) is Fixed. A VERIFY-05 PR is one whose title starts with
`[VERIFY-05` or whose head branch starts with `s05/verify-05`.
Exit 0 ready, 1 not ready (each reason printed), 2 unknown (GitHub or the ledger unreadable).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import closelib


def is_verify_pr(pr: dict[str, Any], ticket: str, branch: str) -> bool:
    return str(pr.get("title", "")).startswith(f"[{ticket}") or closelib.head_ref(pr).startswith(
        branch
    )


def verify_problems(
    pulls: list[dict[str, Any]],
    ledger_text: str,
    ticket: str = "VERIFY-05",
    branch: str = "s05/verify-05",
) -> list[str]:
    """Every reason RETRO must not start yet; empty when it may start."""
    problems: list[str] = []
    verify = [p for p in pulls if is_verify_pr(p, ticket, branch)]
    for p in verify:
        if p.get("state") == "open":
            problems.append(f"{ticket} PR #{p['number']} is open: {p.get('title', '')}")
    if not any(closelib.merged_into_main(p) for p in verify):
        problems.append(f"no merged {ticket} PR (the VERIFY PR is always merged, ADR 0055 rule 3)")
    finding = re.compile(rf"-{re.escape(ticket.replace('-', ''))}R\d+-\d+$")
    for fid, row in closelib.ledger_latest(ledger_text).items():
        if finding.search(fid) and not closelib.is_fixed(row["disposition"]):
            shown = row["disposition"] or "no disposition"
            problems.append(f"{fid} (ledger line {row['line']}) is '{shown}', not Fixed")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True, help="OWNER/NAME")
    ap.add_argument("--ledger", required=True, type=Path, help="docs/sprints/05/review-rounds.md")
    ap.add_argument("--ticket", default="VERIFY-05")
    ap.add_argument("--branch", default="s05/verify-05", help="VERIFY head-branch prefix")
    args = ap.parse_args(argv)
    try:
        text = args.ledger.read_text(encoding="utf-8")
        pulls = closelib.all_pulls(args.repo)
    except (OSError, ValueError, KeyError, TypeError) as exc:  # URLError is an OSError
        print(f"retro-ready: unknown (input could not be read: {exc})")
        return 2
    problems = verify_problems(pulls, text, args.ticket, args.branch)
    for p in problems:
        print(f"FAIL {p}")
    if problems:
        print(f"retro-ready: not ready ({len(problems)} reason(s)); do not brief RETRO-05")
        return 1
    print(f"retro-ready: ready ({args.ticket} merged, no {args.ticket} PR open, findings Fixed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
