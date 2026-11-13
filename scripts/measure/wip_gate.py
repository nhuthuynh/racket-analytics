#!/usr/bin/env python3
"""WIP gate: refuse a ticket start while a stage is full (QA-WIP-GATE).

Story PRC-06, atomic item PRC-12.1, goal metric G06-10, ADR 0056 decision 3,
working-agreement §3 "Flow and WIP limits", sprint-06 §2.1. The orchestrator runs it before
every "start ticket" step and logs a refusal; a refusal turns the next agent turn to review,
QA or merge work instead.

Stage of each open ticket PR into main (head branch s<nn>/<id> as `merge_ready.py` reads it, or
title "[ID] ..."), from GitHub REST only:
- in progress: the PR is a draft (ADR 0052);
- awaiting merge: `scripts/ci/merge_ready.py` exits 0 on the head (working-agreement §3); it is
  run only for ready PRs with an APPROVE and no CHANGES REQUESTED on the head;
- awaiting QA: ready, not merge-ready, principal-engineer approves the head and
  senior-qa-engineer has no verdict on it yet;
- in review: every other ready PR (no verdicts yet, an approve on an older head only, a CHANGES
  REQUESTED on the head, or approves that `merge_ready.py` still refuses).
The verdict rule (submitted reviews by trusted authors, "Reviewer: <role>" on the next line,
latest per role) is `merge_ready.py`'s, reused unchanged.

A start is refused when it would put "in progress" over its limit, or when a later stage it
must pass through is full (count >= limit). Limits: 4, 3, 2, 1 (sprint-06 §2.1).

Usage: wip_gate.py --repo OWNER/NAME --stage start [--limits 4,3,2,1] [--merge-ready PATH]
(--merge-ready: the merge-readiness script to run, default scripts/ci/merge_ready.py.)
Env: GITHUB_TOKEN or GH_TOKEN (optional for a public repo); GITHUB_API_URL (default GitHub).
Exit codes: 0 start allowed, 1 start refused (the full stages are named), 2 GitHub or
merge_ready.py could not answer, or bad arguments (fail closed: no start, ADR 0014).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import urllib.request
from collections.abc import Collection, Mapping, Sequence
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


MERGE_READY = Path(__file__).resolve().parents[1] / "ci" / "merge_ready.py"


def _merge_ready() -> ModuleType:
    spec = importlib.util.spec_from_file_location("merge_ready", MERGE_READY)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {MERGE_READY}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MR = _merge_ready()


def is_ticket_pr(pr: Mapping[str, Any]) -> bool:
    """An open PR into main whose head branch is `s<nn>/<id>` (`merge_ready.py`'s
    `_TICKET_BRANCH`) or whose title starts `[ID]`; either one is enough (PE-QWG-01)."""
    branch = (pr.get("head") or {}).get("ref") or ""
    return (
        pr.get("state") == "open"
        and (pr.get("base") or {}).get("ref") == "main"
        and (
            MR._TICKET_BRANCH.fullmatch(branch) is not None
            or bool(TICKET.match(pr.get("title") or ""))
        )
    )


def head(pr: Mapping[str, Any]) -> str:
    return (pr.get("head") or {}).get("sha") or ""


def on_head(pr: Mapping[str, Any], reviews: Sequence[dict[str, Any]]) -> dict[str, str]:
    """role -> verdict, for each role whose latest verdict was given on the PR's head SHA."""
    sha = head(pr)
    return {role: v for role, (v, at) in MR.verdicts(list(reviews)).items() if at == sha}


def merge_candidate(pr: Mapping[str, Any], reviews: Sequence[dict[str, Any]]) -> bool:
    """A ready ticket PR with an APPROVE and no CHANGES REQUESTED on its head: the only PRs
    `merge_ready.py` is asked about (it cannot pass without one; tier 0 needs any one role)."""
    verdicts = on_head(pr, reviews).values()
    return (
        is_ticket_pr(pr)
        and not pr.get("draft")
        and MR.APPROVE in verdicts
        and MR.CHANGES not in verdicts
    )


def stage_of(
    pr: Mapping[str, Any], reviews: Sequence[dict[str, Any]], merge_ready: bool = False
) -> str | None:
    """The stage of one open PR, or None when it is not a ticket PR into main. `merge_ready` is
    whether `scripts/ci/merge_ready.py` exits 0 on the PR's head."""
    if not is_ticket_pr(pr):
        return None
    if pr.get("draft"):
        return IN_PROGRESS
    if merge_ready and merge_candidate(pr, reviews):
        return AWAITING_MERGE
    verdicts = on_head(pr, reviews)
    if (
        MR.CHANGES not in verdicts.values()
        and verdicts.get(MR.PRINCIPAL) == MR.APPROVE
        and MR.QA not in verdicts
    ):
        return AWAITING_QA
    return IN_REVIEW


def count_stages(
    pulls: Sequence[Mapping[str, Any]],
    reviews: Mapping[int, Sequence[dict[str, Any]]],
    merge_ready: Collection[int] = (),
) -> dict[str, int]:
    counts = dict.fromkeys(STAGES, 0)
    for pr in pulls:
        n = pr["number"]
        found = stage_of(pr, reviews.get(n, ()), n in merge_ready)
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
    line = " · ".join(f"{stage} {counts[stage]}" for stage in STAGES)
    return line[0].upper() + line[1:]


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


def _merge_ready_rc(args: argparse.Namespace, pr: Mapping[str, Any]) -> int:
    """0 merge-ready, 1 not; anything else is unknown and raises (fail closed)."""
    cmd = [sys.executable, str(args.merge_ready), "--repo", args.repo, "--pr", str(pr["number"])]
    done = subprocess.run(  # noqa: S603 (fixed script, arguments from the REST listing)
        [*cmd, "--sha", head(pr)], capture_output=True, text=True, timeout=300, check=False
    )
    if done.returncode not in (0, 1):
        raise ValueError(f"merge_ready.py on #{pr['number']} exited {done.returncode}")
    return done.returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--repo", required=True, help="OWNER/NAME")
    ap.add_argument("--stage", required=True, choices=["start"], help="the move to check")
    ap.add_argument("--limits", default=",".join(map(str, LIMITS)))
    ap.add_argument("--merge-ready", type=Path, default=MERGE_READY)
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
        merge_ready = {
            p["number"]
            for p in ready
            if merge_candidate(p, reviews[p["number"]]) and _merge_ready_rc(args, p) == 0
        }
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        # URLError is an OSError; a merge_ready.py exit other than 0 or 1 is a ValueError.
        print(f"wip-gate: unknown (GitHub or merge_ready.py could not answer: {exc})")
        return 2
    counts = count_stages(pulls, reviews, merge_ready)
    print(stage_line(counts))
    found = start_refusals(counts, limits)
    if found:
        print(f"wip-gate: start refused: {'; '.join(found)}")
        return 1
    print("wip-gate: start allowed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
