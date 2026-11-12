"""Binds tests/features/r1_read_latency.feature (ST-074; NFR-010.1-.9; G05-01).

``scripts/ci/perf_verdict.py`` runs as a subprocess with the nightly ``perf-r1`` job's
arguments (the G05-01 command of goal-scorecard §4) on Locust stats and history files
written by ``perf_r1_fixtures``.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from conftest import REPO_ROOT
from perf_r1_fixtures import GROUPS, history_rows, write_run
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]
scenarios("r1_read_latency.feature")

SCRIPT = REPO_ROOT / "scripts" / "ci" / "perf_verdict.py"
R1_ARGS = ("--rps", "50", "--min-rps", "49.5", "--warmup-s", "60", "--p95-ms", "300",
           "--p99-ms", "800", "--max-error-pct", "0.5", "--per-endpoint", GROUPS)  # fmt: skip


@pytest.fixture
def run(tmp_path: Path) -> dict[str, Any]:
    return {"dir": tmp_path, "stats": {}, "history": None}


@given("an R1 run in which every read has p95 120 ms and p99 400 ms")
def all_within(run: dict[str, Any]) -> None:
    run["stats"] = {}


@given(parsers.parse('an R1 run in which the "{name}" read has p95 {ms:d} ms'))
def one_slow(run: dict[str, Any], name: str, ms: int) -> None:
    run["stats"] = {"p95": {name: ms}}


@given(parsers.parse('an R1 run in which the "{name}" read has {n:d} failed requests of {total:d}'))
def failures(run: dict[str, Any], name: str, n: int, total: int) -> None:
    run["stats"] = {"requests": total, "failures": {name: n}}


@given("the run's statistics were never reset after the warm-up")
def no_reset(run: dict[str, Any]) -> None:
    run["history"] = history_rows(reset=False)


@given(parsers.parse("the measured window ran at {rps:g} RPS"))
def slow_rate(run: dict[str, Any], rps: float) -> None:
    run["history"] = history_rows(rps=rps)


@when("the R1 verdict is taken per endpoint")
def take(run: dict[str, Any]) -> None:
    stats = write_run(run["dir"], history=run["history"], **run["stats"])
    out = run["dir"] / "r1-1.json"
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--stats", str(stats), *R1_ARGS, "--json", str(out)],
        capture_output=True, text=True, check=False, timeout=60,
    )  # fmt: skip
    assert out.exists(), res.stdout + res.stderr
    run.update(rc=res.returncode, verdict=json.loads(out.read_text()), err=res.stderr)


@then("the R1 verdict passes for match, score-sheet, dashboard and plan")
def passes(run: dict[str, Any]) -> None:
    v = run["verdict"]
    assert run["rc"] == 0, (v["checks"], run["err"])
    assert v["ok"] is True
    assert {g: e["ok"] for g, e in v["endpoints"].items()} == {
        "match": True, "score-sheet": True, "dashboard": True, "plan": True,
    }  # fmt: skip


@then("the R1 verdict fails")
def fails(run: dict[str, Any]) -> None:
    assert run["rc"] == 1, run["verdict"]["checks"]
    assert run["verdict"]["ok"] is False


@then(parsers.parse('the failure names the "{name}" endpoint and no other'))
def names(run: dict[str, Any], name: str) -> None:
    assert list(run["verdict"]["failed_endpoints"]) == [name]
    assert f"FAIL {name}:" in run["err"]


@then(parsers.parse('the R1 verdict fails on the "{check}" check'))
def fails_on(run: dict[str, Any], check: str) -> None:
    assert run["rc"] == 1
    assert run["verdict"]["checks"][check] is False, run["verdict"]["checks"]
    assert run["verdict"]["failed_endpoints"] == {}  # every read itself was within target
