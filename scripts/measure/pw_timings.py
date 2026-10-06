#!/usr/bin/env python3
"""Browser timings from a Playwright JSON report (goal scorecard G02-06; NFR-011, NFR-012, NFR-014).

The Sprint 2 timing specs (`web/e2e/sprint-02/timing.spec.ts`, ST-039) attach one JSON body
`{"ms": <number>}` per measured sample, named `timing-<metric>`, for example
`timing-tag-optimistic`, `timing-tap-feedback`, `timing-seek-first-frame`,
`timing-score-sheet-interactive`. This script collects every such attachment and checks each
`--target metric=max_p95_ms` against the nearest-rank p95.

    python3 scripts/measure/pw_timings.py reports/goal/e2e-timing.json \
        --target tag-optimistic=200 --target tap-feedback=100 \
        --target seek-first-frame=1500 --target score-sheet-interactive=2000 --min-n 20

Exit 0 only when every target metric has >= --min-n samples and its p95 is within target.
A metric with no samples is "ok": false (fail closed, ADR 0014). Exit 2 on a malformed report.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from taglib import timing_summary

PREFIX = "timing-"


def _walk(node: Any):
    if isinstance(node, dict):
        if "attachments" in node and isinstance(node["attachments"], list):
            yield from node["attachments"]
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def collect(report: dict[str, Any]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for att in _walk(report):
        name = att.get("name", "") if isinstance(att, dict) else ""
        if not name.startswith(PREFIX):
            continue
        try:
            ms = float(json.loads(base64.b64decode(att["body"]))["ms"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError(f"malformed timing attachment {name}: {exc}") from exc
        out.setdefault(name[len(PREFIX) :], []).append(ms)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("report", type=Path, help="Playwright JSON report")
    p.add_argument("--target", action="append", default=[], help="metric=max_p95_ms")
    p.add_argument("--min-n", type=int, default=20)
    p.add_argument("--json", type=Path)
    args = p.parse_args(argv)
    if not args.target:
        print("pw_timings: give at least one --target", file=sys.stderr)
        return 2
    try:
        samples = collect(json.loads(args.report.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        print(f"pw_timings: {exc}", file=sys.stderr)
        return 2
    metrics = {}
    for spec in args.target:
        name, _, limit = spec.partition("=")
        metrics[name] = timing_summary(
            samples.get(name, []), max_p95_ms=float(limit), min_n=args.min_n
        )
    result = {
        "ok": all(m["ok"] for m in metrics.values()),
        "metrics": metrics,
        "unchecked": sorted(set(samples) - set(metrics)),
    }
    text = json.dumps(result, indent=2)
    print(text)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
