#!/usr/bin/env python3
"""Red-first check: every code commit in a PR shows its red step (C4-RED; R3-IN-1, retro 3 B5).

A *code commit* adds or changes production code under backend/src or web/src. Its *red step* is
a `Red:` line in its own commit body (the failing command and result) or an earlier
*test-only commit* in the same PR (tests changed, no production code). The check fails when a
code commit has neither. Docs-only and test-only commits pass; merge commits are not judged;
commits already on the base are not the PR's.

Usage: check_red_first.py --base origin/main --head HEAD
Labels: no label waives this check. Like every pr-policy step it logs the PR's current labels
(pr_labels.py; GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER), so the job log shows that a
`size-waiver` or `qa-approved-test-change` label did not affect it.
Exit codes: 0 ok, 1 a code commit without a red step, 2 usage or git error (fails closed).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum

PRODUCTION_PREFIXES = ("backend/src/", "web/src/")
TEST_PREFIXES = (
    "backend/tests/",
    "web/tests/",
    "web/e2e/",
    "infra/tests/",
    "tests/",
    "fixtures/",
)
RED_LINE = re.compile(r"^Red:[ \t]*\S", re.MULTILINE)
FIELD = "\x1f"  # unit separator between the fields of one commit in `git log` output
RECORD = "\x1e"  # record separator between commits


class Kind(Enum):
    CODE = "code"
    TEST_ONLY = "test-only"
    OTHER = "other"


@dataclass(frozen=True)
class Commit:
    sha: str
    subject: str
    body: str
    paths: tuple[str, ...]  # added, changed or renamed paths; a deletion alone is not a change

    @property
    def kind(self) -> Kind:
        return classify(self.paths)

    @property
    def code_paths(self) -> tuple[str, ...]:
        return tuple(p for p in self.paths if p.startswith(PRODUCTION_PREFIXES))


@dataclass(frozen=True)
class Finding:
    sha: str
    subject: str
    code_paths: tuple[str, ...]


def classify(paths: Iterable[str]) -> Kind:
    paths = tuple(paths)
    if any(p.startswith(PRODUCTION_PREFIXES) for p in paths):
        return Kind.CODE
    if any(p.startswith(TEST_PREFIXES) for p in paths):
        return Kind.TEST_ONLY
    return Kind.OTHER


def has_red_line(body: str) -> bool:
    return RED_LINE.search(body) is not None


def changed_paths(name_status: str) -> tuple[str, ...]:
    """Paths from `git diff-tree --name-status -M`: every status but a plain deletion."""
    paths: list[str] = []
    for line in name_status.splitlines():
        parts = line.split("\t")
        if len(parts) < 2 or parts[0].startswith("D"):
            continue
        paths.extend(parts[1:])
    return tuple(paths)


def findings(commits: Sequence[Commit]) -> list[Finding]:
    """`commits` oldest first. A test-only commit is the red step of every later code commit."""
    found: list[Finding] = []
    red_seen = False
    for c in commits:
        kind = c.kind
        if kind is Kind.CODE and not red_seen and not has_red_line(c.body):
            found.append(Finding(c.sha, c.subject, c.code_paths))
        red_seen = red_seen or kind is Kind.TEST_ONLY
    return found


# ------------------------------------------------------------------ git (the only I/O)
def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def pr_commits(base: str, head: str) -> list[Commit]:
    log = git(
        "log", "--reverse", "--topo-order", "--no-merges",
        f"--format={RECORD}%h{FIELD}%s{FIELD}%b", f"{base}..{head}",
    )  # fmt: skip
    commits = []
    for record in log.split(RECORD)[1:]:
        sha, subject, body = record.split(FIELD, 2)
        diff = git("diff-tree", "--root", "--no-commit-id", "-r", "-M", "--name-status", sha)
        commits.append(Commit(sha, subject, body, changed_paths(diff)))
    return commits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", required=True, help="base ref, e.g. origin/main")
    ap.add_argument("--head", default="HEAD")
    args = ap.parse_args(argv)
    from pr_labels import live_labels  # I/O adapter; the classification above stays pure

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
    for f in found:
        print(f"  {f.sha} {f.subject}: changes {', '.join(f.code_paths)}")
    print(
        "A code commit (backend/src, web/src) needs a 'Red:' line in its body (the failing command"
        " and result) or an earlier test-only commit in this PR (testing-strategy §TDD, C4-RED)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
