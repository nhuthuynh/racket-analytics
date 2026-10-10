#!/usr/bin/env python3
"""Open review-rounds rows that a merged ticket names, with no ledger row for it (FIX-03-1a).

    reconcile_due.py docs/sprints/03/review-rounds.md \
        --plan docs/decisions/0039-*.md --decisions docs/sprints/03/decisions \
        --base origin/main [--json out.json]

A ticket PR that closes a finding writes no review-rounds row, so ``open_defects.py`` keeps
counting the finding as open after the ticket merged (V03R1-01, goal scorecard G03-12). This
check lists every open blocker/major row (as ``open_defects.py`` reads it) that a merged ticket
names: a commit of the ADR 0039 per-ticket plan whose subject scope names one of the row's ids,
or a ticket decisions file ``<id>.md`` / ``<id>-*.md`` that is on the base branch (``--base``,
a git ref): a ticket PR adds its own decisions file before it merges, so a file only on the PR's
head names no merged ticket (PE-FIX031A-01). Without ``--base`` every file counts. The row is
reconciled once its latest row, or that row's section heading, names the ticket, its PR
(``#n``) or its merge commit.

Exit 0 when nothing is due, 1 when a row is due (the engineering-manager writes the row), 2 on
a usage error (no review table, unreadable plan or decisions dir, a base git cannot read; fail
closed, ADR 0014).
Limit: a finding closed by work that names no id (for example a CI run on main) is not seen.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measurelib import _cells, open_defects

_SHA = re.compile(r"`?([0-9a-f]{7,40})`?")
_PR = re.compile(r"#(\d+)\b")
_COMMIT_ROW = re.compile(r"^\|\s*\d+\s*\|\s*`[0-9a-f]{7,40}`\s*\|")


def _merged_prs(plan_text: str) -> dict[str, dict[str, str]]:
    """Ticket -> {pr, merged_as} from the plan's PR table (header names "Merged")."""
    prs: dict[str, dict[str, str]] = {}
    header: list[str] | None = None
    for line in plan_text.splitlines():
        if not line.lstrip().startswith("|"):
            header = None
            continue
        cells = _cells(line)
        if header is None:
            header = [c.lower() for c in cells]
            continue
        merged = next((i for i, h in enumerate(header) if h.startswith("merged")), None)
        if merged is None or "pr" not in header or set("".join(cells)) <= set("-: "):
            continue
        pr, sha = cells[header.index("pr")], _SHA.search(cells[merged])
        if _PR.fullmatch(pr) and sha:
            prs[cells[0]] = {"pr": pr, "merged_as": sha.group(1)}
    return prs


def ticket_index(plan_text: str, decision_stems: list[str]) -> list[dict[str, Any]]:
    """Every merged ticket with the finding ids it names (commit scopes) or is named after."""
    prs = _merged_prs(plan_text)
    tickets: dict[str, dict[str, Any]] = {}

    def add(ticket: str, pr: str | None, names: set[str], prefix: str | None = None) -> None:
        entry = tickets.setdefault(
            ticket,
            {
                "ticket": ticket,
                "pr": pr or prs.get(ticket, {}).get("pr"),
                "merged_as": prs.get(ticket, {}).get("merged_as"),
                "names": set(),
                "prefixes": set(),
            },
        )
        entry["names"] |= names
        if prefix:
            entry["prefixes"].add(prefix)

    for line in plan_text.splitlines():
        if not _COMMIT_ROW.match(line):
            continue
        cells = _cells(line)
        scope = re.search(r"\(([^)]*)\)", cells[2])
        pr = _PR.search(cells[3])
        if not scope or not pr:
            continue  # a commit with no ticket PR is not a merged ticket
        ticket = cells[3].split("(")[0].strip()
        add(ticket, f"#{pr.group(1)}", {s.strip() for s in scope.group(1).split(",")})
    for stem in decision_stems:
        add(stem, None, set(), prefix=stem)
    return [
        {**t, "names": sorted(t["names"]), "prefixes": sorted(t["prefixes"])}
        for t in tickets.values()
    ]


