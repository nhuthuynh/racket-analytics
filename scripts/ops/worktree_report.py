"""List the agent worktrees and what to do with each (OPS-DISK-06, PRC-13.1).

Usage:
    python3 scripts/ops/worktree_report.py [--root /home/user/wt] [--repo owner/name] [--json]

For each directory under ROOT: its branch (`git rev-parse --abbrev-ref HEAD`) and the state of
the newest pull request from that branch (GitHub REST `GET /repos/{repo}/pulls?head=..&state=all`).
Action: "remove" when the PR is merged or closed, "keep" when it is open or no PR exists (unpushed
work is never removed), "check" for a detached HEAD or a directory that is not a worktree.
The report only reads; the owner removes a worktree with `git worktree remove <path>`.
Env: GITHUB_TOKEN or GH_TOKEN (optional for a public repo); GITHUB_API_URL (default GitHub).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

Fetch = Callable[[str], list[dict[str, Any]]]
ACTIONS = {"merged": "remove", "closed": "remove", "open": "keep", "no PR": "keep"}


def action(state: str) -> str:
    return ACTIONS.get(state, "check")


def pr_state(branch: str, fetch: Fetch, repo: str, api: str) -> tuple[str, int | None]:
    """The branch's PR state: an open PR wins, else the newest closed one (merged or not)."""
    owner = repo.split("/", 1)[0]
    head = urllib.parse.quote(f"{owner}:{branch}", safe="")
    prs = fetch(f"{api}/repos/{repo}/pulls?head={head}&state=all")
    if not prs:
        return "no PR", None
    open_prs = [p for p in prs if p.get("state") == "open"]
    pick = open_prs[0] if open_prs else max(prs, key=lambda p: p.get("number", 0))
    if pick.get("state") == "open":
        return "open", pick.get("number")
    return ("merged" if pick.get("merged_at") else "closed"), pick.get("number")


def _fetch(url: str) -> list[dict[str, Any]]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)  # noqa: S310 (https or local test stub)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        body: list[dict[str, Any]] = json.load(resp)
        return body


def branch_of(path: Path) -> str | None:
    res = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    name = res.stdout.strip()
    return name if res.returncode == 0 and name and name != "HEAD" else None


def report(root: Path, fetch: Fetch, repo: str, api: str) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(p for p in root.iterdir() if p.is_dir()):
        branch = branch_of(path) if (path / ".git").exists() else None
        if branch:
            state, number = pr_state(branch, fetch, repo, api)
        else:
            state = "detached" if (path / ".git").exists() else "not a worktree"
            number = None
        rows.append(
            {
                "path": str(path),
                "branch": branch,
                "pr": number,
                "state": state,
                "action": action(state),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path("/home/user/wt"))
    ap.add_argument("--repo", default="nhuthuynh/racket-analytics")
    ap.add_argument("--json", action="store_true", help="one JSON array instead of a table")
    args = ap.parse_args(argv)
    api = (os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
    rows = report(args.root, _fetch, args.repo, api)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows:
        pr = f"#{r['pr']}" if r["pr"] else "-"
        print(f"{r['action']:<7} {r['state']:<8} {pr:<6} {r['branch'] or '-':<60} {r['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
