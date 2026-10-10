#!/usr/bin/env python3
"""Measure repository visibility (sprint-DoD row S3-DoD-P10; SEC-RV3-01; PO P12 option b).

    repo_visibility.py --repo nhuthuynh/racket-analytics \
        --po docs/requirements/po-input-2026-10-05.md [--dod docs/sprints/sprint-03.md]
    repo_visibility.py --from-answer answer.json --po ... [--dod ...]   # recorded answer

Asks GitHub's API as an anonymous reader, because the property is "world-readable or not":
HTTP 200 with "visibility": "public" or "private", or HTTP 404 (an anonymous reader cannot
see it). The row is met when the repository is private or hidden, or when the PO's decision
record has a P10 row confirming public ("confirmed public" / "keep public"). Otherwise it is
'not met: waiting on P10 (GitHub reports "visibility": "public")'.

Exit 0 met, 1 not met, 2 no usable answer or malformed input (fail closed, ADR 0014), 3 the
sprint plan's S3-DoD-P10 status says something other than the measurement.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

DOD_ROW = "S3-DoD-P10"
API = "https://api.github.com/repos/{repo}"
CONFIRMS_PUBLIC = re.compile(r"\b(confirmed public|keep public)\b", re.I)
STATUS = {
    "private": "met (repository is private)",
    "not-found": "met (repository is private: anonymous GitHub API returns 404)",
    "confirmed": "met (PO confirmed public)",
    "public": 'not met: waiting on P10 (GitHub reports "visibility": "public")',
}


def _cells(line: str) -> list[str]:
    return [" ".join(c.replace("**", "").split()) for c in line.strip().strip("|").split("|")]


def _rows(text: str):
    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            yield _cells(line)


def visibility(status: int, body: str) -> str:
    """'public', 'private' or 'not-found' from an anonymous GitHub API answer; else ValueError."""
    if status == 404:
        return "not-found"
    if status != 200:
        raise ValueError(f"GitHub answered HTTP {status}: {body[:200]!r}")
    try:
        found = json.loads(body).get("visibility")
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"GitHub answered HTTP 200 without JSON: {body[:200]!r}") from exc
    if found not in ("public", "private"):
        raise ValueError(f"GitHub answered visibility {found!r}, not public or private")
    return found


def po_confirmed_public(record: str) -> bool:
    """True only when a decision-table row for P10 confirms the repository stays public."""
    return any(
        re.match(r"P10\b", cells[0]) and len(cells) > 1 and CONFIRMS_PUBLIC.search(cells[1])
        for cells in _rows(record)
    )


def measure(seen: str, confirmed_public: bool) -> dict:
    """The S3-DoD-P10 result for what GitHub showed and whether the PO confirmed public."""
    key = "confirmed" if seen == "public" and confirmed_public else seen
    return {
        "visibility": seen,
        "po_confirmed_public": confirmed_public,
        "met": key != "public",
        "status": STATUS[key],
    }


def dod_status(plan: str) -> str:
    """The last cell of the plan's S3-DoD-P10 row, without Markdown emphasis."""
    for cells in _rows(plan):
        if cells[0] == DOD_ROW:
            return cells[-1]
    raise ValueError(f"the sprint plan has no {DOD_ROW} row")


def dod_verdict(status: str) -> str:
    """'met' or 'not met: waiting on P10': the status without its parenthesised note."""
    return status.split("(", 1)[0].strip()


def fetch(repo: str) -> tuple[int, str]:
    """GET the repository as an anonymous reader (no token, on purpose)."""
    request = urllib.request.Request(  # noqa: S310 (fixed https URL, no user scheme)
        API.format(repo=repo),
        headers={"Accept": "application/vnd.github+json", "User-Agent": "racket-analytics-measure"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 (same fixed URL)
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--repo", help="owner/name to ask GitHub about, anonymously")
    source.add_argument("--from-answer", type=Path, help='recorded {"status": n, "body": "..."}')
    parser.add_argument("--po", type=Path, required=True, help="the PO decision record")
    parser.add_argument("--dod", type=Path, help="sprint plan whose S3-DoD-P10 row must agree")
    args = parser.parse_args(argv)
    try:
        if args.repo:
            status, body = fetch(args.repo)
        else:
            recorded = json.loads(args.from_answer.read_text(encoding="utf-8"))
            status, body = int(recorded["status"]), str(recorded["body"])
        confirmed = po_confirmed_public(args.po.read_text(encoding="utf-8"))
        result = measure(visibility(status, body), confirmed)
        claimed = dod_status(args.dod.read_text(encoding="utf-8")) if args.dod else None
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"repo_visibility: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    if claimed is not None and dod_verdict(claimed) != dod_verdict(result["status"]):
        print(
            f"repo_visibility: {DOD_ROW} says {claimed!r} but GitHub and the PO record say "
            f"{result['status']!r}",
            file=sys.stderr,
        )
        return 3
    return 0 if result["met"] else 1


if __name__ == "__main__":
    sys.exit(main())
