"""ST-176a (NFR-006.7, SPK-1.2): ``scripts/eval/run_eval.py`` across its real boundaries: the
filesystem (input JSON, weights file, report), FFmpeg/ffprobe on the committed phone-profile clips
(the CPU-seconds figure) and the committed report under ``docs/evals/``.

Fail closed, negative cases first: a declared weights hash that does not match the file is rc 2;
then the measured CPU figure covers every clip; the committed dry-run report matches a fresh run
row for row (only the CPU line is machine-dependent).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.paths import REPO

pytestmark = pytest.mark.integration

SCRIPT = REPO / "scripts" / "eval" / "run_eval.py"
INPUTS = REPO / "fixtures" / "evals" / "dry-run-v1"
CLIPS = REPO / "fixtures" / "clips" / "phone-profiles-v1"
COMMITTED = REPO / "docs" / "evals" / "2026-11-13-dry-run-phone-profiles-v1.md"


def run(tmp: Path, candidate: Path, **extra: str) -> tuple[int, str, str]:
    out = tmp / "report.md"
    argv = [sys.executable, str(SCRIPT), "--candidate", str(candidate),
            "--baseline", str(INPUTS / "baseline.json"), "--clips", str(CLIPS),
            "--out", str(out), "--date", "2026-11-13"]  # fmt: skip
    for key, value in extra.items():
        argv += [f"--{key.replace('_', '-')}", value]
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    return proc.returncode, proc.stdout + proc.stderr, out.read_text() if out.exists() else ""


def with_weights(tmp: Path, declared: str | None) -> Path:
    weights = tmp / "model.onnx"
    weights.write_bytes(b"not a real model, only bytes to hash")
    candidate = json.loads((INPUTS / "candidate.json").read_text())
    candidate["weights"] = {"path": str(weights), "sha256": declared, "licence": "Apache-2.0"}
    path = tmp / "candidate.json"
    path.write_text(json.dumps(candidate))
    return path


def test_a_declared_weights_hash_that_does_not_match_the_file_is_refused(tmp_path: Path) -> None:
    rc, out, report = run(tmp_path, with_weights(tmp_path, "0" * 64))

    assert rc == 2, out
    assert "sha256" in out
    assert report == ""


def test_the_weights_hash_is_computed_from_the_file(tmp_path: Path) -> None:
    rc, out, report = run(tmp_path, with_weights(tmp_path, None))
    digest = hashlib.sha256(b"not a real model, only bytes to hash").hexdigest()

    assert rc == 0, out
    assert f"| Weights sha256 | `{digest}` |" in report
    assert "| Weights licence | Apache-2.0 |" in report


def test_cpu_seconds_cover_every_phone_profile_clip(tmp_path: Path) -> None:
    rc, out, report = run(tmp_path, INPUTS / "candidate.json")

    assert rc == 0, out
    assert "| Clips decoded | 6 |" in report
    assert "| Match-minutes | 0.200 |" in report


def _rows(report: str) -> list[str]:
    return [line for line in report.splitlines() if line.startswith("| M")]


def test_the_committed_dry_run_report_matches_a_fresh_run(tmp_path: Path) -> None:
    rc, out, report = run(tmp_path, INPUTS / "candidate.json")

    assert rc == 0, out
    assert COMMITTED.exists(), COMMITTED
    assert len(_rows(report)) == 11
    assert _rows(COMMITTED.read_text()) == _rows(report)
