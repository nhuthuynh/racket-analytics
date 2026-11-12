#!/usr/bin/env python3
"""RETRO-05 close checklist (EM-CLOSE-CHECKS, PRC-6.2, PRC-6.3; G05-12; retro 4 F3, L23, L24).

    python3 docs/sprints/05/close-checks/retro05_check.py --repo nhuthuynh/racket-analytics \
        --status docs/sprints/05/status.json --ledger docs/sprints/05/review-rounds.md \
        --blockers docs/sprints/05/blockers.md

1. PR set (PRC-6.2): the PRs merged into main from a Sprint 5 head branch (`--prefix`, default
   `s05/`) equal the `status.json` `ticket_prs.map` entries with `merged: true`; the set
   difference is printed both ways.
2. Open causes (PRC-6.3): every `blockers.md` row whose Status says Open names its causes after
   `Cause:` (or `Causes:`), and each one is still open: `#n` (issue or PR state `open` on
   GitHub), a ledger finding id (latest row Open, Not fixed, Not re-verified or Partly),
   `P<n>` (a PO item) or `setting <n>` (an admin setting; both human items the agents cannot
   close). An Open row that names no cause fails (fail closed, ADR 0014).
3. One close (G05-12): at most one RETRO-05 PR merged or open (`--retro-branch` prefix).
Exit 0 met, 1 not met (each failure printed), 2 unknown (GitHub or an input unreadable).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import closelib

_CAUSE = re.compile(r"\bCauses?:\s*(.*)", re.I)
_ISSUE = re.compile(r"#(\d+)\b")
_HUMAN = re.compile(r"\b(P\d+|setting \d+)\b")


# ------------------------------------------------------------------ PRC-6.2: the PR set


def sprint_merged(pulls: list[dict[str, Any]], prefixes: list[str]) -> set[int]:
    return {
        int(p["number"])
        for p in pulls
        if closelib.merged_into_main(p) and closelib.head_ref(p).startswith(tuple(prefixes))
    }


def status_prs(status: dict[str, Any]) -> set[int]:
    """PR numbers the status map lists as merged; a map that cannot be read is refused."""
    try:
        rows = status["ticket_prs"]["map"]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"status.json has no ticket_prs.map ({exc})") from exc
    out: set[int] = set()
    for row in rows:
        n = row.get("pr") if isinstance(row, dict) else None
        if not isinstance(n, int) or isinstance(n, bool):
            raise ValueError(f"status.json map row without an integer pr: {row!r}")
        if row.get("merged") is True:
            out.add(n)
    return out


def set_problems(github: set[int], status: set[int]) -> list[str]:
    problems = []
    if extra := sorted(github - status):
        problems.append("on GitHub, not in status.json: " + ", ".join(f"#{n}" for n in extra))
    if missing := sorted(status - github):
        problems.append(
            "in status.json, not merged on GitHub: " + ", ".join(f"#{n}" for n in missing)
        )
    return problems


# ------------------------------------------------------------------ PRC-6.3: open causes


def open_blocker_rows(text: str) -> list[dict[str, Any]]:
    """Rows whose Status cell says Open, from every table with a Status column."""
    found = False
    rows: list[dict[str, Any]] = []
    for header, body in closelib.tables(text):
        st = closelib.column(header, "status")
        if st is None:
            continue
        found = True
        for number, row in body:
            if st < len(row) and re.search(r"\bopen\b", closelib.plain(row[st]), re.I):
                rows.append({"line": number, "text": " | ".join(row[:st])})
    if not found:
        raise ValueError("no blockers table with a Status column")
    return rows


def causes(text: str) -> list[str]:
    m = _CAUSE.search(text)
    if not m:
        return []
    named = m.group(1).split(" | ")[0]  # only the cell that names the causes
    refs = [f"#{n}" for n in _ISSUE.findall(named)]
    refs += _HUMAN.findall(named)
    refs += closelib.FINDING_ID.findall(named)
    return list(dict.fromkeys(refs))


def cause_problems(
    rows: list[dict[str, Any]], issue_state: Callable[[int], str], ledger_text: str
) -> list[str]:
    ledger = closelib.ledger_latest(ledger_text)
    problems: list[str] = []
    for row in rows:
        where = f"blockers line {row['line']}"
        named = causes(row["text"])
        if not named:
            problems.append(f"{where}: Open row names no cause ('Cause: #n | <finding id> | P<n>')")
        for ref in named:
            if ref.startswith("#"):
                state = issue_state(int(ref[1:]))
                if state != "open":
                    problems.append(f"{where}: Open row names {ref}, which is {state} on GitHub")
            elif _HUMAN.fullmatch(ref):
                continue  # a human item: open until the PO or an admin acts (not readable here)
            elif ref not in ledger:
                problems.append(f"{where}: Open row names {ref}, which is not in the ledger")
            elif not closelib.is_open(ledger[ref]["disposition"]):
                problems.append(
                    f"{where}: Open row names {ref}, closed in the ledger "
                    f"(line {ledger[ref]['line']}: '{ledger[ref]['disposition']}')"
                )
    return problems


# ------------------------------------------------------------------ G05-12: one close


def retro_pr_problems(pulls: list[dict[str, Any]], branch: str) -> list[str]:
    retro = sorted(
        int(p["number"])
        for p in pulls
        if closelib.head_ref(p).startswith(branch)
        and (p.get("state") == "open" or closelib.merged_into_main(p))
    )
    if len(retro) > 1:
        return ["more than one RETRO PR (one close): " + ", ".join(f"#{n}" for n in retro)]
    return []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True, help="OWNER/NAME")
    ap.add_argument("--status", required=True, type=Path)
    ap.add_argument("--ledger", required=True, type=Path)
    ap.add_argument("--blockers", required=True, type=Path)
    ap.add_argument("--prefix", action="append", help="Sprint head-branch prefix (default s05/)")
    ap.add_argument("--retro-branch", default="s05/retro-05")
    args = ap.parse_args(argv)
    try:
        st = status_prs(json.loads(args.status.read_text(encoding="utf-8")))
        ledger_text = args.ledger.read_text(encoding="utf-8")
        rows = open_blocker_rows(args.blockers.read_text(encoding="utf-8"))
        pulls = closelib.all_pulls(args.repo)
        problems = set_problems(sprint_merged(pulls, args.prefix or ["s05/"]), st)
        problems += cause_problems(rows, lambda n: closelib.issue_state(args.repo, n), ledger_text)
    except (OSError, ValueError, KeyError, TypeError) as exc:  # URLError is an OSError
        print(f"retro05-check: unknown (input could not be read: {exc})")
        return 2
    problems += retro_pr_problems(pulls, args.retro_branch)
    for p in problems:
        print(f"FAIL {p}")
    if problems:
        print(f"retro05-check: not met ({len(problems)} failure(s))")
        return 1
    print(f"retro05-check: met ({len(st)} merged PRs equal the status map; Open causes open)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
