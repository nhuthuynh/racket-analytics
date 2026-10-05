#!/usr/bin/env python3
"""Open blocker and major findings in review-rounds tables (goal scorecard G01-11).

    open_defects.py --json reports/goal/open-defects.json docs/sprints/01/review-rounds.md

Prints ``{"open": n, "rows": [...]}``. Exit 0 only when no blocker or major finding is open.
A file without a review table exits 2 (fail closed, ADR 0014).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measurelib import open_defects


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", type=Path, help="review-rounds Markdown files")
    parser.add_argument("--json", type=Path, help="also write the result here")
    args = parser.parse_args(argv)
    try:
        text = "\n\n".join(p.read_text(encoding="utf-8") for p in args.files)
        rows = open_defects(text)
    except ValueError as exc:
        print(f"open_defects: {exc}", file=sys.stderr)
        return 2
    result = {"open": len(rows), "rows": rows}
    out = json.dumps(result, indent=2)
    print(out)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(out + "\n", encoding="utf-8")
    return 0 if not rows else 1


if __name__ == "__main__":
    sys.exit(main())
