#!/usr/bin/env python3
"""WIP gate: refuse a ticket start while a stage is full (QA-WIP-GATE).

Story PRC-06, atomic item PRC-12.1, goal metric G06-10, ADR 0056 decision 3,
working-agreement §3 "Flow and WIP limits", sprint-06 §2.1. The orchestrator runs it before
every "start ticket" step and logs a refusal; a refusal turns the next agent turn to review,
QA or merge work instead.

Stage of each open ticket PR into main (title "[ID] ..."), from GitHub REST only:
- in progress: the PR is a draft (ADR 0052);
- awaiting merge: ready, the latest verdicts of principal-engineer and senior-qa-engineer are
  "Verdict: APPROVE" on the head SHA and the head's `ci-gate` check run succeeded;
- awaiting QA: ready, principal-engineer approves the head and senior-qa-engineer has no
  verdict on it yet;
- in review: every other ready PR (no verdicts yet, an approve on an older head, a CHANGES
  REQUESTED on the head, or approves with a red or missing `ci-gate`).
The verdict rule (submitted reviews by trusted authors, "Reviewer: <role>" on the next line,
latest per role) is `scripts/ci/merge_ready.py`'s, reused unchanged.

A start is refused when it would put "in progress" over its limit, or when a later stage it
must pass through is full (count >= limit). Limits: 4, 3, 2, 1 (sprint-06 §2.1).

Usage: wip_gate.py --repo OWNER/NAME --stage start [--limits 4,3,2,1]
Env: GITHUB_TOKEN or GH_TOKEN (optional for a public repo); GITHUB_API_URL (default GitHub).
Exit codes: 0 start allowed, 1 start refused (the full stages are named),
2 GitHub could not be read or bad arguments (fail closed: no start, ADR 0014).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

IN_PROGRESS, IN_REVIEW, AWAITING_QA, AWAITING_MERGE = STAGES = (
    "in progress",
    "in review",
    "awaiting QA",
    "awaiting merge",
)
LIMITS = (4, 3, 2, 1)  # sprint-06 §2.1
TICKET = re.compile(r"^\[[A-Za-z0-9][\w.-]*\]")


def _merge_ready() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "ci" / "merge_ready.py"
    spec = importlib.util.spec_from_file_location("merge_ready", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MR = _merge_ready()


def is_ticket_pr(pr: Mapping[str, Any]) -> bool:
    return (
        pr.get("state") == "open"
        and (pr.get("base") or {}).get("ref") == "main"
        and bool(TICKET.match(pr.get("title") or ""))
    )


def head(pr: Mapping[str, Any]) -> str:
    return (pr.get("head") or {}).get("sha") or ""


def gate_green(check_runs: Sequence[Mapping[str, Any]]) -> bool:
    return any(
        r.get("name") == MR.GATE and r.get("status") == "completed" and r.get("conclusion") == "success"
        for r in check_runs
    )


def stage_of(
    pr: Mapping[str, Any],
    reviews: Sequence[dict[str, Any]],
    check_runs: Sequence[Mapping[str, Any]],
) -> str | None:
    """The stage of one open PR, or None when it is not a ticket PR into main."""
    if not is_ticket_pr(pr):
        return None
    if pr.get("draft"):
        return IN_PROGRESS
    sha = head(pr)
    latest = MR.verdicts(list(reviews))
    on_head = {role: v for role, (v, at) in latest.items() if at == sha}
    if MR.CHANGES in on_head.values() or on_head.get(MR.PRINCIPAL) != MR.APPROVE:
        return IN_REVIEW
    if MR.QA not in on_head:
        return AWAITING_QA
    return AWAITING_MERGE if gate_green(check_runs) else IN_REVIEW


def count_stages(
    pulls: Sequence[Mapping[str, Any]],
    reviews: Mapping[int, Sequence[dict[str, Any]]],
    check_runs: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, int]:
    counts = dict.fromkeys(STAGES, 0)
    for pr in pulls:
        found = stage_of(pr, reviews.get(pr["number"], ()), check_runs.get(head(pr), ()))
        if found:
            counts[found] += 1
    return counts


def start_refusals(counts: Mapping[str, int], limits: Sequence[int] = LIMITS) -> list[str]:
    """One line per stage that blocks a start; empty means the start is allowed."""
    found = []
    for stage, limit in zip(STAGES, limits, strict=True):
        n = counts[stage]
        if stage == IN_PROGRESS and n + 1 > limit:
            found.append(f"{stage} {n} of {limit} (a start would make {n + 1})")
        elif stage != IN_PROGRESS and n >= limit:
            found.append(f"{stage} {n} of {limit} (full)")
    return found


def stage_line(counts: Mapping[str, int]) -> str:
    """The stage-count line of working-agreement §7 3c, as flow_metrics.py parses it."""
    return " · ".join(f"{s} {counts[s]}" for s in STAGES).capitalize().replace("qa", "QA")


def _get(url: str) -> Any:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)  # noqa: S310 (https or local test stub)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return json.load(resp)


def _pages(url: str, key: str | None = None) -> list[dict[str, Any]]:
    """Paged with ?page=N, never the Link header (the agent proxy refuses its URL form)."""
    items: list[dict[str, Any]] = []
    sep = "&" if "?" in url else "?"
    for page in range(1, 1000):
        body = _get(f"{url}{sep}per_page=100&page={page}")
        chunk = body[key] if key else body
        if not chunk:
            break
        items.extend(chunk)
    return items


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--repo", required=True, help="OWNER/NAME")
    ap.add_argument("--stage", required=True, choices=["start"], help="the move to check")
    ap.add_argument("--limits", default=",".join(map(str, LIMITS)))
    args = ap.parse_args(argv)
    try:
        limits = tuple(int(x) for x in args.limits.split(","))
    except ValueError:
        limits = ()
    if len(limits) != len(STAGES):
        print("wip-gate: unknown (need 4 WIP limits)")
        return 2
    api = (os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
    base = f"{api}/repos/{args.repo}"
    try:
        pulls = [p for p in _pages(f"{base}/pulls?state=open") if is_ticket_pr(p)]
        ready = [p for p in pulls if not p.get("draft")]
        reviews = {p["number"]: _pages(f"{base}/pulls/{p['number']}/reviews") for p in ready}
        runs = {
            head(p): _pages(f"{base}/commits/{head(p)}/check-runs", "check_runs")
            for p in ready
            if stage_of(p, reviews[p["number"]], [{"name": MR.GATE, "status": "completed", "conclusion": "success"}])
            == AWAITING_MERGE
        }
    except (OSError, ValueError, KeyError, TypeError) as exc:  # URLError is an OSError
        print(f"wip-gate: unknown (GitHub could not be read: {exc})")
        return 2
    counts = count_stages(pulls, reviews, runs)
    print(stage_line(counts))
    found = start_refusals(counts, limits)
    if found:
        print(f"wip-gate: start refused: {'; '.join(found)}")
        return 1
    print("wip-gate: start allowed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
