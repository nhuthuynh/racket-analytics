#!/usr/bin/env python3
"""Pass rate of a selected set of tests in JUnit XML reports (goal scorecard G01-02, G01-03).

    junit_rate.py --include 'it_01_' --require it_01_01 --require it_01_04 \
        --json reports/it-rate.json reports/backend-junit.xml

Selection is a regex over ``file|classname::name``. Exit 0 only when every selected test
passed, nothing selected failed, at least one test was selected and every ``--require``
pattern matched. Skips count as not passed unless ``--allow-skips``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measurelib import junit_rate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("reports", nargs="+", type=Path, help="JUnit XML files")
    parser.add_argument("--include", required=True, help="regex over file|classname::name")
    parser.add_argument("--require", action="append", default=[], help="regex; repeatable")
    parser.add_argument("--allow-skips", action="store_true")
    parser.add_argument("--json", type=Path, help="also write the result here")
    args = parser.parse_args(argv)
    result = junit_rate(args.reports, args.include, args.require, args.allow_skips)
    text = json.dumps(result, indent=2)
    print(text)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
