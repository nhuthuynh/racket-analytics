#!/usr/bin/env python3
"""PR size gate (EP/ENG-04, NFR-077): aim for ~100 changed lines; > 400 needs the EM's
`size-waiver` label. Only production code counts (PO 2026-10-28, ADR 0054): tests, docs,
lockfiles, fixtures and snapshots are excluded, and their total is printed beside the count.
Usage: PR_LABELS='[...]' check_pr_size.py --base origin/main [--head HEAD]
Labels: the PR's current labels from the GitHub API when GITHUB_TOKEN, GITHUB_REPOSITORY and
PR_NUMBER are set, else PR_LABELS (the event payload) (CI-POLICY-LIVE-LABELS, pr_labels.py).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from fnmatch import fnmatch

from pr_labels import live_labels

SOFT_LIMIT = 100
HARD_LIMIT = 400
WAIVER_LABEL = "size-waiver"
LOCKFILES = ("*uv.lock", "*pnpm-lock.yaml", "*package-lock.json")
FIXTURES = ("fixtures/*", "*.snap")
TESTS = (
    "backend/tests/*",
    "web/tests/*",
    "infra/tests/*",
    "e2e/*",
    "*/e2e/*",
    "tests/*",
    "*.feature",
    "*.spec.ts",
    "*.test.ts",
    "*.test.tsx",
    "conftest.py",
    "*/conftest.py",
)
DOCS = ("docs/*", "*.md")
EXCLUDED = LOCKFILES + FIXTURES + TESTS + DOCS


@dataclass(frozen=True)
class Size:
    """A PR's changed lines: `counted` production code, `excluded` tests/docs/locks/fixtures."""

    counted: int
    excluded: int


def is_excluded(path: str) -> bool:
    return any(fnmatch(path, pat) for pat in EXCLUDED)


def destination(path: str) -> str:
    """The new path of a numstat rename record (`a => b`, `x/{a => b}/y`), else `path`."""
    if " => " not in path:
        return path
    if "{" not in path:
        return path.split(" => ", 1)[1]
    head, rest = path.split("{", 1)
    inner, tail = rest.split("}", 1)
    return (head + inner.split(" => ", 1)[1] + tail).replace("//", "/")


def measure(numstat: str) -> Size:
    """Split `git diff --numstat` output; binary files (`-`) count on neither side.
    A rename record is classified by its destination (PE-SIZEPROD-R1-01)."""
    counted = excluded = 0
    for line in numstat.splitlines():
        added, deleted, path = line.split("\t", 2)
        if added == "-":
            continue
        n = int(added) + int(deleted)
        if is_excluded(destination(path)):
            excluded += n
        else:
            counted += n
    return Size(counted, excluded)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", default="HEAD")
    args = ap.parse_args(argv)
    labels = live_labels(os.environ, "pr-size")
    if labels is None:
        try:
            labels = json.loads(os.environ.get("PR_LABELS", "[]") or "[]")
        except ValueError:
            labels = []
    res = subprocess.run(
        # --no-renames: a move counts as a deletion plus an addition, so a file moved out
        # of tests/ or docs/ into production code counts in full (PE-SIZEPROD-R1-01).
        ["git", "diff", "--numstat", "--no-renames", f"{args.base}...{args.head}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        print(f"pr-size: git diff failed:\n{res.stderr}")
        return 2
    size = measure(res.stdout)
    total = size.counted
    print(
        f"pr-size: {total} changed lines of production code (target ~{SOFT_LIMIT}, "
        f"limit {HARD_LIMIT}); {size.excluded} excluded lines (tests, docs, lockfiles, fixtures)"
    )
    if total > HARD_LIMIT and WAIVER_LABEL not in labels:
        print(f"pr-size: over {HARD_LIMIT} lines; split the PR or ask the EM for '{WAIVER_LABEL}'")
        return 1
    if total > SOFT_LIMIT:
        print(f"::warning title=PR size::{total} changed lines; aim for about {SOFT_LIMIT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
