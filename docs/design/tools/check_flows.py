#!/usr/bin/env python3
"""Gate checks for a design flows file (PD-4, PD-4b; ADR 0047 rule 2).

Owner: principal-designer. Documentation tooling, not product code. It checks one flows file:

1. every relative Markdown link resolves to a file in the repository (anchors are ignored);
2. every screen named with ``--screen`` has a states row ``| <id> | <state> |`` for each state in
   ``--states``;
3. the design-review section named by ``--review`` (a heading that contains it) has a decider
   table (header with a ``Cell`` column) whose ``Cell`` column, in the row ``| <role> | ...``,
   opens with a verdict and its ISO date, ``[<role>:] [**]accept|reject[**] (YYYY-MM-DD``, for
   every role in ``--decider``; dates in other columns (Opened, Due) do not count (PE-PD4-01),
   nor does a verdict or date merely mentioned later in the cell (PE-PD4-05);
4. for every role in ``--opened``, that table has the role's row with an ISO date in its
   ``Opened`` column; the cell may still say "pending" (the review is opened, not held);
5. every role named in ``--decider`` or ``--opened`` has exactly one row (SFE-PD4-07), so a
   pending row cannot hide behind a decided one.

``--decider`` rc 0 means the cells are written, not that the review passed: a ``reject`` cell
counts as written and still blocks the tickets the review gates.

Usage:
    python3 docs/design/tools/check_flows.py docs/design/flows-sprint-04.md --review DR-04 \
        --decider principal-designer --opened senior-frontend-engineer \
        --screen P-01 --states Empty,Loading,Error

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
DECIDED = re.compile(r"^(?:[\w-]+:\s*)?\**(?:accept|reject)\**\s*\(20\d\d-\d\d-\d\d\b", re.I)


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


def _review_table(text: str, review: str) -> tuple[list[str], list[list[str]]] | str:
    """Header and body rows of the first table in the ``review`` section that has a Cell column."""
    section = re.search(rf"^(#+) .*{re.escape(review)}.*$", text, re.M)
    if not section:
        return f"FAIL review: no heading names {review}"
    level = len(section.group(1))
    end = re.compile(rf"^#{{1,{level}}} ", re.M).search(text, section.end())
    body = text[section.end() : end.start() if end else len(text)]
    tables: list[list[list[str]]] = []
    previous_is_row = False
    for ln in body.splitlines():
        is_row = ln.startswith("|")
        if is_row:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if not previous_is_row:
                tables.append([])
            if not set("".join(cells)) <= set("-: "):
                tables[-1].append(cells)
        previous_is_row = is_row
    for table in tables:
        if table and "Cell" in table[0]:
            return table[0], table[1:]
    return f"FAIL review: {review} has no decider table with a 'Cell' column"


def _column(header: list[str], rows: list[list[str]], role: str, name: str) -> list[str]:
    i = header.index(name)
    return [r[i] for r in rows if r and r[0] == role and len(r) > i]


def _duplicate(review: str, role: str, values: list[str]) -> str | None:
    if len(values) > 1:
        return f"FAIL row: {review} has {len(values)} rows for {role}; exactly one per role"
    return None


def missing_cells(text: str, review: str, deciders: list[str]) -> list[str]:
    """A decider cell counts only when its one Cell opens with accept/reject and an ISO date."""
    table = _review_table(text, review)
    if isinstance(table, str):
        return [table]
    header, rows = table
    out = []
    for role in deciders:
        cells = _column(header, rows, role, "Cell")
        if dup := _duplicate(review, role, cells):
            out.append(dup)
        elif not (cells and DECIDED.match(cells[0])):
            out.append(f"FAIL cell: {review} has no dated decider cell for {role}")
    return out


def unopened_rows(text: str, review: str, roles: list[str]) -> list[str]:
    """A role's row exists and its Opened column has an ISO date (the cell may still be pending)."""
    table = _review_table(text, review)
    if isinstance(table, str):
        return [table]
    header, rows = table
    if "Opened" not in header:
        return [f"FAIL review: {review} decider table has no 'Opened' column"]
    out = []
    for role in roles:
        opened = _column(header, rows, role, "Opened")
        if dup := _duplicate(review, role, opened):
            out.append(dup)
        elif not (opened and DATE.search(opened[0])):
            out.append(f"FAIL opened: {review} has no row with a dated Opened column for {role}")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("file", type=Path)
    p.add_argument("--review", required=True)
    p.add_argument("--decider", action="append", default=[])
    p.add_argument("--opened", action="append", default=[])
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
        + (missing_cells(text, a.review, a.decider) if a.decider else [])
        + (unopened_rows(text, a.review, a.opened) if a.opened else [])
    )
    for line in problems:
        print(line)
    print(f"check-flows: {len(problems)} problem(s) in {a.file}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
