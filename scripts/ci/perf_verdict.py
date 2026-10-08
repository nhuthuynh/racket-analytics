#!/usr/bin/env python3
"""Verdict on a Locust run of backend/tests/perf/locustfile_sprint02.py (ST-039, SRE slice).

    python3 scripts/ci/perf_verdict.py --stats reports/perf/perf_stats.csv \
        --state reports/perf/perf_state.json --rps 50 --json reports/perf/verdict.json \
        [--history reports/perf/perf_stats_history.csv --users 51] \
        [--summary "$GITHUB_STEP_SUMMARY"]

Gates (sprint-02 §8): every endpoint exercised; availability (non-failed / all) >= 99.5%
(NFR-041); correction and undo p95 <= 1,500 ms (NFR-013, the larger of the two p95s); the
sheet restored byte-identical after the correction+undo pairs (C-04); the account and match
seeded; achieved rate >= 95% of --rps. Read p95/p99 (NFR-010) is a baseline: reported, not
gated, until the R1 review (sprint-02 §3.1).

Achieved rate (CI-PERF-GATES): with --history (Locust's ``_stats_history.csv``) and --users,
the rate is measured over the steady-state **measurement window**: from the first sample in
which all --users are running (the **warm-up** before it, i.e. seeding in ``test_start`` and
user spawn, which Locust counts inside --run-time, is excluded) to the last such sample. The
window must last at least --min-window seconds (default 60), else the run fails. Without
--history the whole-run rate is gated (stricter). Availability and latency always cover the
whole run, warm-up included.

Exit 0 all gates met; 1 a gate failed; 2 the stats or state file is missing or unreadable.
Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

READS = ("score-sheet", "corrections", "match")
COMMANDS = ("correct", "undo")
MIN_AVAILABILITY = 0.995
MAX_CORRECTION_P95_MS = 1500.0
MIN_RATE_SHARE = 0.95
MIN_WINDOW_S = 60.0


def _num(raw: str) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None  # Locust writes "N/A" for an endpoint with no samples


def load_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as fh:
        return {r["Name"]: r for r in csv.DictReader(fh)}


def load_history(path: Path) -> list[dict[str, str]]:
    """Aggregated samples of Locust's ``_stats_history.csv``, oldest first."""
    with path.open(newline="") as fh:
        return [r for r in csv.DictReader(fh) if r["Name"] == "Aggregated"]


def measurement_window(history: list[dict[str, str]], users: int) -> dict | None:
    """The steady-state window: samples in which all ``users`` are running. ``None`` when
    the run never had them all running (no steady state to measure)."""
    steady = [r for r in history if (_num(r.get("User Count")) or 0) >= users]
    if not steady:
        return None
    first, last = steady[0], steady[-1]
    start, end = int(_num(first["Timestamp"]) or 0), int(_num(last["Timestamp"]) or 0)
    seconds = end - start
    requests = int(
        (_num(last["Total Request Count"]) or 0) - (_num(first["Total Request Count"]) or 0)
    )
    origin = int(_num(history[0]["Timestamp"]) or start)
    return {
        "start": start,
        "end": end,
        "seconds": seconds,
        "warm_up_s": start - origin,
        "requests": requests,
        "rps": round(requests / seconds, 3) if seconds > 0 else 0.0,
    }


