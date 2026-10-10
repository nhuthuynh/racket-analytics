#!/usr/bin/env python3
"""Tally the manual screen-reader pass (sprint-DoD row S3-DoD-P6; NFR-027 b; PO P12 option b).

    a11y_manual.py docs/sprints/03/a11y-manual.md [--dod docs/sprints/sprint-03.md]

Reads the result tables of the manual's section 3 (columns "VoiceOver iOS" and "TalkBack
Android"). Each cell is exactly "pass", "fail: <words heard>" or "not run", optionally followed
by a count "(k of w)" where w is the number of rows the row covers. A row like "1-24" stands for
every row it covers: a bare "pass"/"fail: ..." there means all of them were run, a count means
only k were ("not run" needs k = 0; "pass"/"fail" need 1 <= k <= w). Partial counts on the two
screen readers need not be the same rows, so only rows proven run on both are counted for the
status. The status is "met (n of n rows run)" only when every row has a result on both screen
readers, otherwise "not met: waiting on P6 (k of n rows run)", where k counts rows run on both.

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
CELL = re.compile(
    r"^(?:(?P<result>pass|fail:\s*\S.*?)|(?P<not_run>not run))"
    r"(?:\s*\((?P<k>\d+) of (?P<w>\d+)\))?$",
    re.I,
)


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
    if not m:
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


def tally(text: str) -> dict:
    """Rows and rows run per screen reader from the manual's section 3 tables."""
    columns: dict[str, int] | None = None
    seen: list[int] = []
    run = dict.fromkeys(DEVICES, 0)
    both = 0
    for line in _section_3(text).splitlines():
        if not line.lstrip().startswith("|"):
            columns = None
            continue
        cells = _cells(line)
        if all(DEVICES[k] in cells for k in DEVICES):
            columns = {k: cells.index(DEVICES[k]) for k in DEVICES}
            continue
        m = ROW_ID.match(cells[0])
        if columns is None or not m:
            continue
        if len(cells) <= max(columns.values()):
            raise ValueError(f"row {cells[0]} has {len(cells)} cells, fewer than its table header")
        first, last = int(m[1]), int(m[2] or m[1])
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
    args = parser.parse_args(argv)
    try:
        result = tally(args.manual.read_text(encoding="utf-8"))
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
