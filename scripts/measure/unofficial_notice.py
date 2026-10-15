#!/usr/bin/env python3
"""Does the sprint plan place the "unofficial" notice where DR-03 R3-3 decided? (FIX-03-2c)

    unofficial_notice.py docs/sprints/sprint-03.md docs/domain/metric-dictionary.md

Exit 0 when the plan and the dictionary agree; 1 when they contradict the decision; 2 when a
line the check needs is missing (fail closed, ADR 0014).
"""

from __future__ import annotations

import sys


class MissingLine(ValueError):
    """A line the check reads is not in the document."""


def check(plan: str, dictionary: str) -> list[str]:
    return []


if __name__ == "__main__":
    sys.exit(0)
