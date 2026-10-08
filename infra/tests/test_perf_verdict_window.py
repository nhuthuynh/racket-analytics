"""CI-PERF-GATES (Sprint 3; ST-039; NFR-010, NFR-013, NFR-041): the Locust rate is measured
over a steady-state window, never over the runner's start-up.

PR #6 (job 113186548469) got 39.79 RPS against the 47.5 RPS gate (95% of 50) while ``main``
got 51.52 RPS: the 60 s run-time included 13.8 s of seeding and user spawn with no load.
The measurement window opens at the first ``_stats_history.csv`` sample in which every user
is running (warm-up ends) and closes at the last sample. The achieved rate is the requests
in the window divided by its length. The 50 RPS target, the >= 95% gate, availability,
latency and restore gates are unchanged; a window shorter than 60 s fails the run.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO_ROOT

SCRIPT = REPO_ROOT / "scripts" / "ci" / "perf_verdict.py"
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
STATS_HEADER = [
    "Type", "Name", "Request Count", "Failure Count", "Median Response Time",
    "Average Response Time", "Min Response Time", "Max Response Time", "Average Content Size",
    "Requests/s", "Failures/s", "50%", "66%", "75%", "80%", "90%", "95%", "98%", "99%",
    "99.9%", "99.99%", "100%",
]  # fmt: skip
HISTORY_HEADER = [
    "Timestamp", "User Count", "Type", "Name", "Requests/s", "Failures/s", "50%", "66%", "75%",
    "80%", "90%", "95%", "98%", "99%", "99.9%", "99.99%", "100%", "Total Request Count",
    "Total Failure Count", "Total Median Response Time", "Total Average Response Time",
    "Total Min Response Time", "Total Max Response Time", "Total Average Content Size",
]  # fmt: skip
NAMES = {"score-sheet": "GET", "corrections": "GET", "match": "GET", "correct": "PATCH",
         "undo": "POST"}  # fmt: skip
USERS = 51
T0 = 1_791_400_000


def _load_module():  # noqa: ANN202 - the script under test, imported as a module
    spec = importlib.util.spec_from_file_location("perf_verdict", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def history_rows(*, startup_s: int, steady_s: int, steady_rps: float, users: int = USERS) -> list:
    """One Aggregated sample per second: ``startup_s`` seconds with no users (seeding and
    spawn), then ``steady_s`` seconds with every user running at ``steady_rps``."""
    rows, total = [], 0.0
    for i in range(startup_s):
        rows.append([T0 + i, 0, "", "Aggregated", 0.0, 0.0, *["N/A"] * 11, 0, 0, 0, 0, 0, 0, 0])
    for i in range(steady_s + 1):
        if i:
            total += steady_rps
        rows.append(
            [T0 + startup_s + i, users, "", "Aggregated", steady_rps, 0.0, *[20] * 11,
             int(total), 0, 20, 20, 1, 90, 100]
        )  # fmt: skip
    return rows


def write_run(tmp: Path, history: list | None, *, run_s: float = 60.0) -> tuple[Path, Path]:
    """A Locust stats CSV whose Aggregated Requests/s is the whole-run rate (as Locust writes
    it), plus the state file; ``history`` (if any) goes to ``perf_stats_history.csv``."""
    total = int(history[-1][17]) if history else 3000
    per = total // 6
    rows = [[m, n, per if m == "GET" else per // 2, 0, 20, 20, 1, 90, 100, 0, 0,
             *[20] * 5, 200, 200, 300, 300, 300, 300] for n, m in NAMES.items()]  # fmt: skip
    rows.append(["", "Aggregated", total, 0, 20, 20, 1, 90, 100, round(total / run_s, 2), 0,
                 *[20] * 5, 200, 200, 300, 300, 300, 300])  # fmt: skip
    stats = tmp / "perf_stats.csv"
    with stats.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(STATS_HEADER)
        w.writerows(rows)
    if history is not None:
        with (tmp / "perf_stats_history.csv").open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(HISTORY_HEADER)
            w.writerows(history)
    state = tmp / "perf_state.json"
    state.write_text(json.dumps({"seeded": True, "restored_byte_identical": True, "pairs": 60}))
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


def windowed(stats: Path, *extra: str) -> list[str]:
    return ["--history", str(stats.parent / "perf_stats_history.csv"), "--users", str(USERS),
            *extra]  # fmt: skip


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_a_named_history_file_that_is_missing_fails_closed(tmp_path: Path) -> None:
    stats, state = write_run(tmp_path, None)
    rc, _, out = verdict(stats, state, *windowed(stats))
    assert rc == 2, out
    assert "cannot read the run" in out and "perf_stats_history.csv" in out


@pytest.mark.unit
def test_a_run_whose_users_never_all_started_has_no_window_and_fails(tmp_path: Path) -> None:
    hist = history_rows(startup_s=10, steady_s=70, steady_rps=51, users=USERS - 1)
    stats, state = write_run(tmp_path, hist)
    rc, body, out = verdict(stats, state, *windowed(stats))
    assert rc == 1, out
    assert body["checks"]["measurement_window"] is False
    assert body["checks"]["achieved_rps"] is False
    assert body["window"] is None


@pytest.mark.unit
def test_a_window_shorter_than_60_s_fails_even_at_full_rate(tmp_path: Path) -> None:
    hist = history_rows(startup_s=40, steady_s=50, steady_rps=51)
    stats, state = write_run(tmp_path, hist, run_s=90)
    rc, body, out = verdict(stats, state, *windowed(stats))
    assert rc == 1, out
    assert body["window"]["seconds"] == 50
    assert body["checks"]["measurement_window"] is False


@pytest.mark.unit
def test_a_slow_steady_state_still_fails_the_95_percent_gate(tmp_path: Path) -> None:
    # 47.0 < 47.5 (95% of 50): the window must not hide a real throughput loss.
    hist = history_rows(startup_s=2, steady_s=70, steady_rps=47.0)
    stats, state = write_run(tmp_path, hist, run_s=72)
    rc, body, out = verdict(stats, state, *windowed(stats))
    assert rc == 1, out
    assert body["achieved_rps"] == pytest.approx(47.0, abs=0.05)
    assert body["checks"]["achieved_rps"] is False


@pytest.mark.unit
def test_without_a_history_the_whole_run_rate_is_still_gated(tmp_path: Path) -> None:
    # The stricter, pre-window behaviour stays for callers that pass no --history.
    stats, state = write_run(tmp_path, history_rows(startup_s=14, steady_s=46, steady_rps=51))
    rc, body, out = verdict(stats, state)
    assert rc == 1, out
    assert body["checks"]["achieved_rps"] is False
    assert "measurement_window" not in body["checks"]


# ---------------------------------------------------------------- positive
@pytest.mark.unit
def test_runner_start_up_is_excluded_from_the_rate(tmp_path: Path) -> None:
    # PR #6 shape: ~14 s start-up inside the run, then 51 RPS. Whole run ~40 RPS; window 51.
    hist = history_rows(startup_s=14, steady_s=76, steady_rps=51)
    stats, state = write_run(tmp_path, hist, run_s=90)
    rc, body, out = verdict(stats, state, *windowed(stats))
    assert rc == 0, out
    assert body["achieved_rps"] == pytest.approx(51.0, abs=0.05)
    assert body["run_rps"] < 47.5  # the old measure would have failed this run
    assert body["window"]["warm_up_s"] == 14
    assert body["window"]["seconds"] == 76
    assert body["checks"]["measurement_window"] is True


@pytest.mark.unit
def test_window_counts_only_requests_after_warm_up() -> None:
    mod = _load_module()
    hist = history_rows(startup_s=5, steady_s=60, steady_rps=50)
    hist[5][17] = 300  # requests already counted by the first full-user sample: warm-up
    rows = [dict(zip(HISTORY_HEADER, map(str, r), strict=True)) for r in hist]
    w = mod.measurement_window(rows, USERS)
    assert w["start"] == T0 + 5
    assert w["end"] == T0 + 65
    assert w["requests"] == int(hist[-1][17]) - 300
    assert w["rps"] == pytest.approx(w["requests"] / 60)


@pytest.mark.unit
def test_the_summary_names_the_window_and_the_warm_up(tmp_path: Path) -> None:
    summary = tmp_path / "summary.md"
    stats, state = write_run(tmp_path, history_rows(startup_s=14, steady_s=76, steady_rps=51))
    rc, _, out = verdict(stats, state, *windowed(stats, "--summary", str(summary)))
    assert rc == 0, out
    text = summary.read_text()
    assert "warm-up 14 s" in text
    assert "window 76 s" in text


# ---------------------------------------------------------------- CI wiring
def _perf_steps() -> str:
    import yaml

    job = yaml.safe_load(CI_YML.read_text())["jobs"]["perf-baseline"]
    return "\n".join(s.get("run", "") for s in job["steps"])


@pytest.mark.unit
def test_ci_gates_the_windowed_rate_with_room_for_warm_up() -> None:
    text = _perf_steps()
    assert "--history reports/perf/perf_stats_history.csv" in text
    assert "--users 51" in text and "-u 51" in text
    assert "--rps 50" in text  # the target is not lowered
    assert "--min-window" not in text  # CI keeps the 60 s default window
    # run-time = 60 s window + 30 s warm-up allowance (PR #6 needed 13.8 s)
    assert "-t 90s" in text
