#!/usr/bin/env python3
"""Verdict on a Locust run of backend/tests/perf/locustfile_sprint0{2,4}.py (ST-039, ST-054).

    python3 scripts/ci/perf_verdict.py --stats reports/perf/perf_stats.csv \
        --state reports/perf/perf_state.json --rps 50 --json reports/perf/verdict.json \
        [--history reports/perf/perf_stats_history.csv --users 51] \
        [--dashboard-reads stats,evidence] [--summary "$GITHUB_STEP_SUMMARY"]

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

Dashboard reads (C4-LOCUST, ST-054; NFR-010 "dashboard", NFR-041): each Locust name given
with --dashboard-reads (the job passes ``stats,evidence``: GET stats and GET evidence of the
seeded tagged match) must be exercised and, on its own route, have p95 <= 300 ms, p99 <=
800 ms and availability >= 99.5% (gates ``dashboard_p95``, ``dashboard_p99``,
``dashboard_availability``; ``dashboard_failed`` names the routes). A route with no samples
or an "N/A" percentile fails closed. Without the flag the verdict is the Sprint 2 one.

R1 reads per endpoint (ST-074; NFR-010.1-.9; G05-01), ``locustfile_r1.py``:

    python3 scripts/ci/perf_verdict.py --stats reports/perf/r1-1_stats.csv --rps 50 \
        --min-rps 49.5 --warmup-s 60 --p95-ms 300 --p99-ms 800 --max-error-pct 0.5 \
        --per-endpoint match,score-sheet,dashboard,plan --json reports/perf/r1-1.json

With --per-endpoint no --state is read and the Sprint 2 gates are not applied. Each group is
the Locust name itself or every ``<group>:<route>`` name; its p95/p99 is its slowest route and
must be within --p95-ms/--p99-ms, and its non-2xx share within --max-error-pct, as must the
whole run's. A group with no samples or an "N/A" percentile fails closed. With --warmup-s the
history file (--history, else ``<prefix>_stats_history.csv``) must show the locustfile's reset
of the statistics (the Aggregated total drops) at least that many seconds after the first
sample, so the stats file holds the measured window only; the window from the reset to the
last sample must last --min-window seconds and its rate is gated at --min-rps (default 95% of
--rps). Without --warmup-s the rate is the stats file's Aggregated Requests/s. Every failed
endpoint is named on stderr ("FAIL <group>: ...").

Exit 0 all gates met; 1 a gate failed; 2 the stats or state file is missing or unreadable.
Standard library only.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Callable
from pathlib import Path

READS = ("score-sheet", "corrections", "match")
COMMANDS = ("correct", "undo")
MIN_AVAILABILITY = 0.995
MAX_CORRECTION_P95_MS = 1500.0
MIN_RATE_SHARE = 0.95
MIN_WINDOW_S = 60.0
DASHBOARD_P95_MS = 300.0  # NFR-010 "dashboard"
DASHBOARD_P99_MS = 800.0  # NFR-010 "dashboard"


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


def _at(sample: dict[str, str], column: str) -> float:
    """A numeric history cell; missing or "N/A" counts as 0."""
    return _num(sample.get(column, "")) or 0.0


def measurement_window(history: list[dict[str, str]], users: int) -> dict | None:
    """The steady-state window: samples in which all ``users`` are running. ``None`` when
    the run never had them all running (no steady state to measure). Everything before the
    window is the warm-up (seeding and spawn)."""
    steady = [r for r in history if _at(r, "User Count") >= users]
    if not steady:
        return None
    first, last = steady[0], steady[-1]
    start, end = int(_at(first, "Timestamp")), int(_at(last, "Timestamp"))
    seconds = end - start
    requests = int(_at(last, "Total Request Count") - _at(first, "Total Request Count"))
    return {
        "start": start,
        "end": end,
        "seconds": seconds,
        "warm_up_s": start - int(_at(history[0], "Timestamp")),
        "requests": requests,
        "rps": round(requests / seconds, 3) if seconds > 0 else 0.0,
    }


def dashboard_reads(rows: dict[str, dict[str, str]], names: tuple[str, ...]) -> dict[str, dict]:
    """Per-route figures of the dashboard reads; a route Locust never sampled has 0 requests
    and no percentiles."""
    reads = {}
    for name in names:
        row = rows.get(name, {})
        n = _num(row.get("Request Count")) or 0.0
        failed = _num(row.get("Failure Count")) or 0.0
        reads[name] = {
            "requests": int(n),
            "failures": int(failed),
            "availability": round((n - failed) / n, 5) if n else 0.0,
            "p95_ms": _num(row.get("95%")),
            "p99_ms": _num(row.get("99%")),
        }
    return reads


def _route_failures(read: dict) -> list[str]:
    """The dashboard gates this one route fails (fail closed on missing figures)."""
    p95, p99 = read["p95_ms"], read["p99_ms"]
    failed = []
    if not read["requests"] or p95 is None or p95 > DASHBOARD_P95_MS:
        failed.append("dashboard_p95")
    if not read["requests"] or p99 is None or p99 > DASHBOARD_P99_MS:
        failed.append("dashboard_p99")
    if read["availability"] < MIN_AVAILABILITY:
        failed.append("dashboard_availability")
    return failed


DASHBOARD_GATES = ("dashboard_p95", "dashboard_p99", "dashboard_availability")


def dashboard_failed(reads: dict[str, dict]) -> dict[str, list[str]]:
    """For each dashboard gate, the routes that fail it (empty list: the gate passes)."""
    by_gate: dict[str, list[str]] = {g: [] for g in DASHBOARD_GATES}
    for name, read in reads.items():
        for gate in _route_failures(read):
            by_gate[gate].append(name)
    return by_gate


def dashboard_checks(reads: dict[str, dict]) -> dict[str, bool]:
    """The dashboard gates; none when no dashboard read is gated."""
    if not reads:
        return {}
    return {gate: not names for gate, names in dashboard_failed(reads).items()}


def evaluate(
    rows: dict[str, dict[str, str]],
    state: dict,
    rps: float,
    history: list[dict[str, str]] | None = None,
    users: int = 0,
    min_window_s: float = MIN_WINDOW_S,
    dashboard: tuple[str, ...] = (),
) -> dict:
    endpoints = (*READS, *(d for d in dashboard if d not in READS), *COMMANDS)
    missing = [n for n in endpoints if _num(rows.get(n, {}).get("Request Count")) in (None, 0.0)]
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
        for n in endpoints
        if n in rows
    }
    reads = dashboard_reads(rows, dashboard)
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
    checks.update(dashboard_checks(reads))
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
        "dashboard": reads,
        "dashboard_failed": dashboard_failed(reads) if reads else {},
    }


def group_routes(rows: dict[str, dict[str, str]], group: str) -> list[str]:
    """The Locust names of one R1 group: the name itself, or every ``<group>:<route>``."""
    return [n for n in rows if n == group or n.startswith(f"{group}:")]


def reset_window(history: list[dict[str, str]]) -> dict | None:
    """The measured window after the locustfile's statistics reset (the first drop of the
    Aggregated total), to the last sample; ``None`` when the statistics were never reset."""
    totals = [_at(r, "Total Request Count") for r in history]
    at = next((i for i in range(1, len(totals)) if totals[i] < totals[i - 1]), None)
    if at is None:
        return None
    first, reset, last = history[0], history[at], history[-1]
    start, end = int(_at(reset, "Timestamp")), int(_at(last, "Timestamp"))
    requests = int(totals[-1] - totals[at])
    seconds = end - start
    return {
        "start": start,
        "end": end,
        "seconds": seconds,
        "warm_up_s": start - int(_at(first, "Timestamp")),
        "requests": requests,
        "rps": round(requests / seconds, 3) if seconds > 0 else 0.0,
    }


def _endpoint(rows: dict[str, dict[str, str]], group: str, t: dict) -> dict:
    routes = group_routes(rows, group)
    n = sum(_num(rows[r].get("Request Count")) or 0.0 for r in routes)
    failed = sum(_num(rows[r].get("Failure Count")) or 0.0 for r in routes)
    p95s = [_num(rows[r].get("95%")) for r in routes]
    p99s = [_num(rows[r].get("99%")) for r in routes]
    p95 = None if not routes or None in p95s else max(p95s)  # type: ignore[type-var]
    p99 = None if not routes or None in p99s else max(p99s)  # type: ignore[type-var]
    error_pct = round(failed / n * 100, 3) if n else None
    if not n:
        reasons = ["no samples"]
    else:
        reasons = [
            *(["p95"] if p95 is None or p95 > t["p95_ms"] else []),
            *(["p99"] if p99 is None or p99 > t["p99_ms"] else []),
            *(["errors"] if error_pct is None or error_pct > t["max_error_pct"] else []),
        ]
    return {
        "routes": routes,
        "requests": int(n),
        "failures": int(failed),
        "error_pct": error_pct,
        "p95_ms": p95,
        "p99_ms": p99,
        "ok": not reasons,
        "failed": reasons,
    }


def evaluate_endpoints(
    rows: dict[str, dict[str, str]],
    groups: tuple[str, ...],
    thresholds: dict,
    history: list[dict[str, str]] | None,
    min_window_s: float = MIN_WINDOW_S,
) -> dict:
    """The R1 per-endpoint verdict (ST-074; NFR-010.1-.9)."""
    endpoints = {g: _endpoint(rows, g, thresholds) for g in groups}
    agg = rows.get("Aggregated", {})
    total = _num(agg.get("Request Count")) or 0.0
    failed = _num(agg.get("Failure Count")) or 0.0
    error_pct = round(failed / total * 100, 3) if total else None
    window = reset_window(history) if history is not None else None
    if history is None:
        achieved = _num(agg.get("Requests/s")) or 0.0
    else:
        achieved = window["rps"] if window else 0.0
    checks = {
        "all_endpoints": all(e["requests"] for e in endpoints.values()),
        "endpoints": all(e["ok"] for e in endpoints.values()),
        "error_pct": error_pct is not None and error_pct <= thresholds["max_error_pct"],
        "achieved_rps": achieved >= thresholds["min_rps"],
    }
    if history is not None:
        checks["warmup_excluded"] = (
            window is not None and window["warm_up_s"] >= thresholds["warmup_s"]
        )
        checks["measurement_window"] = window is not None and window["seconds"] >= min_window_s
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "missing": [g for g, e in endpoints.items() if not e["requests"]],
        "endpoints": endpoints,
        "failed_endpoints": {g: e["failed"] for g, e in endpoints.items() if not e["ok"]},
        "requests": int(total),
        "failures": int(failed),
        "error_pct": error_pct,
        "achieved_rps": achieved,
        "window": window,
        "thresholds": thresholds,
    }


def endpoint_failures(v: dict) -> list[str]:
    """One stderr line per failed endpoint and per failed run-wide check."""
    t, lines = v["thresholds"], []
    for group, e in v["endpoints"].items():
        why = {
            "no samples": "no samples",
            "p95": f"p95 {e['p95_ms']} ms > {t['p95_ms']:g} ms",
            "p99": f"p99 {e['p99_ms']} ms > {t['p99_ms']:g} ms",
            "errors": f"errors {e['error_pct']} % > {t['max_error_pct']:g} %",
        }
        if e["failed"]:
            detail = "; ".join(why[r] for r in e["failed"])
            lines.append(f"perf_verdict: FAIL {group}: {detail} (routes {', '.join(e['routes'])})")
    for check, ok in v["checks"].items():
        if not ok and check not in ("endpoints", "all_endpoints"):
            lines.append(f"perf_verdict: FAIL run: {check}")
    return lines


def endpoints_markdown(v: dict) -> str:
    t = v["thresholds"]
    lines = [
        f"### R1 reads per endpoint (ST-074; NFR-010: p95 <= {t['p95_ms']:g} ms, p99 <= "
        f"{t['p99_ms']:g} ms, errors <= {t['max_error_pct']:g} %)",
        "",
        f"Verdict: **{'pass' if v['ok'] else 'FAIL'}**; requests {v['requests']}, errors "
        f"{v['error_pct']} %, achieved {v['achieved_rps']} RPS (min {t['min_rps']:g})"
        f"{_window_text(v) if v['window'] else ''}.",
        "",
        "| Endpoint | Requests | Errors % | p95 ms | p99 ms | Gate |",
        "|---|---|---|---|---|---|",
    ]
    for group, e in v["endpoints"].items():
        gate = "pass" if e["ok"] else "FAIL " + ", ".join(e["failed"])
        err = "n/a" if e["error_pct"] is None else f"{e['error_pct']:.3f}"
        lines.append(
            f"| {group} | {e['requests']} | {err} | {e['p95_ms']} | {e['p99_ms']} | {gate} |"
        )
    failed = [k for k, ok in v["checks"].items() if not ok]
    lines += ["", f"Failed checks: {', '.join(failed) or 'none'}."]
    return "\n".join(lines) + "\n"


def _window_text(v: dict) -> str:
    w = v.get("window")
    if w is None:
        return " (whole run)" if "measurement_window" not in v["checks"] else " (no window)"
    whole = f"; whole run {v['run_rps']:.1f}" if "run_rps" in v else ""
    return f" (warm-up {w['warm_up_s']} s excluded, window {w['seconds']} s{whole})"


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
    reads = v.get("dashboard") or {}
    rest = "Other read latency is a baseline only." if reads else "Read latency is a baseline only."
    lines += ["", f"Failed gates: {', '.join(failed) or 'none'}. {rest}"]
    if reads:
        lines += [
            "",
            f"#### Dashboard reads (NFR-010: p95 <= {DASHBOARD_P95_MS:.0f} ms, p99 <= "
            f"{DASHBOARD_P99_MS:.0f} ms; NFR-041: availability >= {MIN_AVAILABILITY:.1%}, "
            "per route)",
            "",
            "| Route | Requests | Failures | Availability | p95 ms | p99 ms | Gate |",
            "|---|---|---|---|---|---|---|",
        ]
        for name, r in reads.items():
            gate = "FAIL" if _route_failures(r) else "pass"
            lines.append(
                f"| {name} | {r['requests']} | {r['failures']} | {r['availability']:.4f} | "
                f"{r['p95_ms']} | {r['p99_ms']} | {gate} |"
            )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--stats", type=Path, required=True, help="Locust --csv PREFIX_stats.csv")
    p.add_argument(
        "--state", type=Path, help="the locustfile's state JSON (not with --per-endpoint)"
    )
    p.add_argument("--rps", type=float, required=True)
    p.add_argument("--history", type=Path, help="Locust --csv PREFIX_stats_history.csv")
    p.add_argument("--users", type=int, default=0, help="users that make the steady state")
    p.add_argument("--min-window", type=float, default=MIN_WINDOW_S, help="seconds")
    p.add_argument(
        "--dashboard-reads",
        default="",
        help="comma-separated Locust names gated as dashboard reads (NFR-010), e.g. stats,evidence",
    )
    p.add_argument(
        "--per-endpoint",
        default="",
        help="comma-separated R1 groups gated each on its own (ST-074), e.g. match,plan",
    )
    p.add_argument("--min-rps", type=float, help="R1 rate gate (default 95%% of --rps)")
    p.add_argument("--warmup-s", type=float, default=0.0, help="R1 warm-up excluded, seconds")
    p.add_argument("--p95-ms", type=float, default=DASHBOARD_P95_MS, help="R1 p95 target")
    p.add_argument("--p99-ms", type=float, default=DASHBOARD_P99_MS, help="R1 p99 target")
    p.add_argument("--max-error-pct", type=float, default=0.5, help="R1 non-2xx share, %%")
    p.add_argument("--json", type=Path)
    p.add_argument("--summary", type=Path, help="append a Markdown table (GITHUB_STEP_SUMMARY)")
    args = p.parse_args(argv)
    groups = tuple(n.strip() for n in args.per_endpoint.split(",") if n.strip())
    if groups:
        return _main_endpoints(args, groups)
    if args.state is None:
        p.error("the following arguments are required: --state")
    try:
        rows = load_rows(args.stats)
        state = json.loads(args.state.read_text())
        history = load_history(args.history) if args.history else None
    except (OSError, ValueError, KeyError) as exc:
        print(f"perf_verdict: cannot read the run: {exc}", file=sys.stderr)
        return 2
    if history is not None and args.users < 1:
        p.error("--history needs --users (the users that make the steady state)")
    dashboard = tuple(n.strip() for n in args.dashboard_reads.split(",") if n.strip())
    v = evaluate(rows, state, args.rps, history, args.users, args.min_window, dashboard)
    _emit(v, args, markdown)
    return 0 if v["ok"] else 1


def _main_endpoints(args: argparse.Namespace, groups: tuple[str, ...]) -> int:
    history_path = args.history
    if history_path is None and args.warmup_s > 0:
        history_path = args.stats.with_name(
            args.stats.name.replace("_stats.csv", "_stats_history.csv")
        )
    try:
        rows = load_rows(args.stats)
        history = load_history(history_path) if history_path else None
    except (OSError, ValueError, KeyError) as exc:
        print(f"perf_verdict: cannot read the run: {exc}", file=sys.stderr)
        return 2
    thresholds = {
        "p95_ms": args.p95_ms,
        "p99_ms": args.p99_ms,
        "max_error_pct": args.max_error_pct,
        "min_rps": args.min_rps if args.min_rps is not None else MIN_RATE_SHARE * args.rps,
        "warmup_s": args.warmup_s,
    }
    v = evaluate_endpoints(rows, groups, thresholds, history, args.min_window)
    _emit(v, args, endpoints_markdown)
    for line in endpoint_failures(v):
        print(line, file=sys.stderr)
    return 0 if v["ok"] else 1


def _emit(v: dict, args: argparse.Namespace, md: Callable[[dict], str]) -> None:
    text = json.dumps(v, indent=2)
    print(text)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as fh:
            fh.write(md(v))


if __name__ == "__main__":
    sys.exit(main())
