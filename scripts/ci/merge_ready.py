#!/usr/bin/env python3
"""Merge readiness check (CI-PR-GATE; PO rule 2026-10-07; docs/ops/branch-protection.md).

A pull request may merge into `main` only when, on its current head SHA:
  * every current CI check run concluded success (a non-gate run may be `skipped` or `neutral`, e.g.
    the schedule-only flaky report), and `ci-gate` itself concluded success;
  * the latest review of the principal-engineer and the latest review of at least one
    senior-* role start with "Verdict: APPROVE" and were given on that SHA;
  * no role's latest review on that SHA says "Verdict: CHANGES REQUESTED".
All agents post as one GitHub account, so a review names its role on the line right after the
verdict ("Reviewer: <role>"). Only submitted reviews (COMMENTED, APPROVED, CHANGES_REQUESTED)
by a trusted author (author_association OWNER, MEMBER or COLLABORATOR) count, because anyone
can review a PR on a public repo and the token owner's own PENDING review is listed too.
A workflow triggered again on the same SHA (a label, a re-open) gets a new check suite; only
the newest workflow run per (workflow, event) counts, so the runs the older trigger left
behind (cancelled by `cancel-in-progress`, or failed) neither block nor hide a failure.

Usage: merge_ready.py --repo OWNER/NAME --pr N --sha HEAD_SHA
Env: GITHUB_TOKEN or GH_TOKEN (optional for a public repo); GITHUB_API_URL (default GitHub).
Exit codes: 0 merge-ready, 1 not ready (reasons printed), 2 GitHub could not be read.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from collections.abc import Sequence
from typing import Any

GATE = "ci-gate"
PRINCIPAL = "principal-engineer"
SENIOR_PREFIX = "senior-"
APPROVE = "APPROVE"
CHANGES = "CHANGES REQUESTED"
GREEN = {"success"}
GREEN_IF_NOT_GATE = {"success", "skipped", "neutral"}
SUBMITTED = {"COMMENTED", "APPROVED", "CHANGES_REQUESTED"}
TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}
_VERDICT = re.compile(
    r"\AVerdict:\s*(APPROVE|CHANGES REQUESTED)\b[^\n]*\r?\nReviewer:\s*([a-z-]+)[ \t]*\r?$",
    re.MULTILINE,
)
_NEXT = re.compile(r'<([^>]+)>;\s*rel="next"')


# ------------------------------------------------------------------ rule (no I/O)
def superseded_suites(workflow_runs: Sequence[dict[str, Any]]) -> set[Any]:
    """Check suites of workflow runs that a newer run of the same workflow and event replaced
    on this SHA. Suites without a workflow run (other apps) are never superseded."""
    newest: dict[tuple[Any, Any], dict[str, Any]] = {}
    for wr in workflow_runs:
        key = (wr.get("workflow_id"), wr.get("event"))
        if key not in newest or wr["id"] > newest[key]["id"]:
            newest[key] = wr
    current = {wr.get("check_suite_id") for wr in newest.values()}
    return {wr.get("check_suite_id") for wr in workflow_runs} - current


def latest_runs(
    check_runs: list[dict[str, Any]], workflow_runs: Sequence[dict[str, Any]] = ()
) -> dict[tuple[Any, str], dict[str, Any]]:
    """The newest run per (check suite, name) in the current suites; job re-runs get higher
    ids. Same-named jobs of two workflows are different suites, so one cannot hide the
    other's failure."""
    stale = superseded_suites(workflow_runs)
    latest: dict[tuple[Any, str], dict[str, Any]] = {}
    for run in check_runs:
        if (run.get("check_suite") or {}).get("id") in stale:
            continue
        key = ((run.get("check_suite") or {}).get("id"), run["name"])
        if key not in latest or run["id"] > latest[key]["id"]:
            latest[key] = run
    return latest


def verdicts(reviews: list[dict[str, Any]]) -> dict[str, tuple[str, str]]:
    """role -> (verdict, commit SHA) of that role's latest verdict review."""
    found: dict[str, tuple[tuple[str, int], str, str]] = {}
    for rv in reviews:
        match = _VERDICT.match((rv.get("body") or "").lstrip())
        if not match or rv.get("state") not in SUBMITTED:
            continue
        if rv.get("author_association") not in TRUSTED:
            continue
        verdict, role = match.groups()
        key = (rv.get("submitted_at") or "", rv["id"])
        if role not in found or key > found[role][0]:
            found[role] = (key, verdict, rv.get("commit_id") or "")
    return {role: (v, sha) for role, (_, v, sha) in found.items()}


