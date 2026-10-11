#!/usr/bin/env python3
"""Tally the manual screen-reader pass (sprint-DoD row S3-DoD-P6; NFR-027 b; PO P12 option b).

    a11y_manual.py docs/sprints/03/a11y-manual.md [--dod docs/sprints/sprint-03.md] [--rows 38]

Reads the result tables of the manual's section 3 (columns "VoiceOver iOS" and "TalkBack
Android"). Each cell is exactly "pass", "fail: <words heard>" or "not run", optionally followed
by a count "(k of w)" where w is the number of rows the row covers (a count is never part of
the words heard: "fail: (3 of 24)" and "fail: (3 of 24) x" are malformed). A row like
"1-24" stands for every row it covers: a bare "pass"/"fail: ..." there means all of them were
run, a count means only k were ("not run" needs k = 0; "pass"/"fail" need 1 <= k <= w).
Partial counts on the two screen readers need not be the same rows, so only rows proven run
on both are counted for the status. The status is "met (n of n rows run)" only when every
row has a result on both screen readers, otherwise "not met: waiting on P6 (k of n rows
run)", where k counts rows run on both.

Every table in section 3 is a result table: a header without both columns, a row id that is
not "n" or "first-last", a reversed range, or (with --rows N) a row count other than N is
malformed.

Exit 0 met, 1 not met, 2 malformed manual or plan (fail closed, ADR 0014), 3 the sprint
plan's S3-DoD-P6 status cell says something other than the tally.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DEVICES = {"voiceover": "VoiceOver iOS", "talkback": "TalkBack Android"}
DOD_ROW = "S3-DoD-P6"
ROW_ID = re.compile(r"^(\d+)(?:\s*[-\u2013]\s*(\d+))?$")
COUNT = r"\(\s*(?P<k>\d+)\s+of\s+(?P<w>\d+)\s*\)"
CELL = re.compile(
    rf"^(?:(?P<result>pass|fail:\s*(?P<words>\S.*?))|(?P<not_run>not run))(?:\s*{COUNT})?$",
    re.I,
)
# A count is never words heard, wherever it stands in them (PE-R2-01, PE-R3-01, PE-70-02).
COUNT_IN_WORDS = re.compile(r"\(\s*\d+\s+of\s+\d+\s*\)", re.I)
SEPARATOR = re.compile(r"^:?-+:?$")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _section_3(text: str) -> str:
    parts = re.split(r"^## 3\.[^\n]*\n", text, maxsplit=1, flags=re.M)
    if len(parts) < 2:
        raise ValueError("no result table: the manual has no section 3")
    return re.split(r"^## ", parts[1], maxsplit=1, flags=re.M)[0]


def _ran(cell: str, rid: str, width: int) -> int:
    """How many of the row's `width` rows the cell records as run (fail closed on anything else)."""
    m = CELL.match(cell.strip())
    if not m or (m["words"] and COUNT_IN_WORDS.search(m["words"])):
        raise ValueError(
            f"row {rid}: {cell!r} is not 'pass', 'fail: <words heard>' or 'not run'"
            " (optionally followed by '(k of w)')"
        )
    if m["k"] is None:
        return width if m["result"] else 0
    k, w = int(m["k"]), int(m["w"])
    low = 1 if m["result"] else 0
    high = width if m["result"] else 0
    if w != width or not low <= k <= high:
        raise ValueError(f"row {rid}: the count in {cell!r} does not fit a row of {width} row(s)")
    return k


def _header(cells: list[str]) -> dict[str, int]:
    """Column index per screen reader; a section 3 table must name both exactly."""
    if not all(DEVICES[k] in cells for k in DEVICES):
        raise ValueError(
            f"table header {' | '.join(cells)!r} lacks the VoiceOver iOS and TalkBack Android"
            " columns"
        )
    return {k: cells.index(DEVICES[k]) for k in DEVICES}


def _row_range(rid: str) -> tuple[int, int]:
    """First and last row a row id covers ("25" or "1-24"); anything else fails closed."""
    m = ROW_ID.match(rid)
    if not m:
        raise ValueError(f"row id {rid!r} cannot be read (expected 'n' or 'first-last')")
    first, last = int(m[1]), int(m[2] or m[1])
    if last < first:
        raise ValueError(f"row {rid} is a reversed range")
    return first, last


def tally(text: str, expected_rows: int | None = None) -> dict:
    """Rows and rows run per screen reader from the manual's section 3 tables.

    Every table in section 3 is a result table; `expected_rows`, when given, must match."""
    columns: dict[str, int] | None = None
    seen: list[int] = []
    run = dict.fromkeys(DEVICES, 0)
    both = 0
    for line in _section_3(text).splitlines():
        if not line.lstrip().startswith("|"):
            columns = None
            continue
        cells = _cells(line)
        if columns is None:
            columns = _header(cells)
            continue
        if all(SEPARATOR.match(c) for c in cells):
            continue
        first, last = _row_range(cells[0])
        if len(cells) <= max(columns.values()):
            raise ValueError(f"row {cells[0]} has {len(cells)} cells, fewer than its table header")
        for n in range(first, last + 1):
            expected = len(seen) + 1
            if n != expected:
                raise ValueError(f"row {n} is out of order or numbered twice (expected {expected})")
            seen.append(n)
        width = last - first + 1
        ran = {k: _ran(cells[i], cells[0], width) for k, i in columns.items()}
        for k, r in ran.items():
            run[k] += r
        # Rows proven run on both: partial counts on the two readers may be different rows.
        both += max(0, sum(ran.values()) - width * (len(ran) - 1))
    if not seen:
        raise ValueError("no result table with VoiceOver iOS and TalkBack Android columns")
    rows = len(seen)
    if expected_rows is not None and rows != expected_rows:
        raise ValueError(f"the manual has {rows} rows, expected {expected_rows}")
    return {"rows": rows, **run, "both": both, "met": both == rows, "status": status(both, rows)}


def status(both: int, rows: int) -> str:
    """The sprint-DoD wording (sprint-03 section 9.1) for `both` of `rows` rows run."""
    if both == rows:
        return f"met ({rows} of {rows} rows run)"
    return f"not met: waiting on P6 ({both} of {rows} rows run)"


def dod_status(plan: str) -> str:
    """The last cell of the plan's S3-DoD-P6 row, without Markdown emphasis."""
    for line in plan.splitlines():
        cells = _cells(line) if line.lstrip().startswith("|") else []
        if cells and cells[0] == DOD_ROW:
            return " ".join(cells[-1].replace("**", "").split())
    raise ValueError(f"the sprint plan has no {DOD_ROW} row")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("manual", type=Path, help="the screen-reader manual (a11y-manual.md)")
    parser.add_argument("--dod", type=Path, help="sprint plan whose S3-DoD-P6 row must agree")
    parser.add_argument("--rows", type=int, help="the number of rows the manual must have")
    args = parser.parse_args(argv)
    try:
        result = tally(args.manual.read_text(encoding="utf-8"), args.rows)
        claimed = dod_status(args.dod.read_text(encoding="utf-8")) if args.dod else None
    except (OSError, ValueError) as exc:
        print(f"a11y_manual: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    if claimed is not None and claimed != result["status"]:
        print(
            f"a11y_manual: {DOD_ROW} says {claimed!r} but the manual says {result['status']!r}",
            file=sys.stderr,
        )
        return 3
    return 0 if result["met"] else 1


if __name__ == "__main__":
    sys.exit(main())
