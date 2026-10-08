#!/usr/bin/env python3
"""List the ``@red-until-<story>`` Playwright tests of a JSON report, per story (ADR 0046).

    PLAYWRIGHT_JSON_OUTPUT_NAME=../reports/e2e-red-until.json \
        pnpm exec playwright test --grep "@red-until-" --reporter=json || true
    python3 scripts/ci/e2e_red_until_report.py --json reports/e2e-red-until.json \
        [--summary "$GITHUB_STEP_SUMMARY"]

The E2E gate runs ``--grep-invert "@red-until-"``; this report shows the red-first specs still
waiting on a story, without gating on them (the Playwright twin of ``red_until_report.py``).
It fails closed:

* exit 1 when a tagged test **passed** in any project (a stale tag: the story is done, so the
  test must join the gate), when no test was selected, or when a selected test has no story tag;
* exit 2 when the JSON report is missing or unreadable.

Failed, timed-out, interrupted and skipped tests are expected and exit 0. Standard library only.

With ``--specs DIR`` (ADR 0046 amendment, 2026-10-08) the ``@red-until-`` tags in the spec files
under DIR are counted first. With 0 tags no red-first spec is waiting on a story: the report is
not read and the exit is 0. With 1 or more tags the rules above apply, so an empty selection still
fails closed (a broken grep or a renamed tag).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

# The JSON reporter writes tags without the leading "@"; accept both. Story or finding ids:
# ST-047, COACH-1, QA-R1S3-01.
STORY = re.compile(r"^@?red-until-([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+[a-z]?)$")


def specs(suites: list[dict]) -> Iterator[dict]:
    for suite in suites:
        yield from suite.get("specs", [])
        yield from specs(suite.get("suites", []))


def story_of(tags: list[str]) -> str | None:
    for tag in tags:
        found = STORY.match(tag)
        if found:
            return found.group(1)
    return None


SPEC_SUFFIXES = (".spec.ts", ".spec.tsx", ".spec.js", ".spec.mjs")


def count_tags(root: Path) -> int:
    """Number of ``@red-until-`` tags in the Playwright spec files under ``root``."""
    return sum(
        path.read_text(encoding="utf-8", errors="replace").count("@red-until-")
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name.endswith(SPEC_SUFFIXES)
    )


def write(text: str, summary: Path | None) -> None:
    print(text)
    if summary:
        with summary.open("a", encoding="utf-8") as fh:
            fh.write(text)


def outcome(test: dict) -> str:
    results = test.get("results") or []
    last = results[-1].get("status", "") if results else "skipped"
    if last == "passed":
        return "passed"
    if last == "skipped":
        return "skipped"
    return "failed"  # failed, timedOut, interrupted


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json", type=Path, required=True)
    p.add_argument("--summary", type=Path)
    p.add_argument("--specs", type=Path, help="spec directory whose @red-until- tags are counted")
    args = p.parse_args(argv)
    tags = None
    if args.specs is not None:
        if not args.specs.is_dir():
            print(f"e2e_red_until_report: no spec directory {args.specs}", file=sys.stderr)
            return 2
        tags = count_tags(args.specs)
        if tags == 0:
            write(
                "### E2E tests waiting on a story (ADR 0046)\n\n"
                f"0 `@red-until-` tags under `{args.specs}`: "
                "no red-first E2E spec is waiting on a story.\n",
                args.summary,
            )
            return 0
    try:
        data = json.loads(args.json.read_text(encoding="utf-8"))
        suites = data.get("suites", [])
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

    lines = [
        "### E2E tests waiting on a story (`@red-until-<story>`, listed, not gated; ADR 0046)",
        "",
        "| Story | Failed | Passed | Skipped |",
        "|---|---|---|---|",
    ]
    for story in sorted(per_story):
        c = per_story[story]
        lines.append(f"| {story} | {c['failed']} | {c['passed']} | {c['skipped']} |")
    problems = []
    if not seen:
        where = f" although the spec files carry {tags} tag(s)" if tags else ""
        problems.append(f"no red-until E2E tests were selected{where} (fail closed)")
    problems += [f"stale tag, the test passes: {s}" for s in stale]
    problems += [f"no story in the tags of {u}" for u in unnamed]
    problems += [f"report error: {e.get('message', e)}" for e in data.get("errors", [])]
    lines += ["", *(f"- {p}" for p in problems)] if problems else ["", "No stale tags."]
    write("\n".join(lines) + "\n", args.summary)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
