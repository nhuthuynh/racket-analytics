#!/usr/bin/env python3
"""Verdict on a Locust run of backend/tests/perf/locustfile_sprint02.py (ST-039, SRE slice).

    python3 scripts/ci/perf_verdict.py --stats reports/perf/perf_stats.csv \
        --state reports/perf/perf_state.json --rps 50 --json reports/perf/verdict.json \
        [--summary "$GITHUB_STEP_SUMMARY"]

Gates (sprint-02 §8): every endpoint exercised; availability (non-failed / all) >= 99.5%
(NFR-041); correction and undo p95 <= 1,500 ms (NFR-013, the larger of the two p95s); the
sheet restored byte-identical after the correction+undo pairs (C-04); the account and match
seeded; achieved rate >= 95% of --rps. Read p95/p99 (NFR-010) is a baseline: reported, not
gated, until the R1 review (sprint-02 §3.1).

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


def _num(raw: str) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None  # Locust writes "N/A" for an endpoint with no samples


def load_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as fh:
        return {r["Name"]: r for r in csv.DictReader(fh)}


def evaluate(rows: dict[str, dict[str, str]], state: dict, rps: float) -> dict:
    missing = [
        n for n in (*READS, *COMMANDS) if _num(rows.get(n, {}).get("Request Count")) in (None, 0.0)
    ]
    agg = rows.get("Aggregated", {})
    total = _num(agg.get("Request Count")) or 0.0
    failed = _num(agg.get("Failure Count")) or 0.0
    availability = round((total - failed) / total, 5) if total else 0.0
    cmd_p95 = [_num(rows.get(n, {}).get("95%")) for n in COMMANDS]
    corrections_p95 = max((p for p in cmd_p95 if p is not None), default=None)
    achieved = _num(agg.get("Requests/s")) or 0.0
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
        "achieved_rps": achieved >= 0.95 * rps,
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "missing": missing,
        "requests": int(total),
        "failures": int(failed),
        "availability": availability,
        "corrections_p95_ms": corrections_p95,
        "achieved_rps": achieved,
        "target_rps": rps,
        "baseline": baseline,
    }


def markdown(v: dict) -> str:
    lines = [
        "### Locust baseline (ST-039; NFR-010 baseline, NFR-013 and NFR-041 gated)",
        "",
        f"Verdict: **{'pass' if v['ok'] else 'FAIL'}**; requests {v['requests']}, failures "
        f"{v['failures']}, availability {v['availability']:.4f}, achieved {v['achieved_rps']:.1f} "
        f"of {v['target_rps']:.0f} RPS, correction p95 {v['corrections_p95_ms']} ms.",
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
    p.add_argument("--json", type=Path)
    p.add_argument("--summary", type=Path, help="append a Markdown table (GITHUB_STEP_SUMMARY)")
    args = p.parse_args(argv)
    try:
        rows = load_rows(args.stats)
        state = json.loads(args.state.read_text())
    except (OSError, ValueError, KeyError) as exc:
        print(f"perf_verdict: cannot read the run: {exc}", file=sys.stderr)
        return 2
    v = evaluate(rows, state, args.rps)
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
