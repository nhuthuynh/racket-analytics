#!/usr/bin/env python3
"""Flow metrics and cost-per-PR completeness from the GitHub REST API (QA-FLOW-METRICS).

Story PRC-05, atomic items PRC-5.1-5.5, goal metric G05-11, ADR 0056 decisions 1 and 3,
working-agreement §10. The values are reported, never targets [ASB/AGL-02].

Reads (REST only, paged with ?page=N because the agent proxy refuses GitHub's Link URLs):
GET /repos/{repo}/pulls?state=closed|open, /pulls/{n}/commits, /actions/runs?event=pull_request.
Writes: cycle time (first commit -> merge; median, max), PR time-to-merge (open -> merge),
throughput (PRs merged into main in the window), work item age of open PRs into main, WIP
breaches (the "In progress N · in review N · awaiting QA N · awaiting merge N" lines of the
decisions files), CI minutes per PR (workflow-run wall time on the PR's branch between open and
merge) and cost-table completeness (a "Cost per PR" table with at least one row in
decisions/<TICKET-ID>.md; the ticket id is the PR title's "[ID]" prefix).

Usage: flow_metrics.py --repo OWNER/NAME --decisions DIR [--since DATE] [--until DATE]
       [--pr-from N] [--pr-to N] [--wip-limits 4,3,2,1] [--now ISO] [--json PATH]
Env: GITHUB_TOKEN or GH_TOKEN (optional for a public repo); GITHUB_API_URL (default GitHub).
Exit codes: 0 measured and complete, 1 measured but a merged ticket has no cost table,
2 GitHub could not be read or bad arguments (fail closed, ADR 0014).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NamedTuple

STAGES = ("in progress", "in review", "awaiting QA", "awaiting merge")
DEFAULT_LIMITS = (4, 3, 2, 1)  # sprint-05 §2.1
_SEP = r"\s*[·,;]\s*"
STAGE_LINE = re.compile(
    rf"in progress\s+(\d+){_SEP}in review\s+(\d+){_SEP}awaiting qa\s+(\d+){_SEP}"
    r"awaiting merge\s+(\d+)",
    re.IGNORECASE,
)
TICKET = re.compile(r"^\[([A-Za-z0-9][\w.-]*)\]")
COST_HEADING = re.compile(r"^#+\s.*cost per pr", re.IGNORECASE)
NOT_MEASURED = "not measured"


class Window(NamedTuple):
    # A NamedTuple, not a dataclass: tests load this file without registering it in sys.modules.
    since: datetime | None = None  # merged_at >= since
    until: datetime | None = None  # merged_at < until
    pr_from: int | None = None
    pr_to: int | None = None

    def has_number(self, n: int) -> bool:
        return (self.pr_from is None or n >= self.pr_from) and (
            self.pr_to is None or n <= self.pr_to
        )

    def has_merge(self, at: datetime) -> bool:
        return (self.since is None or at >= self.since) and (self.until is None or at < self.until)


def ts(text: str) -> datetime:
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return (value if value.tzinfo else value.replace(tzinfo=UTC)).astimezone(UTC)


def hours(start: datetime, end: datetime) -> float:
    return round((end - start).total_seconds() / 3600, 1)


def ticket_of(pr: dict[str, Any]) -> str | None:
    m = TICKET.match(pr.get("title") or "")
    return m.group(1) if m else None


def into_main(pr: dict[str, Any]) -> bool:
    return (pr.get("base") or {}).get("ref") == "main"


def counts_as_merged(pr: dict[str, Any], window: Window) -> bool:
    """Merged into main, inside the number range and the merge window (PRC-5.2)."""
    return bool(
        pr.get("merged_at")
        and into_main(pr)
        and window.has_number(pr["number"])
        and window.has_merge(ts(pr["merged_at"]))
    )


def counts_as_open(pr: dict[str, Any], window: Window) -> bool:
    return into_main(pr) and window.has_number(pr["number"])


def first_commit(commits: list[dict[str, Any]]) -> datetime | None:
    dates = [ts(c["commit"]["author"]["date"]) for c in commits]
    return min(dates) if dates else None


def stage_breaches(
    decisions_dir: Path, limits: tuple[int, ...]
) -> tuple[int, list[dict[str, Any]]]:
    lines, rows = 0, []
    for path in sorted(decisions_dir.glob("*.md")):
        for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            m = STAGE_LINE.search(line)
            if not m:
                continue
            lines += 1
            reason = line[m.end() :].strip(" .·,;:-") or None
            for stage, count, limit in zip(STAGES, map(int, m.groups()), limits, strict=True):
                if count > limit:
                    rows.append(
                        {
                            "file": path.name,
                            "line": no,
                            "stage": stage,
                            "count": count,
                            "limit": limit,
                            "reason": reason,
                        }
                    )
    return lines, rows


def cost_rows(text: str) -> list[list[str]]:
    """Data rows of the first table under a "Cost per PR" heading; [] when there is none."""
    rows: list[list[str]] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("#"):
            if in_section and rows:
                break
            in_section = bool(COST_HEADING.match(line))
            continue
        if in_section and line.lstrip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append(cells)
        elif in_section and rows:
            break
    data = [r for r in rows[1:] if not all(set(c) <= set("-: ") for c in r)]
    return data


def measure(
    closed: list[dict[str, Any]],
    open_prs: list[dict[str, Any]],
    commits: dict[int, list[dict[str, Any]]],
    runs: list[dict[str, Any]],
    decisions_dir: Path,
    window: Window,
    now: datetime,
    limits: tuple[int, ...] = DEFAULT_LIMITS,
) -> dict[str, Any]:
    merged = sorted((p for p in closed if counts_as_merged(p, window)), key=lambda p: p["number"])
    rows, cycles, to_merge = [], [], []
    for p in merged:
        start, end = first_commit(commits.get(p["number"], [])), ts(p["merged_at"])
        cycle = hours(start, end) if start else None
        if cycle is not None:
            cycles.append(cycle)
        to_merge.append(hours(ts(p["created_at"]), end))
        rows.append(
            {
                "number": p["number"],
                "ticket": ticket_of(p),
                "cycle_time_h": cycle,
                "time_to_merge_h": to_merge[-1],
            }
        )
    median_cycle = statistics.median(cycles) if cycles else None

    ages = []
    for p in sorted(open_prs, key=lambda p: p["number"]):
        if not counts_as_open(p, window):
            continue
        start = first_commit(commits.get(p["number"], [])) or ts(p["created_at"])
        age = hours(start, now)
        over = median_cycle is not None and age > median_cycle
        ages.append(
            {
                "number": p["number"],
                "ticket": ticket_of(p),
                "age_h": age,
                "over_median_cycle_time": over,
            }
        )

    ci = []
    for p in merged:
        opened, end = ts(p["created_at"]), ts(p["merged_at"])
        mine = [
            r
            for r in runs
            if r.get("head_branch") == (p.get("head") or {}).get("ref")
            and r.get("run_started_at")
            and opened <= ts(r["run_started_at"]) <= end
        ]
        minutes = sum((ts(r["updated_at"]) - ts(r["run_started_at"])).total_seconds() for r in mine)
        ci.append(
            {
                "number": p["number"],
                "ticket": ticket_of(p),
                "runs": len(mine),
                "minutes": round(minutes / 60, 1),
            }
        )

    missing, not_measured = [], []
    for p in merged:
        ticket = ticket_of(p)
        path = decisions_dir / f"{ticket}.md"
        data = cost_rows(path.read_text(encoding="utf-8")) if ticket and path.is_file() else []
        if not data:
            missing.append(f"#{p['number']} {ticket or '(no ticket id)'}")
        not_measured += [f"{ticket}: {r[0]}" for r in data if NOT_MEASURED in " ".join(r).lower()]
    with_table = len(merged) - len(missing)

    stage_lines, breaches = stage_breaches(decisions_dir, limits)
    return {
        "throughput": len(merged),
        "cycle_time_h": {
            "n": len(cycles),
            "median": median_cycle,
            "max": max(cycles) if cycles else None,
        },
        "time_to_merge_h": {
            "n": len(to_merge),
            "median": statistics.median(to_merge) if to_merge else None,
            "mean": round(statistics.mean(to_merge), 1) if to_merge else None,
            "max": max(to_merge) if to_merge else None,
        },
        "work_item_age": ages,
        "wip_breaches": {"stage_lines": stage_lines, "count": len(breaches), "rows": breaches},
        "ci_minutes": ci,
        "ci_minutes_total": round(sum(r["minutes"] for r in ci), 1),
        "cost_tables": {
            "merged": len(merged),
            "with_table": with_table,
            "share": round(with_table / len(merged), 3) if merged else None,
            "missing": missing,
            "not_measured": not_measured,
        },
        "complete": not missing,
        "merged": rows,
    }


def _get(url: str) -> Any:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)  # noqa: S310 (https or local test stub)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return json.load(resp)


def _pages(url: str, key: str | None = None) -> list[dict[str, Any]]:
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
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True, help="OWNER/NAME")
    ap.add_argument("--decisions", required=True, type=Path, help="docs/sprints/<nn>/decisions")
    ap.add_argument("--since", type=ts, help="merged at or after (ISO date or time, UTC)")
    ap.add_argument("--until", type=ts, help="merged before (ISO date or time, UTC)")
    ap.add_argument("--pr-from", type=int)
    ap.add_argument("--pr-to", type=int)
    ap.add_argument("--wip-limits", default=",".join(map(str, DEFAULT_LIMITS)))
    ap.add_argument("--now", type=ts, help="age reference time (default: now)")
    ap.add_argument("--json", type=Path, help="write the full report here")
    args = ap.parse_args(argv)
    limits = tuple(int(x) for x in args.wip_limits.split(","))
    if len(limits) != len(STAGES) or not args.decisions.is_dir():
        print("flow-metrics: unknown (need 4 WIP limits and an existing --decisions dir)")
        return 2
    window = Window(args.since, args.until, args.pr_from, args.pr_to)
    api = (os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
    base = f"{api}/repos/{args.repo}"
    try:
        closed = _pages(f"{base}/pulls?state=closed")
        open_prs = _pages(f"{base}/pulls?state=open")
        wanted = [p for p in closed if counts_as_merged(p, window)]
        wanted += [p for p in open_prs if counts_as_open(p, window)]
        commits = {p["number"]: _pages(f"{base}/pulls/{p['number']}/commits") for p in wanted}
        oldest = min((ts(p["created_at"]) for p in wanted), default=datetime.now(UTC))
        day = (oldest - timedelta(days=1)).date().isoformat()
        runs = _pages(
            f"{base}/actions/runs?event=pull_request&created=%3E%3D{day}", "workflow_runs"
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:  # URLError is an OSError
        print(f"flow-metrics: unknown (GitHub could not be read: {exc})")
        return 2
    now = args.now or datetime.now(UTC)
    report = measure(closed, open_prs, commits, runs, args.decisions, window, now, limits)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    ct, tm, cost = report["cycle_time_h"], report["time_to_merge_h"], report["cost_tables"]
    print(f"throughput: {report['throughput']} PRs merged into main")
    print(f"cycle time (first commit -> merge): median {ct['median']} h, max {ct['max']} h")
    print(
        f"time to merge (open -> merge): median {tm['median']} h, mean {tm['mean']} h, "
        f"max {tm['max']} h"
    )
    for a in report["work_item_age"]:
        flag = " (over the median cycle time)" if a["over_median_cycle_time"] else ""
        print(f"age: #{a['number']} {a['ticket']} {a['age_h']} h{flag}")
    wip = report["wip_breaches"]
    print(f"WIP breaches: {wip['count']} (from {wip['stage_lines']} stage-count lines)")
    for b in wip["rows"]:
        print(
            f"- {b['file']}:{b['line']} {b['stage']} {b['count']} > {b['limit']}: "
            f"{b['reason'] or 'no reason given'}"
        )
    print(f"CI minutes: {report['ci_minutes_total']} over {len(report['ci_minutes'])} PRs")
    print(f"cost tables: {cost['with_table']} of {cost['merged']} merged tickets")
    for m in cost["missing"]:
        print(f"- no cost table: {m}")
    for m in cost["not_measured"]:
        print(f"- not measured: {m}")
    status = "complete" if report["complete"] else "incomplete"
    print(f"flow-metrics: measured, {status}")
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
