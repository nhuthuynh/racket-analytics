"""ST-039 slice 3 (SRE): verdict on a Locust run of backend/tests/perf/locustfile_sprint02.py.

Gates now (sprint-02 §8): availability >= 99.5% (NFR-041) with every endpoint exercised, the
correction round trip p95 <= 1,500 ms (NFR-013), the sheet restored byte-identical after the
correction+undo pairs (C-04), and the achieved rate >= 95% of the target. Read latency
(NFR-010) is recorded as a baseline, not gated, until the R1 review (sprint-02 §3.1 ST-039).
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "ci" / "perf_verdict.py"
HEADER = [
    "Type", "Name", "Request Count", "Failure Count", "Median Response Time",
    "Average Response Time", "Min Response Time", "Max Response Time", "Average Content Size",
    "Requests/s", "Failures/s", "50%", "66%", "75%", "80%", "90%", "95%", "98%", "99%",
    "99.9%", "99.99%", "100%",
]  # fmt: skip
READS = ["score-sheet", "corrections", "match"]
COMMANDS = {"correct": "PATCH", "undo": "POST"}


def row(typ: str, name: str, n: int, fail: int, p95: float, p99: float, rps: float) -> list:
    pct = [p95 / 2, p95 / 2, p95 / 2, p95 / 2, p95 * 0.9, p95, p95, p99, p99, p99, p99]
    return [typ, name, n, fail, p95 / 2, p95 / 2, 1, p99, 100, rps, fail / 60, *pct]


def write_run(
    tmp: Path,
    *,
    read_fail: int = 0,
    read_p95: float = 40,
    cmd_p95: float = 200,
    rps: float = 50.0,
    missing: str | None = None,
    restored: bool | None = True,
    seeded: bool = True,
) -> tuple[Path, Path]:
    rows = []
    for name in READS:
        if name != missing:
            rows.append(row("GET", name, 1000, read_fail, read_p95, read_p95 * 2, rps / 3 - 0.4))
    for name, method in COMMANDS.items():
        if name != missing:
            rows.append(row(method, name, 60, 0, cmd_p95, cmd_p95 * 1.2, 0.5))
    total = sum(r[2] for r in rows)
    fails = sum(r[3] for r in rows)
    rows.append(row("", "Aggregated", total, fails, read_p95, read_p95 * 2, rps))
    stats = tmp / "perf_stats.csv"
    with stats.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(HEADER)
        w.writerows(rows)
    state = tmp / "perf_state.json"
    body: dict = {"seeded": seeded, "pairs": 60}
    if restored is not None:
        body["restored_byte_identical"] = restored
    state.write_text(json.dumps(body))
    return stats, state


def verdict(stats: Path, state: Path, *extra: str) -> tuple[int, dict, str]:
    out = stats.parent / "verdict.json"
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--stats", str(stats), "--state", str(state),
         "--rps", "50", "--json", str(out), *extra],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    body = json.loads(out.read_text()) if out.exists() else {}
    return res.returncode, body, res.stdout + res.stderr


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_missing_stats_file_fails_closed(tmp_path: Path) -> None:
    _, state = write_run(tmp_path)
    rc, _, out = verdict(tmp_path / "nope.csv", state)
    assert rc == 2, out


@pytest.mark.unit
@pytest.mark.parametrize("name", ["score-sheet", "corrections", "match", "correct", "undo"])
def test_an_endpoint_that_was_never_exercised_fails(tmp_path: Path, name: str) -> None:
    rc, body, _ = verdict(*write_run(tmp_path, missing=name))
    assert rc == 1
    assert name in body["missing"]


@pytest.mark.unit
def test_availability_below_99_5_percent_fails(tmp_path: Path) -> None:
    # 3 x 1000 reads + 120 commands; 6 failures per read endpoint = 18/3120 = 0.58%
    rc, body, _ = verdict(*write_run(tmp_path, read_fail=6))
    assert rc == 1
    assert body["availability"] < 0.995
    assert body["checks"]["availability"] is False


@pytest.mark.unit
def test_correction_p95_above_1500_ms_fails(tmp_path: Path) -> None:
    rc, body, _ = verdict(*write_run(tmp_path, cmd_p95=1600))
    assert rc == 1
    assert body["corrections_p95_ms"] == 1600
    assert body["checks"]["corrections_p95"] is False


@pytest.mark.unit
@pytest.mark.parametrize("restored", [False, None])
def test_sheet_not_restored_or_not_reported_fails(tmp_path: Path, restored: bool | None) -> None:
    rc, body, _ = verdict(*write_run(tmp_path, restored=restored))
    assert rc == 1
    assert body["checks"]["restored_byte_identical"] is False


@pytest.mark.unit
def test_failed_seeding_fails(tmp_path: Path) -> None:
    rc, body, _ = verdict(*write_run(tmp_path, seeded=False))
    assert rc == 1
    assert body["checks"]["seeded"] is False


@pytest.mark.unit
def test_achieved_rate_below_95_percent_fails(tmp_path: Path) -> None:
    rc, body, _ = verdict(*write_run(tmp_path, rps=40.0))
    assert rc == 1
    assert body["checks"]["achieved_rps"] is False


# ---------------------------------------------------------------- positive
@pytest.mark.unit
def test_slow_reads_are_a_baseline_not_a_gate(tmp_path: Path) -> None:
    rc, body, out = verdict(*write_run(tmp_path, read_p95=900))
    assert rc == 0, out
    assert body["baseline"]["score-sheet"]["p95_ms"] == 900
    assert "read_p95" not in body["checks"]


@pytest.mark.unit
def test_a_good_run_passes_and_writes_a_markdown_summary(tmp_path: Path) -> None:
    summary = tmp_path / "summary.md"
    rc, body, out = verdict(*write_run(tmp_path), "--summary", str(summary))
    assert rc == 0, out
    assert all(body["checks"].values())
    assert body["availability"] == 1.0
    text = summary.read_text()
    assert "| score-sheet |" in text
    assert "baseline" in text.lower()
