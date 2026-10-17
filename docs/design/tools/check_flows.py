#!/usr/bin/env python3
"""Gate checks for a design flows file (PD-4; ADR 0047 rule 2).

Owner: principal-designer. Documentation tooling, not product code. It checks one flows file:

1. every relative Markdown link resolves to a file in the repository (anchors are ignored);
2. every screen named with ``--screen`` has a states row ``| <id> | <state> |`` for each state in
   ``--states``;
3. the design-review section named by ``--review`` (a heading that contains it) has a decider-cell
   row ``| <role> | ...`` with an ISO date (YYYY-MM-DD) for every role in ``--decider``.

Usage:
    python3 docs/design/tools/check_flows.py docs/design/flows-sprint-04.md --review DR-04 \
        --decider senior-frontend-engineer --screen P-01 --states Empty,Loading,Error

Exit codes: 0 all checks pass; 1 at least one problem (one ``FAIL`` line each); 2 file missing.
Standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")


def broken_links(path: Path, text: str) -> list[str]:
    out = []
    for target in LINK.findall(text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue
        if not (path.parent / target.split("#", 1)[0]).exists():
            out.append(f"FAIL link: {target} does not resolve from {path}")
    return out


def missing_states(text: str, screens: list[str], states: list[str]) -> list[str]:
    out = []
    for screen in screens:
        for state in states:
            row = re.compile(rf"^\| {re.escape(screen)} \| {re.escape(state)} \|", re.M)
            if not row.search(text):
                out.append(f"FAIL state: {screen} has no '{state}' row")
    return out


def missing_cells(text: str, review: str, deciders: list[str]) -> list[str]:
    section = re.search(rf"^(#+) .*{re.escape(review)}.*$", text, re.M)
    if not section:
        return [f"FAIL review: no heading names {review}"]
    level = len(section.group(1))
    end = re.compile(rf"^#{{1,{level}}} ", re.M).search(text, section.end())
    body = text[section.end() : end.start() if end else len(text)]
    out = []
    for role in deciders:
        rows = [ln for ln in body.splitlines() if ln.startswith(f"| {role} |")]
        if not any(DATE.search(ln) for ln in rows):
            out.append(f"FAIL cell: {review} has no dated decider cell for {role}")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("file", type=Path)
    p.add_argument("--review", required=True)
    p.add_argument("--decider", action="append", default=[])
    p.add_argument("--screen", action="append", default=[])
    p.add_argument("--states", default="Empty,Loading,Error,Offline,Not-found")
    a = p.parse_args(argv)
    if not a.file.is_file():
        print(f"FAIL file: {a.file} does not exist")
        return 2
    text = a.file.read_text(encoding="utf-8")
    problems = (
        broken_links(a.file, text)
        + missing_states(text, a.screen, a.states.split(","))
        + missing_cells(text, a.review, a.decider)
    )
    for line in problems:
        print(line)
    print(f"check-flows: {len(problems)} problem(s) in {a.file}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
