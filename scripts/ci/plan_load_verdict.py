#!/usr/bin/env python3
"""Verdict on a Locust run of backend/tests/perf/locustfile_plan.py (SRE-VERIFY04R3-01;
G04-02 c; NFR-019 read side).

    python3 scripts/ci/plan_load_verdict.py --stats reports/perf/plan_stats.csv \
        --history reports/perf/plan_stats_history.csv --state reports/perf/plan_state.json \
        --rps 50 --users 50 --json reports/perf/plan_verdict.json [--summary FILE]

Gates, the goal's targets unchanged: the account seeded with a plan; ``GET /me/plan`` (Locust
name ``plan``) p95 <= 300 ms, p99 <= 800 ms, availability >= 99.5%; the rate over the
steady window (all --users running, ``perf_verdict.measurement_window``) >= 95% of --rps and
the window >= --min-window seconds. A route with no samples fails closed.
Exit 0 all gates met; 1 a gate failed; 2 an input file is missing or unreadable.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from perf_verdict import (
    MIN_AVAILABILITY,
    MIN_RATE_SHARE,
    MIN_WINDOW_S,
    dashboard_reads,
    load_history,
    load_rows,
    measurement_window,
)

ROUTE = "plan"
P95_MS = 300.0  # G04-02 (c)
P99_MS = 800.0  # G04-02 (c)


def evaluate(rows: dict, history: list, state: dict, rps: float, users: int, min_window: float):
    plan = dashboard_reads(rows, (ROUTE,))[ROUTE]
    window = measurement_window(history, users) or {"seconds": 0, "rps": 0.0}
    sampled = plan["requests"] > 0
    checks = {
        "seeded": state.get("seeded") is True,
        "p95": sampled and plan["p95_ms"] is not None and plan["p95_ms"] <= P95_MS,
        "p99": sampled and plan["p99_ms"] is not None and plan["p99_ms"] <= P99_MS,
        "availability": sampled and plan["availability"] >= MIN_AVAILABILITY,
        "achieved_rps": window["rps"] >= MIN_RATE_SHARE * rps,
        "window": window["seconds"] >= min_window,
    }
    return {"ok": all(checks.values()), "checks": checks, "plan": plan, "window": window}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--stats", type=Path, required=True)
    p.add_argument("--history", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--rps", type=float, required=True)
    p.add_argument("--users", type=int, required=True)
    p.add_argument("--min-window", type=float, default=MIN_WINDOW_S)
    p.add_argument("--json", type=Path)
    p.add_argument("--summary", type=Path)
    args = p.parse_args(argv)
    try:
        rows, history = load_rows(args.stats), load_history(args.history)
        state = json.loads(args.state.read_text())
    except (OSError, ValueError, KeyError) as exc:
        print(f"plan-load-verdict: cannot read the run: {exc}", file=sys.stderr)
        return 2
    v = evaluate(rows, history, state, args.rps, args.users, args.min_window) | {"state": state}
    text = json.dumps(v, indent=2)
    print(text)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n")
    if args.summary:
        failed = [k for k, ok in v["checks"].items() if not ok] or ["none"]
        with args.summary.open("a") as fh:
            fh.write(
                f"### GET /me/plan at {args.rps:g} RPS (G04-02 c)\n\n"
                f"p95 {v['plan']['p95_ms']} ms, p99 {v['plan']['p99_ms']} ms, availability "
                f"{v['plan']['availability']}, {v['window']['rps']} RPS over "
                f"{v['window']['seconds']} s. Failed gates: {', '.join(failed)}\n"
            )
    return 0 if v["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
