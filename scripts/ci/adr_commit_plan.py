#!/usr/bin/env python3
"""A ticket plan names every commit of a range exactly once (PE-R3S3-04; ADR 0039, PO P13).

Reads the commits of a git range (``git log --format=%H A..B``, merges included) and counts how
often the ADR names each one. A commit is *named* by a hex word of 7 to 40 characters that is a
prefix of its full SHA and stands alone (no hex letter or digit, and no other word character,
directly before or after it). Every commit must be named exactly once.

    adr_commit_plan.py --adr docs/decisions/0039-....md --range origin/main..origin/sprint-03

Exit 0 every commit named once; 1 a commit is missing or named more than once (each one is
listed); 2 the ADR is unreadable, git cannot read the range, or the range is empty.
Standard library only.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

_HEX_WORD = re.compile(r"(?<![0-9A-Za-z_])[0-9a-f]{7,40}(?![0-9A-Za-z_])")


def plan_problems(shas: list[str], text: str) -> list[str]:
    """One line per commit of ``shas`` (full SHAs, in range order) not named exactly once."""
    if not shas:
        raise ValueError("the range has no commits")
    words = _HEX_WORD.findall(text)
    problems = []
    for sha in shas:
        count = sum(1 for w in words if sha.startswith(w))
        if count == 0:
            problems.append(f"{sha[:7]}: missing (named 0 times)")
        elif count > 1:
            problems.append(f"{sha[:7]}: named {count} times")
    return problems


def range_commits(repo: Path, rng: str) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(repo), "log", "--reverse", "--format=%H", rng, "--"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        raise ValueError(f"git cannot read {rng}: {out.stderr.strip()}")
    return out.stdout.split()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--adr", required=True, type=Path)
    ap.add_argument("--range", required=True, dest="rng")
    ap.add_argument("--repo", default=".", type=Path)
    args = ap.parse_args(argv)
    try:
        text = args.adr.read_text(encoding="utf-8")
        shas = range_commits(args.repo, args.rng)
        problems = plan_problems(shas, text)
    except (OSError, ValueError) as exc:
        print(f"adr-plan: {exc}", file=sys.stderr)
        return 2
    for line in problems:
        print(line)
    if problems:
        print(f"{len(problems)} of {len(shas)} commits in {args.rng} not named exactly once")
        return 1
    print(f"{len(shas)} commits in {args.rng}, each named once in {args.adr}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