def head_reasons(pr: dict[str, Any], sha: str) -> list[str]:
    """`sha` must be the head of an open PR into main (no stale-SHA merge)."""
    reasons: list[str] = []
    if pr.get("state") != "open":
        reasons.append(f"PR is {pr.get('state')}, not open")
    if pr.get("base", {}).get("ref") != "main":
        reasons.append(f"PR targets {pr.get('base', {}).get('ref')}, not main")
    if pr.get("head", {}).get("sha") != sha:
        reasons.append(f"{sha} is not the PR head ({pr.get('head', {}).get('sha')})")
    return reasons


def check_reasons(
    check_runs: list[dict[str, Any]],
    sha: str,
    workflow_runs: Sequence[dict[str, Any]] = (),
) -> list[str]:
    """Every latest check run of the current suites is green; ci-gate exists and succeeded."""
    current = latest_runs(check_runs, workflow_runs).values()
    runs = sorted(current, key=lambda r: (r["name"], r["id"]))
    reasons = [] if any(r["name"] == GATE for r in runs) else [f"no {GATE} check run on {sha}"]
    for run in runs:
        name = run["name"]
        outcome = run.get("conclusion") if run.get("status") == "completed" else run.get("status")
        if outcome not in (GREEN if name == GATE else GREEN_IF_NOT_GATE):
            reasons.append(f"check '{name}' is {outcome}")
    return reasons


def review_reasons(reviews: list[dict[str, Any]], sha: str) -> list[str]:
    """Principal and a senior approve the head; nobody's latest verdict there blocks."""
    latest = verdicts(reviews)
    reasons = [
        f"{role}: Verdict: {CHANGES} on the head"
        for role, (verdict, at) in sorted(latest.items())
        if verdict == CHANGES and at == sha
    ]
    principal = latest.get(PRINCIPAL)
    if principal != (APPROVE, sha):
        reasons.append(f"{PRINCIPAL}: no latest 'Verdict: {APPROVE}' on the head ({principal})")
    seniors = {r: v for r, v in latest.items() if r.startswith(SENIOR_PREFIX)}
    if (APPROVE, sha) not in seniors.values():
        reasons.append(f"senior reviewer: no latest 'Verdict: {APPROVE}' on the head ({seniors})")
    return reasons


def evaluate(
    pr: dict[str, Any],
    sha: str,
    check_runs: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    workflow_runs: Sequence[dict[str, Any]] = (),
) -> list[str]:
    """Reasons the PR may not merge at `sha`; an empty list means merge-ready."""
    return (
        head_reasons(pr, sha)
        + check_reasons(check_runs, sha, workflow_runs)
        + review_reasons(reviews, sha)
    )


# ------------------------------------------------------------------ GitHub REST (I/O)
def _get(url: str) -> tuple[Any, str | None]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)  # noqa: S310 (https or local test stub)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        link = _NEXT.search(resp.headers.get("Link") or "")
        return json.load(resp), link.group(1) if link else None


def _all_pages(url: str, key: str | None = None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    next_url: str | None = f"{url}{'&' if '?' in url else '?'}per_page=100"
    while next_url:
        body, next_url = _get(next_url)
        items.extend(body[key] if key else body)
    return items


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True, help="OWNER/NAME")
    ap.add_argument("--pr", required=True, type=int)
    ap.add_argument("--sha", required=True, help="the PR head SHA to be merged")
    args = ap.parse_args(argv)
    api = (os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
    base = f"{api}/repos/{args.repo}"
    try:
        pr, _ = _get(f"{base}/pulls/{args.pr}")
        runs = _all_pages(f"{base}/commits/{args.sha}/check-runs", "check_runs")
        reviews = _all_pages(f"{base}/pulls/{args.pr}/reviews")
        wruns = _all_pages(f"{base}/actions/runs?head_sha={args.sha}", "workflow_runs")
    except (OSError, ValueError, KeyError) as exc:  # URLError is an OSError
        print(f"merge-ready: unknown (GitHub could not be read: {exc})")
        return 2
    reasons = evaluate(pr, args.sha, runs, reviews, wruns)
    for reason in reasons:
        print(f"- {reason}")
    print(f"merge-ready: {'no' if reasons else 'yes'} (PR #{args.pr} at {args.sha})")
    return 1 if reasons else 0


if __name__ == "__main__":
    sys.exit(main())
