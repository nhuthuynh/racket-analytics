#!/usr/bin/env python3
"""Does the sprint plan place the "unofficial" notice where DR-03 R3-3 decided? (FIX-03-2c)

    unofficial_notice.py docs/sprints/sprint-03.md docs/domain/metric-dictionary.md

DR-03 R3-3 (product-manager option a, coach accept): while the rules are provisional, the score
sheet and every stats page say "unofficial", once before the first card, not on each metric card.
The plan's OQ-01 line ("Rulebook PDFs later") and metric-dictionary rule 0.5 must both say so.

Exit 0 when they agree; 1 when they contradict the decision (each problem printed); 2 when a
line the check needs is missing (fail closed, ADR 0014).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PLAN_MARKER = "**Rulebook PDFs later (OQ-01).**"
DICTIONARY_MARKER = "**Rules dependence:**"
ONCE = "once before the first card"
DICTIONARY_ONCE = re.compile(r"once,? before the first card")
PER_CARD = re.compile(r"every metric card[^.|]*unofficial", re.IGNORECASE)


class MissingLine(ValueError):
    """A line the check reads is not in the document."""


def _line(text: str, marker: str, where: str) -> str:
    for line in text.splitlines():
        if marker in line:
            return line
    raise MissingLine(f"{where} has no line with {marker!r}")


def check(plan: str, dictionary: str) -> list[str]:
    """The ways the plan and the dictionary contradict DR-03 R3-3; empty when they agree."""
    plan_line = _line(plan, PLAN_MARKER, "sprint plan (Rulebook PDFs later)")
    rule = _line(dictionary, DICTIONARY_MARKER, "metric dictionary (rule 0.5, Rules dependence)")
    problems = [
        f'sprint plan line {n} promises the notice on "every metric card" '
        "(DR-03 R3-3: once per stats page)"
        for n, line in enumerate(plan.splitlines(), start=1)
        if PER_CARD.search(line)
    ]
    if "every stats page" not in plan_line:
        problems.append('sprint plan OQ-01 line does not say "every stats page"')
    if ONCE not in plan_line:
        problems.append(f'sprint plan OQ-01 line does not say "{ONCE}"')
    if not DICTIONARY_ONCE.search(rule):
        problems.append('metric-dictionary rule 0.5 does not say "once, before the first card"')
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("plan", type=Path, help="docs/sprints/sprint-03.md")
    parser.add_argument("dictionary", type=Path, help="docs/domain/metric-dictionary.md")
    args = parser.parse_args(argv)
    try:
        problems = check(
            args.plan.read_text(encoding="utf-8"), args.dictionary.read_text(encoding="utf-8")
        )
    except MissingLine as exc:
        print(f"unofficial_notice: {exc}", file=sys.stderr)
        return 2
    for problem in problems:
        print(problem)
    if not problems:
        print("unofficial_notice: plan and dictionary agree with DR-03 R3-3")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
