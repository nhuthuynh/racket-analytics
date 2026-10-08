#!/usr/bin/env python3
"""PR size gate (EP/ENG-04, NFR-077): aim for ~100 changed lines; > 400 needs the EM's
`size-waiver` label. Lockfiles, fixtures and gold data do not count.
Usage: PR_LABELS='[...]' check_pr_size.py --base origin/main [--head HEAD]
`--base` is the base branch; lines are counted from its merge base with `--head`
(pr_change_set.py, CI-POLICY-BASE).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from fnmatch import fnmatch

from pr_change_set import ChangeSetError, diff

SOFT_LIMIT = 100
HARD_LIMIT = 400
WAIVER_LABEL = "size-waiver"
EXCLUDED = ("*uv.lock", "*pnpm-lock.yaml", "*package-lock.json", "fixtures/*", "*.snap")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", default="HEAD")
    args = ap.parse_args(argv)
    try:
        labels = json.loads(os.environ.get("PR_LABELS", "[]") or "[]")
    except ValueError:
        labels = []
    try:
        change_set = diff(args.base, args.head, "--numstat")
    except ChangeSetError as exc:
        print(f"pr-size: {exc}; failing closed")
        return 2
    print(f"pr-size: {change_set.describe(args.base, args.head)}")
    total = 0
    for line in change_set.changes.splitlines():
        added, deleted, path = line.split("\t", 2)
        if added == "-" or any(fnmatch(path, pat) for pat in EXCLUDED):
            continue  # binary or excluded
        total += int(added) + int(deleted)
    print(f"pr-size: {total} changed lines (target ~{SOFT_LIMIT}, limit {HARD_LIMIT})")
    if total > HARD_LIMIT and WAIVER_LABEL not in labels:
        print(f"pr-size: over {HARD_LIMIT} lines; split the PR or ask the EM for '{WAIVER_LABEL}'")
        return 1
    if total > SOFT_LIMIT:
        print(f"::warning title=PR size::{total} changed lines; aim for about {SOFT_LIMIT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
