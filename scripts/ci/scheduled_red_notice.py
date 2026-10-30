#!/usr/bin/env python3
"""Decide the product owner's notice for one completed workflow run (retro C4; ADR 0053).

CI FIRST depends on someone noticing a red `main`; between agent sessions nobody did (retro 4,
M6: main red for about 6 days). .github/workflows/scheduled-red-notice.yml runs this for every
completed run of a scheduled workflow and acts on --out-dir/action.txt:

* ``open``  a scheduled run failed (failure, timed_out, startup_failure): open one issue per
  workflow, assigned to the repository owner, or comment on the one already open;
* ``close`` a scheduled run passed: close that workflow's open issue;
* ``none``  anything else (not scheduled, cancelled, skipped, ...).

It writes title.txt and body.md (open/close) and summary.json, and never calls GitHub.
Usage: scheduled_red_notice.py --workflow NAME --event EVENT --conclusion C --run-url URL
       --sha SHA --date YYYY-MM-DD --out-dir DIR
Exit 0 decided, 2 an input is empty or invalid (fails closed: the notice job goes red).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

RED = frozenset({"failure", "timed_out", "startup_failure"})
TITLE = "[CI-RED] scheduled {workflow} run failed"
RUN_URL = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+/actions/runs/\d+(/attempts/\d+)?$")
FLAGS = ("workflow", "event", "conclusion", "run_url", "sha", "date", "out_dir")


class NoticeError(Exception):
    """An input the notice cannot be decided from."""


def decide(event: str, conclusion: str) -> str:
    if event != "schedule":
        return "none"
    if conclusion in RED:
        return "open"
    return "close" if conclusion == "success" else "none"


def title(workflow: str) -> str:
    return TITLE.format(workflow=workflow)


def red_body(workflow: str, conclusion: str, url: str, sha: str, date: str) -> str:
    return "\n".join(
        [
            f"The scheduled **{workflow}** run of {date} ended with `{conclusion}` on `main`.",
            "",
            f"- Run: {url}",
            f"- Commit: `{sha}`",
            "",
            "This notice is for the product owner: no agent session may be running, so nobody",
            "else has seen it (retro 4, M6). Under CI FIRST (PO 2026-10-08) the next session",
            "fixes this before any feature ticket. Each further red run of this workflow adds",
            "a comment here; the next green scheduled run closes this issue.",
            "",
        ]
    )


def green_body(workflow: str, url: str, sha: str, date: str) -> str:
    return f"The scheduled **{workflow}** run of {date} passed: {url} (commit `{sha}`). Closing.\n"


def write(args: argparse.Namespace) -> str:
    for flag in FLAGS:
        if not getattr(args, flag).strip():
            raise NoticeError(f"--{flag.replace('_', '-')} is empty")
    if not RUN_URL.match(args.run_url):
        raise NoticeError(f"--run-url {args.run_url!r} is not a GitHub Actions run URL")
    action = decide(args.event, args.conclusion)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "action.txt").write_text(action + "\n")
    if action != "none":
        (out / "title.txt").write_text(title(args.workflow) + "\n")
        body = (
            red_body(args.workflow, args.conclusion, args.run_url, args.sha, args.date)
            if action == "open"
            else green_body(args.workflow, args.run_url, args.sha, args.date)
        )
        (out / "body.md").write_text(body)
    summary = {"action": action, "workflow": args.workflow, "conclusion": args.conclusion}
    (out / "summary.json").write_text(json.dumps(summary) + "\n")
    return action


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for flag in FLAGS:
        ap.add_argument(f"--{flag.replace('_', '-')}", required=True)
    args = ap.parse_args(argv)
    try:
        action = write(args)
    except NoticeError as exc:
        print(f"scheduled_red_notice: {exc}", file=sys.stderr)
        return 2
    print(f"scheduled_red_notice: {args.workflow} {args.event} {args.conclusion} -> {action}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
