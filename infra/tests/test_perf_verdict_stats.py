"""C4-LOCUST integration (ST-054 SRE half; NFR-010 "dashboard", NFR-041): ``perf_verdict.py``
gates the dashboard reads, GET stats and GET evidence, on Locust stats CSVs.

Each fixture in ``fixtures/perf/`` is a Locust 2.46.7 ``--csv`` stats file of the
``perf-baseline`` shape (50 readers in rotation over score-sheet, corrections, match, stats
and evidence, 1 correction user). The script runs as the job runs it, with
``--dashboard-reads stats,evidence``: every dashboard read must have p95 <= 300 ms,
p99 <= 800 ms and availability >= 99.5% on its own route, or the run fails (rc 1).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT

pytestmark = pytest.mark.integration

SCRIPT = REPO_ROOT / "scripts" / "ci" / "perf_verdict.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "perf"
DASHBOARD = ("--dashboard-reads", "stats,evidence")


def verdict(tmp: Path, fixture: str, *extra: str) -> tuple[int, dict, str]:
    out = tmp / "verdict.json"
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--stats", str(FIXTURES / fixture),
         "--state", str(FIXTURES / "perf_state_ok.json"), "--rps", "50", "--json", str(out),
         *extra],
        capture_output=True, text=True, check=False, timeout=60,
    )  # fmt: skip
    body = json.loads(out.read_text()) if out.exists() else {}
    return res.returncode, body, res.stdout + res.stderr


# ---------------------------------------------------------------- negative cases first
@pytest.mark.parametrize(
    ("fixture", "gate", "route"),
    [
        ("stats_reads_p95_over_stats.csv", "dashboard_p95", "stats"),
        ("stats_reads_p99_over_stats.csv", "dashboard_p99", "evidence"),
        ("stats_reads_availability_under_stats.csv", "dashboard_availability", "evidence"),
    ],
)
def test_a_dashboard_read_over_its_threshold_fails_the_run(
    tmp_path: Path, fixture: str, gate: str, route: str
) -> None:
    rc, body, out = verdict(tmp_path, fixture, *DASHBOARD)
    assert rc == 1, out
    assert body["checks"][gate] is False
    assert route in body["dashboard_failed"][gate]
    # the whole-run gates alone would have passed this run: the route gate is what fails it
    assert body["checks"]["availability"] is True
    assert body["checks"]["achieved_rps"] is True


def test_a_dashboard_read_that_was_never_exercised_fails(tmp_path: Path) -> None:
    rc, body, out = verdict(tmp_path, "stats_reads_evidence_missing_stats.csv", *DASHBOARD)
    assert rc == 1, out
    assert "evidence" in body["missing"]
    assert body["checks"]["all_endpoints"] is False
    assert body["checks"]["dashboard_p95"] is False


def test_the_summary_names_the_failed_dashboard_route(tmp_path: Path) -> None:
    summary = tmp_path / "summary.md"
    rc, _, out = verdict(
        tmp_path, "stats_reads_p95_over_stats.csv", *DASHBOARD, "--summary", str(summary)
    )
    assert rc == 1, out
    text = summary.read_text()
    assert "Dashboard reads" in text
    assert "| stats | 600 | 0 | 1.0000 | 310.0 | 520.0 | FAIL |" in text
    assert "dashboard_p95" in text


# ---------------------------------------------------------------- positive
def test_dashboard_reads_within_thresholds_pass(tmp_path: Path) -> None:
    summary = tmp_path / "summary.md"
    rc, body, out = verdict(
        tmp_path, "stats_reads_ok_stats.csv", *DASHBOARD, "--summary", str(summary)
    )
    assert rc == 0, out
    assert body["checks"]["dashboard_p95"] is True
    assert body["checks"]["dashboard_p99"] is True
    assert body["checks"]["dashboard_availability"] is True
    assert body["dashboard"]["stats"] == {
        "requests": 600, "failures": 0, "availability": 1.0, "p95_ms": 120.0, "p99_ms": 400.0,
    }  # fmt: skip
    assert "| evidence | 600 | 0 | 1.0000 | 90.0 | 300.0 | pass |" in summary.read_text()


def test_the_thresholds_are_inclusive(tmp_path: Path) -> None:
    # p95 300 ms, p99 800 ms and 597 of 600 (99.5%) on both routes: exactly at the line passes
    rc, body, out = verdict(tmp_path, "stats_reads_at_threshold_stats.csv", *DASHBOARD)
    assert rc == 0, out
    assert body["dashboard"]["stats"]["availability"] == 0.995


def test_without_the_flag_the_sprint_2_verdict_is_unchanged(tmp_path: Path) -> None:
    # The flag adds gates; it never changes the Sprint 2 ones (no accepted test changes).
    rc, body, out = verdict(tmp_path, "stats_reads_p95_over_stats.csv")
    assert rc == 0, out
    assert not any(k.startswith("dashboard") for k in body["checks"])
