#!/usr/bin/env python3
"""Red-first check: every code commit in a PR shows its red step (C4-RED; R3-IN-1, retro 3 B5).

A *code commit* adds, changes or renames a path under backend/src or web/src. Its *red step* is
a `Red:` line in its own body or an earlier *test-only commit* in the PR (tests, no production
code). Merge commits and the base's commits are not judged; no label waives the check.
Usage: check_red_first.py --base origin/main --head HEAD. Exit 0 ok, 1 finding, 2 git error.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

PRODUCTION = ("backend/src/", "web/src/")
TESTS = ("backend/tests/", "web/tests/", "web/e2e/", "infra/tests/", "tests/", "fixtures/")
RED_LINE = re.compile(r"^Red:[ \t]*\S", re.MULTILINE)
FIELD, RECORD = "\x1f", "\x1e"


class Kind(Enum):
    CODE, TEST_ONLY, OTHER = "code", "test-only", "other"


@dataclass(frozen=True)
class Commit:
    sha: str
    subject: str
    body: str
    paths: tuple[str, ...]  # added, changed or renamed; a plain deletion is not a change


def classify(paths: Sequence[str]) -> Kind:
    if any(p.startswith(PRODUCTION) for p in paths):
        return Kind.CODE
    return Kind.TEST_ONLY if any(p.startswith(TESTS) for p in paths) else Kind.OTHER


def has_red_line(body: str) -> bool:
    return RED_LINE.search(body) is not None


def changed_paths(name_status: str) -> tuple[str, ...]:
    """Paths from `git diff-tree --name-status -M`, except plain deletions."""
    rows = (line.split("\t") for line in name_status.splitlines())
    return tuple(p for r in rows if len(r) > 1 and not r[0].startswith("D") for p in r[1:])


def findings(commits: Sequence[Commit]) -> list[Commit]:
    """Code commits without a red step; `commits` oldest first."""
    found: list[Commit] = []
    red_seen = False
    for c in commits:
        kind = classify(c.paths)
        if kind is Kind.CODE and not red_seen and not has_red_line(c.body):
            found.append(c)
        red_seen = red_seen or kind is Kind.TEST_ONLY
    return found


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def pr_commits(base: str, head: str) -> list[Commit]:
    fmt = f"--format={RECORD}%h{FIELD}%s{FIELD}%b"
    log = git("log", "--reverse", "--topo-order", "--no-merges", fmt, f"{base}..{head}")
    diff = ("diff-tree", "--root", "--no-commit-id", "-r", "-M", "--name-status")
    rows = (r.split(FIELD, 2) for r in log.split(RECORD)[1:])
    return [Commit(sha, s, b, changed_paths(git(*diff, sha))) for sha, s, b in rows]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", required=True, help="base ref, e.g. origin/main")
    ap.add_argument("--head", default="HEAD")
    args = ap.parse_args(argv)
    from pr_labels import live_labels  # I/O adapter; everything above main() stays pure

    live_labels(os.environ, "red-first")
    print("red-first: no label waives this check")
    try:
        commits = pr_commits(args.base, args.head)
    except subprocess.CalledProcessError as exc:
        print(f"red-first: git failed ({(exc.stderr or '').strip()}); failing closed")
        return 2
    found = findings(commits)
    if not found:
        print(f"red-first: ok, {len(commits)} commit(s) checked")
        return 0
    print(f"red-first: FAIL, {len(found)} code commit(s) without a red step")
    for c in found:
        code = ", ".join(p for p in c.paths if p.startswith(PRODUCTION))
        print(f"  {c.sha} {c.subject}: changes {code}")
    print("Add a 'Red:' body line (failing command and result) or an earlier test-only commit.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
