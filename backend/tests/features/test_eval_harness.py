"""Bindings for tests/features/eval_harness.feature (ST-176a; NFR-006.7, SPK-1.2; ADR 0060).

Runs ``scripts/eval/run_eval.py`` in a subprocess exactly as a reviewer would, on the committed
phone-profile clips (real FFmpeg decode for the CPU-seconds figure) and the synthetic inputs in
``fixtures/evals/dry-run-v1``. Written red first: the script does not exist yet.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support.paths import REPO

scenarios("eval_harness.feature")

SCRIPT = REPO / "scripts" / "eval" / "run_eval.py"
INPUTS = REPO / "fixtures" / "evals" / "dry-run-v1"
CLIPS = REPO / "fixtures" / "clips" / "phone-profiles-v1"
ROWS = [f"M{i}" for i in range(1, 12)]


@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    return {"tmp": tmp_path, "out": tmp_path / "report.md"}


def _row(report: str, metric: str) -> list[str]:
    for line in report.splitlines():
        if line.startswith(f"| {metric} |"):
            return [c.strip() for c in line.strip().strip("|").split("|")]
    raise AssertionError(f"no row {metric} in the report")


@given(parsers.parse('the dry-run candidate and baseline for gold set "{gid}" version {v:d}'))
def dry_run(ctx: dict[str, Any], gid: str, v: int) -> None:
    ctx["candidate"] = INPUTS / "candidate.json"
    ctx["baseline"] = INPUTS / "baseline.json"
    assert json.loads(ctx["baseline"].read_text())["gold_set"] == {"id": gid, "version": v}


@given("the planted-regression candidate and the dry-run baseline")
def planted(ctx: dict[str, Any]) -> None:
    ctx["candidate"] = INPUTS / "planted-regression.json"
    ctx["baseline"] = INPUTS / "baseline.json"


@given(parsers.parse('the dry-run candidate and a baseline for gold set "{gid}" version {v:d}'))
def other_version(ctx: dict[str, Any], gid: str, v: int) -> None:
    baseline = json.loads((INPUTS / "baseline.json").read_text())
    baseline["gold_set"] = {"id": gid, "version": v}
    ctx["baseline"] = ctx["tmp"] / "baseline-v2.json"
    ctx["baseline"].write_text(json.dumps(baseline))
    ctx["candidate"] = INPUTS / "candidate.json"


@given("the phone-profile fixture clips")
def clips(ctx: dict[str, Any]) -> None:
    ctx["clips"] = CLIPS


@when("the eval harness runs")
def runs(ctx: dict[str, Any]) -> None:
    argv = [sys.executable, str(SCRIPT), "--candidate", str(ctx["candidate"]),
            "--baseline", str(ctx["baseline"]), "--clips", str(ctx["clips"]),
            "--out", str(ctx["out"]), "--date", "2026-11-13"]  # fmt: skip
    ctx["proc"] = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    ctx["report"] = ctx["out"].read_text() if ctx["out"].exists() else None


@then(parsers.parse("it exits with code {rc:d}"))
def exits(ctx: dict[str, Any], rc: int) -> None:
    proc = ctx["proc"]
    assert proc.returncode == rc, proc.stdout + proc.stderr


@then("the report has a row for each of M1 to M11 with candidate, baseline, delta and verdict")
def all_rows(ctx: dict[str, Any]) -> None:
    for metric in ROWS:
        cells = _row(ctx["report"], metric)
        assert cells[-2] == "pass", (metric, cells)
        assert re.fullmatch(r"[+−-]?\d+(\.\d+)?", cells[-3]), (metric, cells)  # delta


@then("the report names the gold-set version, the weights hash and licence, and the config")
def provenance(ctx: dict[str, Any]) -> None:
    report = ctx["report"]
    assert "dry-run-synthetic v1" in report
    assert "Weights sha256" in report and "Weights licence" in report
    assert '"ball_px_threshold": 10' in report


@then("the report gives a CPU-seconds per match-minute value above zero")
def cpu(ctx: dict[str, Any]) -> None:
    found = re.search(r"CPU-seconds per match-minute \| ([\d.]+)", ctx["report"])
    assert found and float(found.group(1)) > 0, ctx["report"]


@then(parsers.parse('the report marks M1 and M7 as "fail" and every other measured row as "pass"'))
def planted_rows(ctx: dict[str, Any]) -> None:
    verdicts = {m: _row(ctx["report"], m)[-2] for m in ROWS}
    assert verdicts == {m: ("fail" if m in {"M1", "M7"} else "pass") for m in ROWS}


@then("no report is written")
def no_report(ctx: dict[str, Any]) -> None:
    assert ctx["report"] is None
    assert "gold-set version" in ctx["proc"].stdout + ctx["proc"].stderr