def _names(ticket: dict[str, Any], finding: str) -> bool:
    if finding in ticket["names"]:
        return True
    return any(p == finding or p.startswith(finding + "-") for p in ticket["prefixes"])


def _mentions(text: str, ticket: dict[str, Any]) -> bool:
    words = [re.escape(ticket["ticket"])]
    if ticket["pr"]:
        words.append(re.escape(ticket["pr"]) + r"(?!\d)")
    if ticket["merged_as"]:
        words.append(re.escape(ticket["merged_as"][:7]))
    edge = r"(?<![A-Za-z0-9-]){}(?![A-Za-z0-9-])"
    return any(re.search(edge.format(w), text) for w in words)


def due_rows(ledger_text: str, tickets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Open blocker/major rows named by a ticket that neither the row nor its heading names."""
    lines = ledger_text.splitlines()
    due = []
    for row in open_defects(ledger_text):
        latest = lines[row["line"] - 1]
        context = " | ".join(_cells(latest)[1:])  # never the finding-id cell itself
        heading = next(
            (lines[i] for i in range(row["line"] - 1, -1, -1) if lines[i].startswith("#")), ""
        )
        named = [
            t
            for t in tickets
            if any(_names(t, f) for f in row["ids"])
            and not _mentions(context, t)
            and not _mentions(heading, t)
        ]
        if named:
            due.append({**row, "tickets": named})
    return due


def decision_stems(decisions: Path, base: str | None) -> list[str]:
    """Stems of the ``*.md`` ticket decisions files; with ``base``, only those on that ref."""
    if not decisions.is_dir():
        raise ValueError(f"not a directory: {decisions}")
    names = {p.name for p in decisions.glob("*.md")}
    if base is not None:
        if base.startswith("-"):
            raise ValueError(f"not a git ref: {base}")
        argv = ["git", "-C", str(decisions), "ls-tree", "--name-only", f"{base}^{{commit}}", "."]
        out = subprocess.run(  # noqa: S603 - fixed argv, no shell; base is the caller's own ref
            argv,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if out.returncode != 0:
            raise ValueError(f"cannot list {decisions} at base {base}: {out.stderr.strip()}")
        names &= set(out.stdout.splitlines())
    return sorted(n[: -len(".md")] for n in names)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ledger", type=Path, help="review-rounds Markdown file")
    parser.add_argument("--plan", type=Path, help="ADR with the per-ticket plan (ADR 0039)")
    parser.add_argument("--decisions", type=Path, help="the sprint's ticket decisions dir")
    parser.add_argument("--base", help="git ref; only decisions files on it count (merged)")
    parser.add_argument("--json", type=Path, help="also write the result here")
    args = parser.parse_args(argv)
    try:
        text = args.ledger.read_text(encoding="utf-8")
        plan_text = args.plan.read_text(encoding="utf-8") if args.plan else ""
        stems = decision_stems(args.decisions, args.base) if args.decisions else []
        open_count = len(open_defects(text))
        due = due_rows(text, ticket_index(plan_text, stems))
    except (OSError, ValueError) as exc:
        print(f"reconcile-due: {exc}", file=sys.stderr)
        return 2
    for row in due:
        named = "; ".join(
            f"ticket {t['ticket']}"
            + (f" ({t['pr']})" if t["pr"] else "")
            + (f" merged as {t['merged_as']}" if t["merged_as"] else "")
            for t in row["tickets"]
        )
        ids = " / ".join(row["ids"])
        print(f"due: line {row['line']}: {ids} ({row['severity']}) named by {named}")
    print(f"reconcile-due: {open_count} open blocker/major rows, {len(due)} due")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        result = {"open": open_count, "due": len(due), "rows": due}
        args.json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 1 if due else 0


if __name__ == "__main__":
    sys.exit(main())
