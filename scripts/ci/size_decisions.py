#!/usr/bin/env python3
"""Ticket-PR size decisions (SIZE-WAIVERS-03; ADR 0039 rule 4, ADR 0030 rule 4; NFR-077).

A ticket's **size decision** is a stack of PRs, read from the "## Size decisions" table of a
decisions file (`| Ticket | Measured | PRs, in stack order | Kind |`). Each PR is either
``waived N`` (gets the `size-waiver` label, valid up to N changed lines) or a **stacked part**
``N`` that must pass `PR size` unlabelled, so at most 400 lines.

A ticket's **measured** lines are its non-record code lines (ADR 0039: record paths go back to
the base state on a ticket branch). Its PRs must also carry the ticket's own decisions file
(`docs/sprints/03/decisions/<ID>.md`, PO rule 2026-10-07), which `check_pr_size.py` counts, so
the caps must cover the measured lines plus ``DECISIONS_FILE_BUDGET`` (SQA-1, PR #6).

    size_decisions.py check FILE --scope TICKET=LINES ...   # every ticket decided, parts legal
    size_decisions.py apply FILE --ticket T --pr K --changed N   # label for one re-measured PR

Exit 0 ok (``apply`` prints ``label: size-waiver`` or ``label: none``); 1 a problem or a new
decision row is needed; 2 the file is missing or malformed. Standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HARD_LIMIT = 400  # check_pr_size.py HARD_LIMIT
DECISIONS_FILE_BUDGET = 40  # lines of the ticket's own decisions file, in one of its PRs
WAIVER_LABEL = "size-waiver"
HEADING = "## Size decisions"
_PART = re.compile(r"(waived )?(\d+)")


@dataclass(frozen=True)
class Part:
    """One PR of a ticket: its recorded size cap, and whether it carries a waiver."""

    cap: int
    waived: bool


@dataclass(frozen=True)
class Verdict:
    label: str | None
    new_row_needed: bool
    reason: str


Decisions = dict[str, tuple[Part, ...]]


def parse(text: str) -> Decisions:
    """The size-decisions table: ticket -> its PRs in stack order. ValueError if malformed."""
    if HEADING not in text:
        raise ValueError(f"no '{HEADING}' table")
    section = text.split(HEADING, 1)[1].split("\n#", 1)[0]
    decisions: Decisions = {}
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in ("Ticket", "") or set(cells[0]) <= {"-"}:
            continue
        ticket, parts = cells[0], []
        for raw in cells[2].split(";"):
            m = _PART.fullmatch(raw.strip())
            if not m:
                raise ValueError(f"{ticket}: '{raw.strip()}' is neither N nor 'waived N'")
            parts.append(Part(cap=int(m.group(2)), waived=m.group(1) is not None))
        decisions[ticket] = tuple(parts)
    return decisions


def problems(decisions: Decisions, scope: dict[str, int]) -> list[str]:
    """Every ticket in scope decided, no unwaived part over 400, and the measured lines plus
    the ticket's own decisions file covered."""
    found = []
    for ticket, measured in scope.items():
        parts = decisions.get(ticket)
        if parts is None:
            found.append(f"{ticket}: no size decision ({measured} changed lines measured)")
            continue
        found += [
            f"{ticket}: PR {i} is {p.cap} lines, over {HARD_LIMIT}, without a waiver"
            for i, p in enumerate(parts, 1)
            if not p.waived and p.cap > HARD_LIMIT
        ]
        covered, needed = sum(p.cap for p in parts), measured + DECISIONS_FILE_BUDGET
        if covered < needed:
            found.append(
                f"{ticket}: the PRs cover {covered} of {needed} changed lines"
                f" ({measured} measured + {DECISIONS_FILE_BUDGET} for its decisions file)"
            )
    return found


def apply(decisions: Decisions, ticket: str, pr: int, changed: int) -> Verdict:
    """The label for PR ``pr`` (1-based) of ``ticket`` re-measured at ``changed`` lines."""
    parts = decisions.get(ticket, ())
    if not 1 <= pr <= len(parts):
        return Verdict(None, True, f"{ticket} PR {pr} has no size decision")
    part = parts[pr - 1]
    limit = part.cap if part.waived else HARD_LIMIT
    if changed > limit:
        kind = "its waiver" if part.waived else "the unwaived limit"
        return Verdict(None, True, f"{ticket} PR {pr}: {changed} lines, over {kind} of {limit}")
    if part.waived:
        return Verdict(WAIVER_LABEL, False, f"{ticket} PR {pr}: waived up to {part.cap}")
    return Verdict(None, False, f"{ticket} PR {pr}: stacked part, {changed} <= {HARD_LIMIT}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("command", choices=("check", "apply"))
    ap.add_argument("file", type=Path)
    ap.add_argument("--scope", action="append", default=[], metavar="TICKET=LINES")
    ap.add_argument("--ticket")
    ap.add_argument("--pr", type=int, default=1)
    ap.add_argument("--changed", type=int)
    args = ap.parse_args(argv)
    try:
        decisions = parse(args.file.read_text())
        scope = {t: int(n) for t, n in (s.rsplit("=", 1) for s in args.scope)}
    except (OSError, ValueError) as exc:
        print(f"size-decisions: cannot read {args.file}: {exc}", file=sys.stderr)
        return 2
    if args.command == "check":
        found = problems(decisions, scope)
        print("\n".join(found) or f"size-decisions: {len(scope)} tickets decided")
        return 1 if found else 0
    if args.ticket is None or args.changed is None:
        ap.error("apply needs --ticket and --changed")
    v = apply(decisions, args.ticket, args.pr, args.changed)
    if v.new_row_needed:
        print(f"new decision row needed: {v.reason}")
        return 1
    print(f"label: {v.label or 'none'}\n{v.reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
