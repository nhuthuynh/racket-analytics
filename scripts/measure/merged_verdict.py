#!/usr/bin/env python3
"""Post-merge verdict check (FIX-03-2b; goal metric G03-12-PE-PR24-01; ledger row PE-PR24-01).

A merged pull request meets the review rule for a role only when that role's latest verdict
review is "Verdict: APPROVE" given on the head the PR was merged at (ADR 0039 rule 3; PO rule
2026-10-07). The verdict rule (submitted reviews by trusted authors, "Reviewer: <role>" on the
line after the verdict, latest per role) is `scripts/ci/merge_ready.py`'s, reused unchanged;
this script reads it after the merge, where `merge_ready.py` refuses a closed PR outright.

Usage: merged_verdict.py --repo OWNER/NAME --pr N --role ROLE [--role ROLE ...]
Env: GITHUB_TOKEN or GH_TOKEN (optional for a public repo); GITHUB_API_URL (default GitHub).
Exit codes: 0 met, 1 not met (reasons printed), 2 GitHub could not be read.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any


def _merge_ready() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "ci" / "merge_ready.py"
    spec = importlib.util.spec_from_file_location("merge_ready", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MR = _merge_ready()


def merged_reasons(
    pr: dict[str, Any], reviews: list[dict[str, Any]], roles: Sequence[str]
) -> list[str]:
    """Reasons the roles' verdicts do not meet the rule on the merged head; empty means met."""
    if not (pr.get("merged") or pr.get("merged_at")):
        return [f"PR #{pr.get('number')} is not merged (state {pr.get('state')})"]
    head = (pr.get("head") or {}).get("sha")
    latest = MR.verdicts(reviews)
    reasons = []
    for role in roles:
        if role not in latest:
            reasons.append(f"{role}: no verdict review on PR #{pr.get('number')}")
        elif latest[role] != (MR.APPROVE, head):
            verdict, at = latest[role]
            reasons.append(f"{role}: latest verdict {verdict} on {at}, not APPROVE on {head}")
    return reasons


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True, help="OWNER/NAME")
    ap.add_argument("--pr", required=True, type=int)
    ap.add_argument("--role", required=True, action="append", help="e.g. principal-engineer")
    args = ap.parse_args(argv)
    api = (os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
    base = f"{api}/repos/{args.repo}"
    try:
        pr, _ = MR._get(f"{base}/pulls/{args.pr}")
        reviews = MR._all_pages(f"{base}/pulls/{args.pr}/reviews")
    except (OSError, ValueError, KeyError) as exc:  # URLError is an OSError
        print(f"merged-verdict: unknown (GitHub could not be read: {exc})")
        return 2
    reasons = merged_reasons(pr, reviews, args.role)
    for reason in reasons:
        print(f"- {reason}")
    head = (pr.get("head") or {}).get("sha")
    status = "not met" if reasons else "met"
    print(f"merged-verdict: {status} (PR #{args.pr} merged head {head})")
    return 1 if reasons else 0


if __name__ == "__main__":
    sys.exit(main())
