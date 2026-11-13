#!/usr/bin/env python3
"""Is the latest scheduled CI or Nightly quality run on `main` red? (CI-SCHEDULED-RED, PRC-9.1)

CI FIRST needs a red scheduled run to be seen: run 43007950254 (2026-11-11) failed while the
red-run notice ran only as `skipped` on push events, so no status record named it. This report
prints one line per watched workflow for the EM status record, and `merge_ready.py` imports
`block_reason` to refuse merges while the latest scheduled CI run on `main` is red.

    scheduled_red.py --repo OWNER/NAME         # live: scheduled runs on main from GitHub
    scheduled_red.py --payload RUN.json [...]  # replay recorded run objects or run listings

A line starts `scheduled-red: RED` (red), `scheduled-red: green` or `scheduled-red: none` (no
completed scheduled run of that workflow listed). Env: GITHUB_TOKEN or GH_TOKEN (optional for
a public repo); GITHUB_API_URL (default GitHub).
Exit 0 no watched workflow is red, 1 at least one is red, 2 the runs could not be read.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

CI = ".github/workflows/ci.yml"
WATCHED = {CI: "CI", ".github/workflows/nightly-quality.yml": "Nightly quality"}
# Same set as scheduled_red_notice.py: GitHub reports a job timeout as `cancelled`.
RED = frozenset({"failure", "timed_out", "startup_failure", "cancelled"})
RUNS_QUERY = "event=schedule&branch=main&status=completed&per_page=30"
LISTING = f"actions/runs?{RUNS_QUERY}"  # every workflow, newest first
CI_LISTING = f"actions/workflows/{CI.rsplit('/', 1)[1]}/runs?{RUNS_QUERY}"  # CI only


def latest(runs: Iterable[dict[str, Any]], path: str) -> dict[str, Any] | None:
    """The newest completed scheduled run of the workflow at `path` on `main`."""
    found = [
        r
        for r in runs
        if r.get("path") == path
        and r.get("event") == "schedule"
        and r.get("head_branch") == "main"
        and r.get("status") == "completed"
    ]
    return max(found, key=lambda r: (r.get("created_at") or "", r["id"]), default=None)


def is_red(run: dict[str, Any]) -> bool:
    return run.get("conclusion") in RED


def describe(run: dict[str, Any]) -> str:
    return (
        f"run {run['id']} at {str(run.get('head_sha'))[:8]} ended {run.get('conclusion')} "
        f"({run.get('created_at')}) {run.get('html_url', '')}".rstrip()
    )


def report(runs: Sequence[dict[str, Any]]) -> list[str]:
    """One status-record line per watched workflow, from its latest scheduled run on main."""
    lines = []
    for path, name in WATCHED.items():
        run = latest(runs, path)
        if run is None:
            lines.append(f"scheduled-red: none {name}: no completed scheduled run on main listed")
        else:
            colour = "RED" if is_red(run) else "green"
            lines.append(f"scheduled-red: {colour} {name} {describe(run)}")
    return lines


def block_reason(runs: Sequence[dict[str, Any]]) -> str | None:
    """Why a merge is refused: the latest scheduled CI run on main is red; else None."""
    run = latest(runs, CI)
    if run is None or not is_red(run):
        return None
    return f"the latest scheduled CI {describe(run)} on main: fix main first (CI FIRST)"


def from_payload(data: Any) -> list[dict[str, Any]]:
    """Run objects from a recorded single run or a `{"workflow_runs": [...]}` listing."""
    if isinstance(data, dict) and isinstance(data.get("workflow_runs"), list):
        return list(data["workflow_runs"])
    if isinstance(data, dict) and "id" in data:
        return [data]
    raise ValueError("neither a workflow run nor a workflow_runs listing")


def fetch(api: str, repo: str) -> list[dict[str, Any]]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{api.rstrip('/')}/repos/{repo}/{LISTING}"
    req = urllib.request.Request(url, headers=headers)  # noqa: S310 (https or local test stub)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return from_payload(json.load(resp))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--repo", help="OWNER/NAME: read the scheduled runs on main from GitHub")
    src.add_argument("--payload", nargs="+", type=Path, help="recorded run JSON files")
    args = ap.parse_args(argv)
    try:
        if args.repo:
            api = os.environ.get("GITHUB_API_URL") or "https://api.github.com"
            runs = fetch(api, args.repo)
        else:
            runs = [r for p in args.payload for r in from_payload(json.loads(p.read_text()))]
    except (OSError, ValueError, KeyError, TypeError) as exc:  # URLError is an OSError
        print(f"scheduled-red: unknown (runs could not be read: {exc})")
        return 2
    lines = report(runs)
    print("\n".join(lines))
    return 1 if any(line.startswith("scheduled-red: RED ") for line in lines) else 0


if __name__ == "__main__":
    sys.exit(main())
