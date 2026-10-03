#!/usr/bin/env python3
"""Flaky-test report (NFR-074): compare JUnit XML files from repeated runs of the same suite.

A test is flaky when it passed in at least one run and failed or errored in another.
Consistently failing tests are broken, not flaky, and are left to the normal gate.
Usage: flaky_report.py [--fail-on-flaky] --out report.md run1.xml run2.xml ...
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def outcomes(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for case in ET.parse(path).getroot().iter("testcase"):  # noqa: S314
        test_id = f"{case.get('classname', '')}::{case.get('name', '')}"
        if case.find("failure") is not None or case.find("error") is not None:
            result[test_id] = "fail"
        elif case.find("skipped") is not None:
            result[test_id] = "skip"
        else:
            result[test_id] = "pass"
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--fail-on-flaky", action="store_true")
    ap.add_argument("runs", nargs="+")
    args = ap.parse_args(argv)

    seen: dict[str, set[str]] = defaultdict(set)
    for run in args.runs:
        for test_id, outcome in outcomes(Path(run)).items():
            seen[test_id].add(outcome)
    flaky = sorted(t for t, o in seen.items() if {"pass", "fail"} <= o)

    lines = [
        "# Flaky-test report (NFR-074)",
        "",
        f"{len(args.runs)} runs, {len(seen)} tests, {len(flaky)} flaky.",
        "",
    ]
    if flaky:
        lines += [
            "Quarantine within 1 day with an owner, issue and fix-by date (testing-strategy §9).",
            "",
        ]
        lines += [f"- `{t}`" for t in flaky]
    Path(args.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 1 if (flaky and args.fail_on_flaky) else 0


if __name__ == "__main__":
    sys.exit(main())
