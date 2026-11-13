#!/usr/bin/env python3
"""Eval harness (ST-176a; NFR-006.7, SPK-1.2): judge a model run against ADR 0060, row by row.

Reads a candidate run and the per-metric best accepted baseline (JSON), measures CPU-seconds per
match-minute by decoding the given clips with FFmpeg (the floor of any vision stage; no model
exists yet), and writes a report from ``docs/evals/TEMPLATE.md``: candidate, baseline, delta and
pass/fail per ADR 0060 row, gold-set version, weights hash and licence, config and cost.
Rule 1: the baseline must share the candidate's gold-set id and version and its config (else rc 2);
any one row outside its tolerance fails. Rule 2: M11 below its target fails once a
baseline has met it. Low sample neither passes nor fails (needs ML + QA agreement).
Usage: run_eval.py --candidate C.json [--baseline B.json] --clips DIR --out REPORT.md [--date D]
Exit 0 every row passes or is not judged; 1 a row fails; 2 input error (no report written).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import resource
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TEMPLATE = Path(__file__).resolve().parents[2] / "docs" / "evals" / "TEMPLATE.md"
CLIP_SUFFIXES = (".mp4", ".mov", ".mkv", ".webm")
EPS = 1e-9
SHA256 = re.compile(r"[0-9a-f]{64}")
DRY_RUN_BANNER = (
    "**DRY RUN:** the metric values are synthetic inputs that exercise the harness; "
    "no model and no gold-set footage exist (P11). Never cite them."
)


class InputError(Exception):
    pass


@dataclass(frozen=True)
class Row:
    id: str
    metric: str
    unit: str
    higher_is_better: bool
    target: float
    tolerance: float
    min_units: int
    label: str


# ADR 0060 Rule 3, one row per NFR-006 metric.
ROWS = (
    Row("M1", "Ball F1 (10 px at 1080p)", "%", True, 80.0, 1.0, 2000, "capability"),
    Row("M2", "HOTA (4 players)", "points", True, 65.0, 1.0, 3, "capability"),
    Row("M3", "Auto-calibration success", "% videos", True, 70.0, 5.0, 20, "capability"),
    Row("M4", "Reprojection error", "cm RMS", False, 15.0, 1.0, 20, "capability"),
    Row("M5", "Hit precision", "%", True, 85.0, 1.0, 500, "capability"),
    Row("M6", "Hit recall", "%", True, 85.0, 1.0, 500, "capability"),
    Row("M7", "Median hit-timing error", "ms", False, 33.0, 3.0, 500, "capability"),
    Row("M8", "p95 hit-timing error", "ms", False, 100.0, 10.0, 500, "capability"),
    Row("M9", "Bounce recall", "%", True, 70.0, 2.0, 300, "capability"),
    Row("M10", "Landing error p80", "cm", False, 60.0, 3.0, 300, "capability"),
    Row("M11", "Rally-segmentation F1 (ADR 0004)", "%", True, 90.0, 1.0, 100, "regression"),
)


@dataclass(frozen=True)
class Measure:
    value: float
    units: int


@dataclass(frozen=True)
class Result:
    row: Row
    measure: Measure | None
    baseline: float | None
    delta: float | None
    verdict: str
    target_met: bool | None


@dataclass(frozen=True)
class Cost:
    cpu_seconds: float
    durations_s: list[float]
    stage: str


def meets(row: Row, value: float, bound: float) -> bool:
    """`value` is at least as good as `bound` in the row's direction."""
    return value >= bound - EPS if row.higher_is_better else value <= bound + EPS


def judge(row: Row, measure: Measure | None, baseline: float | None) -> Result:
    if measure is None:
        return Result(row, None, baseline, None, "not measured", None)
    target_met = meets(row, measure.value, row.target)
    delta = None if baseline is None else round(measure.value - baseline, 6)
    if measure.units < row.min_units:
        verdict = "low sample"
    elif baseline is None:
        verdict = "n/a: no baseline"
    else:
        slack = -row.tolerance if row.higher_is_better else row.tolerance
        verdict = "pass" if meets(row, measure.value, baseline + slack) else "fail"
        gated = row.label == "regression" and meets(row, baseline, row.target)
        if gated and not target_met:
            verdict = "fail"
    return Result(row, measure, baseline, delta, verdict, target_met)


