#!/usr/bin/env python3
"""PR size gate (EP/ENG-04, NFR-077): aim for ~100 changed lines; > 400 needs the EM's
`size-waiver` label. Lockfiles, fixtures and gold data do not count.
Usage: PR_LABELS='[...]' check_pr_size.py --base origin/main [--head HEAD]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from fnmatch import fnmatch

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
    res = subprocess.run(
        ["git", "diff", "--numstat", f"{args.base}...{args.head}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        print(f"pr-size: git diff failed:\n{res.stderr}")
        return 2
    total = 0
    for line in res.stdout.splitlines():
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
