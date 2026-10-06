#!/usr/bin/env python3
"""List the ``red_until(story=…)`` rows of a pytest JUnit run, per story (W-01; sprint-02 §8).

    python3 scripts/ci/red_until_report.py --junit reports/red-until.xml --root backend \
        [--summary "$GITHUB_STEP_SUMMARY"]

The per-PR gate selects ``not red_until``; this report shows what the rows still waiting on a
story are, without gating on them. It fails closed:

* exit 1 when a red-until row **passed** (a stale marker: the story is done, so the row must
  join the gate; retro 1 A2), when no row was selected, or when a row's file names no story;
* exit 2 when the JUnit file is missing or unreadable.

Failed, errored and skipped rows are expected and exit 0. Standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

STORY = re.compile(r"red_until\(\s*story\s*=\s*[\"']([A-Z]+-\d+[a-z]?)[\"']")


def outcome(case: ET.Element) -> str:
    for tag in ("failure", "error", "skipped"):
        if case.find(tag) is not None:
            return {"failure": "failed", "error": "error", "skipped": "skipped"}[tag]
    return "passed"


def story_of(classname: str, root: Path, cache: dict[str, str | None]) -> str | None:
    rel = classname.split("::")[0].replace(".", "/") + ".py"
    if rel not in cache:
        path = root / rel
        found = STORY.search(path.read_text()) if path.is_file() else None
        cache[rel] = found.group(1) if found else None
    return cache[rel]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--junit", type=Path, required=True)
    p.add_argument("--root", type=Path, required=True, help="pytest rootdir (backend)")
    p.add_argument("--summary", type=Path)
    args = p.parse_args(argv)
    try:
        cases = list(ET.parse(args.junit).getroot().iter("testcase"))  # noqa: S314 (own report)
    except (OSError, ET.ParseError) as exc:
        print(f"red_until_report: cannot read {args.junit}: {exc}", file=sys.stderr)
        return 2

    cache: dict[str, str | None] = {}
    per_story: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    stale, unnamed = [], []
    for case in cases:
        cls, name = case.get("classname", ""), case.get("name", "")
        story = story_of(cls, args.root, cache)
        result = outcome(case)
        if story is None:
            unnamed.append(f"{cls}::{name}")
            continue
        per_story[story][result] += 1
        if result == "passed":
            stale.append(f"{story} {cls}::{name}")

    lines = [
        "### Rows waiting on a story (`red_until`, listed, not gated; sprint-02 §8)",
        "",
        "| Story | Failed | Passed | Skipped/error |",
        "|---|---|---|---|",
    ]
    for story in sorted(per_story):
        c = per_story[story]
        lines.append(f"| {story} | {c['failed']} | {c['passed']} | {c['skipped'] + c['error']} |")
    problems = []
    if not cases:
        problems.append("no red_until rows were selected (fail closed)")
    problems += [f"stale marker, the row passes: {s}" for s in stale]
    problems += [f"no story named in the file of {u}" for u in unnamed]
    lines += ["", *(f"- {p}" for p in problems)] if problems else ["", "No stale markers."]
    text = "\n".join(lines) + "\n"
    print(text)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as fh:
            fh.write(text)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