def gold_set(run: dict[str, Any], name: str) -> tuple[str, int]:
    """The (id, version) of a run's gold set; missing or malformed fails closed (Rule 1)."""
    gold = run.get("gold_set")
    gid = gold.get("id") if isinstance(gold, dict) else None
    version = gold.get("version") if isinstance(gold, dict) else None
    bad_version = isinstance(version, bool) or not isinstance(version, int)
    if not isinstance(gid, str) or not gid or bad_version:
        raise InputError(f"{name} gold_set must be {{id, version}}, got {gold!r}")
    return gid, version


def config(run: dict[str, Any], name: str) -> dict[str, Any]:
    """A run's config; Rule 1 needs one on both sides to compare like with like."""
    value = run.get("config")
    if not isinstance(value, dict):
        raise InputError(f"{name} config must be an object, got {value!r}")
    return value


def evaluate(candidate: dict[str, Any], baseline: dict[str, Any] | None) -> list[Result]:
    known = {r.id for r in ROWS}
    unknown = sorted(set(candidate.get("metrics", {})) - known)
    if unknown:
        raise InputError(f"unknown metric id(s) {', '.join(unknown)}; ADR 0060 has M1-M11")
    cand_gold = gold_set(candidate, "candidate")
    if baseline is not None:
        if gold_set(baseline, "baseline") != cand_gold:
            raise InputError(
                f"gold-set version differs: candidate {candidate['gold_set']}, baseline "
                f"{baseline['gold_set']}; ADR 0060 Rule 1 never compares across versions"
            )
        if config(baseline, "baseline") != config(candidate, "candidate"):
            raise InputError(
                f"config differs: candidate {candidate['config']}, baseline "
                f"{baseline['config']}; ADR 0060 Rule 1 compares only runs with the same config"
            )
    best = (baseline or {}).get("metrics", {})
    results = []
    for row in ROWS:
        raw = candidate.get("metrics", {}).get(row.id)
        measure = None if raw is None else Measure(float(raw["value"]), int(raw["units"]))
        base = best.get(row.id)
        results.append(judge(row, measure, None if base is None else float(base["value"])))
    return results


def exit_code(results: list[Result]) -> int:
    return 1 if any(r.verdict == "fail" for r in results) else 0


def per_match_minute(cpu_seconds: float, durations_s: list[float]) -> float:
    minutes = sum(durations_s) / 60.0
    if minutes <= 0:
        raise InputError("no footage: CPU-seconds per match-minute needs at least one clip")
    return cpu_seconds / minutes


def _num(value: float | None, signed: bool = False) -> str:
    if value is None:
        return "—"
    return f"{value:+.2f}" if signed else f"{value:.2f}"


def _table(rows: list[list[str]]) -> str:
    return "\n".join("| " + " | ".join(cells) + " |" for cells in rows)


def _row_cells(r: Result) -> list[str]:
    better = "higher" if r.row.higher_is_better else "lower"
    sign = "≥" if r.row.higher_is_better else "≤"
    met = {None: "—", True: "yes", False: "no"}[r.target_met]
    return [
        r.row.id,
        r.row.metric,
        f"{r.row.unit}, {better} is better",
        f"{sign} {r.row.target:g}",
        f"{r.row.tolerance:g}",
        str(r.row.min_units),
        r.row.label,
        _num(r.measure.value if r.measure else None),
        str(r.measure.units) if r.measure else "—",
        _num(r.baseline),
        _num(r.delta, signed=True),
        r.verdict,
        met,
    ]


def _ids(results: list[Result], verdict: str) -> str:
    return ", ".join(r.row.id for r in results if r.verdict == verdict) or "none"


