"""Binds tests/features/ci_perf_stats_gates.feature (C4-LOCUST; ST-054 SRE half; NFR-010
"dashboard", NFR-041).

Runs ``scripts/ci/perf_verdict.py`` exactly as the ``perf-baseline`` job does, with
``--dashboard-reads stats,evidence``, on the Locust stats fixtures in
``infra/tests/fixtures/perf/``. The workflow wiring itself is checked by infra/tests.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support.paths import REPO

scenarios("ci_perf_stats_gates.feature")

CI = REPO / "scripts" / "ci"
PERF_FIXTURES = REPO / "infra" / "tests" / "fixtures" / "perf"


@pytest.fixture
def ctx(tmp_path: Path) -> dict[str, Any]:
    return {"dir": tmp_path}


@given(parsers.parse('the Locust stats file "{name}"'))
def locust_stats_file(ctx: dict[str, Any], name: str) -> None:
    ctx["stats"] = PERF_FIXTURES / name
    assert ctx["stats"].is_file(), ctx["stats"]


@when("the performance verdict is taken with the stats and evidence reads gated")
def take_verdict(ctx: dict[str, Any]) -> None:
    out = ctx["dir"] / "v.json"
    res = subprocess.run(
        [sys.executable, str(CI / "perf_verdict.py"), "--stats", str(ctx["stats"]),
         "--state", str(PERF_FIXTURES / "perf_state_ok.json"), "--rps", "50",
         "--json", str(out), "--dashboard-reads", "stats,evidence"],
        capture_output=True, text=True, check=False, timeout=60,
    )  # fmt: skip
    assert out.exists(), res.stdout + res.stderr
    ctx["rc"], ctx["verdict"] = res.returncode, json.loads(out.read_text())


@then(parsers.parse('the "{gate}" gate fails on the "{route}" route'))
def gate_fails_on_route(ctx: dict[str, Any], gate: str, route: str) -> None:
    assert ctx["verdict"]["checks"][gate] is False
    assert route in ctx["verdict"]["dashboard_failed"][gate]


@then("the performance verdict fails")
def verdict_fails(ctx: dict[str, Any]) -> None:
    assert ctx["rc"] == 1
    assert ctx["verdict"]["ok"] is False


@then("every dashboard read gate passes")
def dashboard_passes(ctx: dict[str, Any]) -> None:
    checks = ctx["verdict"]["checks"]
    gates = {k: v for k, v in checks.items() if k.startswith("dashboard_")}
    assert gates == {"dashboard_p95": True, "dashboard_p99": True,
                     "dashboard_availability": True}, checks  # fmt: skip
    assert ctx["rc"] == 0, checks


@then(parsers.parse('the "{route}" route is reported with p95 {p95:d} ms and p99 {p99:d} ms'))
def route_reported(ctx: dict[str, Any], route: str, p95: int, p99: int) -> None:
    read = ctx["verdict"]["dashboard"][route]
    assert (read["p95_ms"], read["p99_ms"]) == (p95, p99)
