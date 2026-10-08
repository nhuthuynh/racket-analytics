"""Binds tests/features/ci_perf_gates.feature (CI-PERF-GATES; ST-039; NFR-013, NFR-041,
NFR-073).

Runs the two CI scripts exactly as the workflow does (``scripts/ci/perf_verdict.py`` on a
Locust stats + history pair, ``scripts/ci/run_with_budget.py`` around a command) in a temp
directory. The workflow wiring itself is checked by infra/tests (SRE lane).
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support.paths import REPO

scenarios("ci_perf_gates.feature")

CI = REPO / "scripts" / "ci"
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
ENDPOINTS = {"score-sheet": "GET", "corrections": "GET", "match": "GET", "correct": "PATCH",
             "undo": "POST"}  # fmt: skip
T0 = 1_791_400_000


@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    return {"dir": tmp_path, "history": []}


# ---------------------------------------------------------------- the load test
@given(parsers.parse("a load test that starts up for {seconds:d} seconds with no load"))
def start_up(ctx: dict[str, Any], seconds: int) -> None:
    ctx["history"] = [[T0 + i, 0, "", "Aggregated", 0, 0, *["N/A"] * 11, 0, 0, 0, 0, 0, 0, 0]
                      for i in range(seconds)]  # fmt: skip


@given(
    parsers.parse(
        "then holds {rps:d} requests per second for {seconds:d} seconds with all {users:d} users"
    )
)
def steady(ctx: dict[str, Any], rps: int, seconds: int, users: int) -> None:
    t, total = T0 + len(ctx["history"]), 0
    for i in range(seconds + 1):
        total += rps if i else 0
        ctx["history"].append(
            [t + i, users, "", "Aggregated", rps, 0, *[20] * 11, total, 0, 20, 20, 1, 90, 100]
        )
    ctx["users"] = users


@when(parsers.parse("the performance verdict is taken for {rps:d} requests per second"))
def take_verdict(ctx: dict[str, Any], rps: int) -> None:
    d: Path = ctx["dir"]
    total = ctx["history"][-1][17]
    run_s = len(ctx["history"]) - 1
    per = total // 6
    with (d / "perf_stats.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(STATS_HEADER)
        for name, method in ENDPOINTS.items():
            n = per if method == "GET" else per // 2
            w.writerow([method, name, n, 0, 20, 20, 1, 90, 100, 0, 0, *[20] * 5,
                        200, 200, 300, 300, 300, 300])  # fmt: skip
        w.writerow(["", "Aggregated", total, 0, 20, 20, 1, 90, 100, total / run_s, 0,
                    *[20] * 5, 200, 200, 300, 300, 300, 300])  # fmt: skip
    with (d / "perf_stats_history.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(HISTORY_HEADER)
        w.writerows(ctx["history"])
    (d / "state.json").write_text(json.dumps({"seeded": True, "restored_byte_identical": True}))
    res = subprocess.run(
        [sys.executable, str(CI / "perf_verdict.py"), "--stats", str(d / "perf_stats.csv"),
         "--state", str(d / "state.json"), "--rps", str(rps), "--json", str(d / "v.json"),
         "--history", str(d / "perf_stats_history.csv"), "--users", str(ctx["users"])],
        capture_output=True, text=True, check=False, timeout=60,
    )  # fmt: skip
    assert (d / "v.json").exists(), res.stdout + res.stderr
    ctx["rc"], ctx["verdict"] = res.returncode, json.loads((d / "v.json").read_text())


@then(
    parsers.parse(
        "the achieved rate is {rps:d} requests per second over a {seconds:d} second window"
    )
)
def rate_over_window(ctx: dict[str, Any], rps: int, seconds: int) -> None:
    v = ctx["verdict"]
    assert v["achieved_rps"] == pytest.approx(rps, abs=0.05)
    assert v["window"]["seconds"] == seconds


@then("the rate gate passes")
def rate_passes(ctx: dict[str, Any]) -> None:
    assert ctx["verdict"]["checks"]["achieved_rps"] is True
    assert ctx["rc"] == 0, ctx["verdict"]["checks"]


@then("the rate gate fails")
def rate_fails(ctx: dict[str, Any]) -> None:
    assert ctx["verdict"]["checks"]["achieved_rps"] is False
    assert ctx["rc"] == 1


@then("the measurement window gate fails")
def window_fails(ctx: dict[str, Any]) -> None:
    assert ctx["verdict"]["checks"]["measurement_window"] is False
    assert ctx["rc"] == 1


# ---------------------------------------------------------------- the time budget
@given(parsers.parse("a suite that takes {seconds:g} seconds"))
def a_suite(ctx: dict[str, Any], seconds: float) -> None:
    ctx["cmd"] = ["sleep", f"{seconds:g}"]


@when(parsers.parse("it runs under a budget of {seconds:d} second"))
@when(parsers.parse("it runs under a budget of {seconds:d} seconds"))
def under_budget(ctx: dict[str, Any], seconds: int) -> None:
    rec = ctx["dir"] / "budget.json"
    res = subprocess.run(
        [sys.executable, str(CI / "run_with_budget.py"), str(seconds), "--json", str(rec), "--",
         *ctx["cmd"]],
        capture_output=True, text=True, check=False, timeout=60,
    )  # fmt: skip
    ctx["rc"] = res.returncode
    ctx["record"] = json.loads(rec.read_text()) if rec.exists() else {}


@then(parsers.parse("it is stopped with exit code {rc:d}"))
@then(parsers.parse("it finishes with exit code {rc:d}"))
def exit_code(ctx: dict[str, Any], rc: int) -> None:
    assert ctx["rc"] == rc


@then("the budget record says it was over budget")
def over(ctx: dict[str, Any]) -> None:
    assert ctx["record"]["within_budget"] is False


@then("the budget record says it was within budget")
def within(ctx: dict[str, Any]) -> None:
    assert ctx["record"]["within_budget"] is True
