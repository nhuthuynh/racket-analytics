#!/usr/bin/env python3
"""Test and gold immutability guard (ST-003; EP/ENG-28; NFR-078).

Fails (exit 1) when the PR modifies, deletes or renames an existing file under a protected
path, unless the PR carries the `qa-approved-test-change` label (applied by the
senior-qa-engineer; label mechanism is judgment, see docs/process/ci-cd.md).
Adding new files is always allowed: TDD adds tests, it never rewrites accepted ones.

Usage: PR_LABELS='["a","b"]' check_test_immutability.py --base origin/main --head HEAD
`--base` is the base branch; the PR change set is diffed from its merge base with `--head`
(pr_change_set.py, CI-POLICY-BASE).
Exit codes: 0 ok, 1 violation, 2 usage or git error (fails closed).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from pr_change_set import ChangeSetError, diff

PROTECTED_PREFIXES = (
    "backend/tests/",
    "web/e2e/",
    "fixtures/gold/",
    "tests/features/",
)
APPROVAL_LABEL = "qa-approved-test-change"


def is_protected(path: str) -> bool:
    return path.startswith(PROTECTED_PREFIXES)


def violations(name_status: str) -> list[tuple[str, str]]:
    """Parse `git diff --name-status -M` output into (verb, path) violations."""
    found: list[tuple[str, str]] = []
    for line in name_status.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        kind = status[0]
        if kind == "A":
            continue
        if kind in {"R", "C"}:
            old, new = parts[1], parts[2]
            if kind == "R" and is_protected(old):
                found.append(("renamed", f"{old} -> {new}"))
            continue
        path = parts[1]
        if is_protected(path):
            verb = {"M": "modified", "D": "deleted", "T": "type-changed"}.get(kind, "changed")
            found.append((verb, path))
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", required=True, help="base branch, e.g. origin/main")
    ap.add_argument("--head", default="HEAD")
    args = ap.parse_args(argv)

    try:
        labels = json.loads(os.environ.get("PR_LABELS", "[]") or "[]")
        if not isinstance(labels, list):
            raise ValueError("PR_LABELS must be a JSON array")
    except ValueError as exc:
        print(f"test-immutability: cannot read PR_LABELS ({exc}); failing closed")
        return 2

    try:
        change_set = diff(args.base, args.head, "--name-status", "-M")
    except ChangeSetError as exc:
        print(f"test-immutability: {exc}; failing closed")
        return 2
    print(f"test-immutability: {change_set.describe(args.base, args.head)}")

    found = violations(change_set.changes)
    if not found:
        print("test-immutability: no existing test, scenario or gold file was changed.")
        return 0
    listing = "\n".join(f"  - {verb}: {path}" for verb, path in found)
    if APPROVAL_LABEL in labels:
        print(f"test-immutability: changes approved by label '{APPROVAL_LABEL}':\n{listing}")
        return 0
    print(
        "test-immutability: this PR changes accepted tests or gold data:\n"
        f"{listing}\n"
        "Accepted tests are never edited or deleted to make code pass (EP/ENG-28, NFR-078).\n"
        f"If the change is intended, the senior-qa-engineer reviews it and applies the "
        f"'{APPROVAL_LABEL}' label."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
