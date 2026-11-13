"""Shared helpers of the Sprint 5 close checks (EM-CLOSE-CHECKS, PRC-6.1-6.3).

GitHub is read over REST only, paged with `?page=N` until an empty page (no GraphQL, no `Link`
header: both answer 403 through the agent proxy, decisions/QA-FLOW-METRICS.md).
Env: GITHUB_TOKEN or GH_TOKEN (optional for a public repo); GITHUB_API_URL (default GitHub).
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any

# A finding or ledger id: QA-VERIFY05R1-02, SEC-S5-TM-01, COACH-S5-01, PE-PLAN05-R3-03.
FINDING_ID = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+\b")
_OPEN = re.compile(r"^(open|not re-verified|not fixed|partly)", re.I)


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def plain(text: str) -> str:
    return text.replace("*", "").strip()


def is_open(disposition: str) -> bool:
    return bool(_OPEN.match(plain(disposition)))


def is_fixed(disposition: str) -> bool:
    return plain(disposition).lower().startswith("fixed")


def tables(text: str) -> list[tuple[list[str], list[tuple[int, list[str]]]]]:
    """Every Markdown table as (header, [(line number, cells)]), separator rows dropped."""
    out: list[tuple[list[str], list[tuple[int, list[str]]]]] = []
    current: tuple[list[str], list[tuple[int, list[str]]]] | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.lstrip().startswith("|"):
            current = None
            continue
        row = cells(line)
        if current is None:
            current = (row, [])
            out.append(current)
        elif not set("".join(row)) <= set("-: "):
            current[1].append((number, row))
    return out


def column(header: list[str], *keys: str) -> int | None:
    lowered = [h.lower() for h in header]
    for key in keys:
        for i, h in enumerate(lowered):
            if key in h:
                return i
    return None


def ledger_latest(text: str) -> dict[str, dict[str, Any]]:
    """Latest disposition of every finding id named in a ledger table's first column.

    A table without a disposition column gives its rows an empty disposition, which is neither
    Fixed nor treated as closed (fail closed, ADR 0014).
    """
    latest: dict[str, dict[str, Any]] = {}
    for header, rows in tables(text):
        disp = column(header, "disposition", "fix", "state", "status")
        for number, row in rows:
            disposition = row[disp] if disp is not None and disp < len(row) else ""
            for finding in dict.fromkeys(FINDING_ID.findall(row[0])):
                latest[finding] = {"disposition": plain(disposition), "line": number}
    return latest


def _get(url: str) -> Any:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)  # noqa: S310 (https or local test stub)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return json.load(resp)


def api_base(repo: str) -> str:
    api = (os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
    return f"{api}/repos/{repo}"


def all_pulls(repo: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for page in range(1, 1000):
        chunk = _get(f"{api_base(repo)}/pulls?state=all&per_page=100&page={page}")
        if not chunk:
            break
        items.extend(chunk)
    return items


def issue_state(repo: str, number: int) -> str:
    """`open` or `closed` for an issue or a pull request (the issues endpoint serves both)."""
    return str(_get(f"{api_base(repo)}/issues/{number}")["state"])


def merged_into_main(pr: dict[str, Any]) -> bool:
    return bool(pr.get("merged_at")) and pr.get("base", {}).get("ref") == "main"


def head_ref(pr: dict[str, Any]) -> str:
    return str(pr.get("head", {}).get("ref", ""))