def render(
    template: str,
    candidate: dict[str, Any],
    results: list[Result],
    cost: Cost,
    weights_sha256: str | None,
    date: str,
    baseline: dict[str, Any] | None = None,
) -> str:
    gold = candidate.get("gold_set", {})
    weights = candidate.get("weights") or {}
    cand_config = json.dumps(candidate.get("config", {}), sort_keys=True)
    base_config = (
        "— (no baseline)"
        if baseline is None
        else f"`{json.dumps(baseline.get('config', {}), sort_keys=True)}`"
    )
    sha_cell = "none (no weights)"
    if weights_sha256:
        sha_cell = f"`{weights_sha256}`"
        if not weights.get("path"):
            sha_cell += " (declared; no file to verify)"
    dry = bool(candidate.get("dry_run"))
    rc = exit_code(results)
    rate = per_match_minute(cost.cpu_seconds, cost.durations_s)
    fields = {
        "title": f"Eval report {date}: {candidate.get('pipeline_version', 'unnamed')}"
        + (" (DRY RUN)" if dry else ""),
        "dry_run": DRY_RUN_BANNER if dry else "",
        "provenance": _table(
            [
                ["Candidate pipeline_version", str(candidate.get("pipeline_version", "—"))],
                ["Gold set", f"{gold.get('id', '—')} v{gold.get('version', '—')}"],
                ["Weights sha256", sha_cell],
                ["Weights licence", str(weights.get("licence", "—"))],
                ["Config", f"`{cand_config}`"],
                ["Baseline config", base_config],
            ]
        ),
        "cost": _table(
            [
                ["Stage measured", cost.stage],
                ["Clips decoded", str(len(cost.durations_s))],
                ["Match-minutes", f"{sum(cost.durations_s) / 60.0:.3f}"],
                ["CPU-seconds", f"{cost.cpu_seconds:.3f}"],
                ["CPU-seconds per match-minute", f"{rate:.3f}"],
            ]
        ),
        "rows": _table([_row_cells(r) for r in results]),
        "verdict": f"**rc {rc}: {'FAIL' if rc else 'PASS'}.** Failing rows: "
        f"{_ids(results, 'fail')}. Low sample (needs ML + QA agreement): "
        f"{_ids(results, 'low sample')}.",
    }
    for key, value in fields.items():
        template = template.replace("{{" + key + "}}", value)
    if "{{" in template:
        raise InputError("template has a field the harness does not fill")
    return template


def _probe_duration(clip: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip)],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(out.stdout.strip())


def measure_decode(clips_dir: Path) -> Cost:
    clips = sorted(p for p in clips_dir.iterdir() if p.suffix.lower() in CLIP_SUFFIXES)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    for clip in clips:
        decode = ["ffmpeg", "-nostdin", "-v", "error", "-i", str(clip), "-f", "null", "-"]
        subprocess.run(decode, check=True)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    return Cost(cpu, [_probe_duration(c) for c in clips], "FFmpeg decode of every clip (no model)")


def weights_hash(weights: dict[str, Any]) -> str | None:
    """sha256 of the weights file; with no file, the declared sha256 (reported as unverified)."""
    declared = weights.get("sha256")
    if declared is not None and not SHA256.fullmatch(str(declared)):
        raise InputError(f"weights sha256 must be 64 lowercase hex characters, got {declared!r}")
    if not weights.get("path"):
        return declared
    digest = hashlib.sha256(Path(weights["path"]).read_bytes()).hexdigest()
    if declared and declared != digest:
        raise InputError(f"weights sha256 declared {weights['sha256']}, file has {digest}")
    return digest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--baseline", type=Path)
    p.add_argument("--clips", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--date", required=True)
    args = p.parse_args(argv)
    try:
        candidate = json.loads(args.candidate.read_text())
        baseline = json.loads(args.baseline.read_text()) if args.baseline else None
        results = evaluate(candidate, baseline)
        sha = weights_hash(candidate.get("weights") or {})
        cost = measure_decode(args.clips)
        report = render(
            TEMPLATE.read_text(), candidate, results, cost, sha, args.date, baseline=baseline
        )
    except (InputError, OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"eval: input error: {exc}", file=sys.stderr)
        return 2
    args.out.write_text(report)
    rc = exit_code(results)
    print(f"eval: rc {rc}; report {args.out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