def evaluate(
    rows: dict[str, dict[str, str]],
    state: dict,
    rps: float,
    history: list[dict[str, str]] | None = None,
    users: int = 0,
    min_window_s: float = MIN_WINDOW_S,
) -> dict:
    missing = [
        n for n in (*READS, *COMMANDS) if _num(rows.get(n, {}).get("Request Count")) in (None, 0.0)
    ]
    agg = rows.get("Aggregated", {})
    total = _num(agg.get("Request Count")) or 0.0
    failed = _num(agg.get("Failure Count")) or 0.0
    availability = round((total - failed) / total, 5) if total else 0.0
    cmd_p95 = [_num(rows.get(n, {}).get("95%")) for n in COMMANDS]
    corrections_p95 = max((p for p in cmd_p95 if p is not None), default=None)
    run_rps = _num(agg.get("Requests/s")) or 0.0
    window = measurement_window(history, users) if history is not None else None
    achieved = run_rps if history is None else (window["rps"] if window else 0.0)
    baseline = {
        n: {
            "requests": int(_num(rows[n]["Request Count"]) or 0),
            "p50_ms": _num(rows[n]["50%"]),
            "p95_ms": _num(rows[n]["95%"]),
            "p99_ms": _num(rows[n]["99%"]),
        }
        for n in (*READS, *COMMANDS)
        if n in rows
    }
    checks = {
        "all_endpoints": not missing,
        "availability": availability >= MIN_AVAILABILITY,
        "corrections_p95": corrections_p95 is not None and corrections_p95 <= MAX_CORRECTION_P95_MS,
        "restored_byte_identical": state.get("restored_byte_identical") is True,
        "seeded": state.get("seeded") is True,
        "achieved_rps": achieved >= MIN_RATE_SHARE * rps,
    }
    if history is not None:
        checks["measurement_window"] = window is not None and window["seconds"] >= min_window_s
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "missing": missing,
        "requests": int(total),
        "failures": int(failed),
        "availability": availability,
        "corrections_p95_ms": corrections_p95,
        "achieved_rps": achieved,
        "run_rps": run_rps,
        "window": window,
        "target_rps": rps,
        "baseline": baseline,
    }


def _window_text(v: dict) -> str:
    w = v.get("window")
    if w is None:
        return " (whole run)" if "measurement_window" not in v["checks"] else " (no window)"
    return (
        f" (warm-up {w['warm_up_s']} s excluded, window {w['seconds']} s; whole run "
        f"{v['run_rps']:.1f})"
    )


def markdown(v: dict) -> str:
    lines = [
        "### Locust baseline (ST-039; NFR-010 baseline, NFR-013 and NFR-041 gated)",
        "",
        f"Verdict: **{'pass' if v['ok'] else 'FAIL'}**; requests {v['requests']}, failures "
        f"{v['failures']}, availability {v['availability']:.4f}, achieved {v['achieved_rps']:.1f} "
        f"of {v['target_rps']:.0f} RPS{_window_text(v)}, correction p95 "
        f"{v['corrections_p95_ms']} ms.",
        "",
        "| Endpoint | Requests | p50 ms | p95 ms | p99 ms |",
        "|---|---|---|---|---|",
    ]
    for name, b in v["baseline"].items():
        lines.append(
            f"| {name} | {b['requests']} | {b['p50_ms']} | {b['p95_ms']} | {b['p99_ms']} |"
        )
    failed = [k for k, ok in v["checks"].items() if not ok]
    lines += ["", f"Failed gates: {', '.join(failed) or 'none'}. Read latency is a baseline only."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--stats", type=Path, required=True, help="Locust --csv PREFIX_stats.csv")
    p.add_argument("--state", type=Path, required=True, help="the locustfile's state JSON")
    p.add_argument("--rps", type=float, required=True)
    p.add_argument("--history", type=Path, help="Locust --csv PREFIX_stats_history.csv")
    p.add_argument("--users", type=int, default=0, help="users that make the steady state")
    p.add_argument("--min-window", type=float, default=MIN_WINDOW_S, help="seconds")
    p.add_argument("--json", type=Path)
    p.add_argument("--summary", type=Path, help="append a Markdown table (GITHUB_STEP_SUMMARY)")
    args = p.parse_args(argv)
    try:
        rows = load_rows(args.stats)
        state = json.loads(args.state.read_text())
        history = load_history(args.history) if args.history else None
    except (OSError, ValueError, KeyError) as exc:
        print(f"perf_verdict: cannot read the run: {exc}", file=sys.stderr)
        return 2
    if history is not None and args.users < 1:
        p.error("--history needs --users (the users that make the steady state)")
    v = evaluate(rows, state, args.rps, history, args.users, args.min_window)
    text = json.dumps(v, indent=2)
    print(text)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as fh:
            fh.write(markdown(v))
    return 0 if v["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
