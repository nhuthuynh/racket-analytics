#!/usr/bin/env python3
"""List the ``@red-until-<story>`` Playwright tests of a JSON report, per story (ADR 0046).

The E2E gate runs ``--grep-invert "@red-until-"``; this report lists the red-first tests still
waiting on a story without gating on them (the twin of ``red_until_report.py``). It fails closed:
exit 1 when a tagged test passed in any project (a stale tag), when nothing was selected, when a
selected test has no story, or on report errors; exit 2 when the report is missing or unreadable.
Failed, timed-out, interrupted and skipped tests exit 0. Amendment (2026-10-08): with 0
``@red-until-`` tags in the source files under ``--specs`` (specs and helpers), a report that
selected nothing and only says "No tests found" exits 0. The report is always read.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

# The JSON reporter writes tags without the "@"; accept both. Ids: ST-047, ST-047b, QA-R1S3-01.
STORY = re.compile(r"^@?red-until-([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+[a-z]?)$")
SOURCES = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
NO_TESTS = "No tests found"


def specs(suites: list[dict]) -> Iterator[dict]:
    for suite in suites:
        yield from suite.get("specs", [])
        yield from specs(suite.get("suites", []))


def story_of(tags: list[str]) -> str | None:
    found = [m.group(1) for m in map(STORY.match, tags) if m]
    return found[0] if found else None


def count_tags(root: Path) -> int:
    """``@red-until-`` occurrences in the source files under ``root``: specs and helpers."""
    files = [p for p in sorted(root.rglob("*")) if p.is_file() and p.suffix in SOURCES]
    return sum(p.read_text(encoding="utf-8", errors="replace").count("@red-until-") for p in files)


def outcome(test: dict) -> str:
    last = (test.get("results") or [{"status": "skipped"}])[-1].get("status", "")
    return last if last in ("passed", "skipped") else "failed"  # failed, timedOut, interrupted


def write(text: str, summary: Path | None) -> None:
    print(text)
    if summary:
        with summary.open("a", encoding="utf-8") as fh:
            fh.write(text)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json", type=Path, required=True)
    p.add_argument("--summary", type=Path)
    p.add_argument("--specs", type=Path, help="directory whose @red-until- tags are counted")
    args = p.parse_args(argv)
    if args.specs is not None and not args.specs.is_dir():
        print(f"e2e_red_until_report: no spec directory {args.specs}", file=sys.stderr)
        return 2
    tags = count_tags(args.specs) if args.specs is not None else None
    try:
        data = json.loads(args.json.read_text(encoding="utf-8"))
        suites = data.get("suites", [])
        errors = [str(e.get("message", e)) for e in data.get("errors", [])]
    except (OSError, ValueError, AttributeError) as exc:
        print(f"e2e_red_until_report: cannot read {args.json}: {exc}", file=sys.stderr)
        return 2

    per_story: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    stale, unnamed, seen = [], [], 0
    for spec in specs(suites):
        story = story_of(spec.get("tags", []))
        where = f"{spec.get('file', '?')} > {spec.get('title', '?')}"
        for test in spec.get("tests", []):
            seen += 1
            project = test.get("projectName", "?")
            if story is None:
                unnamed.append(f"[{project}] {where}")
                continue
            result = outcome(test)
            per_story[story][result] += 1
            if result == "passed":
                stale.append(f"{story} [{project}] {where}")

    title = "### E2E tests waiting on a story (`@red-until-<story>`, listed, not gated; ADR 0046)"
    if not seen and tags == 0 and all(NO_TESTS in e for e in errors):
        write(
            f"{title}\n\n0 `@red-until-` tags under `{args.specs}` and none selected: "
            "no red-first E2E spec is waiting on a story.\n",
            args.summary,
        )
        return 0
    lines = [title, "", "| Story | Failed | Passed | Skipped |", "|---|---|---|---|"]
    for story, c in sorted(per_story.items()):
        lines.append(f"| {story} | {c['failed']} | {c['passed']} | {c['skipped']} |")
    problems = []
    if not seen:
        where = f" although the source files carry {tags} tag(s)" if tags else ""
        problems.append(f"no red-until E2E tests were selected{where} (fail closed)")
    problems += [f"stale tag, the test passes: {s}" for s in stale]
    problems += [f"no story in the tags of {u}" for u in unnamed]
    problems += [f"report error: {e}" for e in errors]
    lines += ["", *(f"- {p}" for p in problems)] if problems else ["", "No stale tags."]
    write("\n".join(lines) + "\n", args.summary)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
