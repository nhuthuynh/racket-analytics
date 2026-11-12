"""Unit tests for scripts/ops/inject_5xx.py, the G05-02 drill (ST-075c; NFR-041.5).

The drill reaches the API only through the ST-075d seam: it sends ``X-Racket-Fault: 5xx`` on
``--rate`` % of its requests and never changes the stack. Negative cases first. The feature's
drill scenarios are bound in test_slo_alerts_scenarios.py.
"""

from __future__ import annotations

import importlib.util
import itertools
import json
import sys
from pathlib import Path

import pytest
from fault_drill_stubs import INJECT, Stub, run_drill, stub_server


def _module():
    spec = importlib.util.spec_from_file_location("inject_5xx", INJECT)
    assert spec is not None, f"{INJECT} is missing"
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["inject_5xx"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.unit
@pytest.mark.parametrize("rate", ["-1", "101", "ten"])
def test_a_rate_outside_0_to_100_is_refused_with_exit_2(rate: str, tmp_path: Path) -> None:
    result = run_drill("--base-url", "http://127.0.0.1:9", "--rate", rate, "--requests", "1",
                       report=tmp_path / "r.json")  # fmt: skip
    assert result.returncode == 2, result.stdout + result.stderr
    assert "--rate" in result.stderr


@pytest.mark.unit
def test_expecting_an_alert_without_prometheus_is_refused(tmp_path: Path) -> None:
    result = run_drill("--base-url", "http://127.0.0.1:9", "--rate", "10", "--requests", "1",
                       "--expect-alert", "ApiAvailabilityFastBurn",
                       report=tmp_path / "r.json")  # fmt: skip
    assert result.returncode == 2
    assert "--prom" in result.stderr


@pytest.mark.unit
def test_an_unreachable_api_is_exit_2_not_a_pass(tmp_path: Path) -> None:
    result = run_drill("--base-url", "http://127.0.0.1:9", "--rate", "0", "--requests", "3",
                       "--expect-no-5xx", report=tmp_path / "r.json")  # fmt: skip
    assert result.returncode == 2, result.stdout + result.stderr


@pytest.mark.unit
@pytest.mark.parametrize(
    ("rate", "n", "want"),
    [(0, 100, 0), (10, 100, 10), (10, 15, 1), (33, 100, 33), (100, 7, 7), (0.5, 400, 2)],
)
def test_the_fault_share_is_exact_and_spread(rate: float, n: int, want: int) -> None:
    faulted = [_module().faulted(i, rate) for i in range(n)]
    assert sum(faulted) == want
    if 0 < rate < 50:
        assert not any(a and b for a, b in itertools.pairwise(faulted))


@pytest.mark.unit
def test_a_dev_stack_ignores_the_header_and_expect_no_5xx_passes(tmp_path: Path) -> None:
    """NFR-041.6 from the drill side: APP_ENV=dev drops the seam, so no 500 comes back."""
    report = tmp_path / "r.json"
    with stub_server(Stub(honour_seam=False)) as stub:
        result = run_drill("--base-url", stub.url, "--rps", "200", "--rate", "100",
                           "--requests", "10", "--expect-no-5xx", report=report)  # fmt: skip
    assert result.returncode == 0, result.stdout + result.stderr
    doc = json.loads(report.read_text())
    assert doc["faulted_requests"] == 10
    assert doc["status_counts"] == {"200": 10}
    assert doc["result"] == "pass"


@pytest.mark.unit
def test_the_expected_alert_firing_passes_and_records_the_time(tmp_path: Path) -> None:
    report = tmp_path / "r.json"
    with stub_server(Stub(firing=["ApiAvailabilityFastBurn"])) as stub:
        result = run_drill("--base-url", stub.url, "--rps", "200", "--rate", "10",
                           "--requests", "20", "--expect-alert", "ApiAvailabilityFastBurn",
                           "--prom", stub.url, "--poll-s", "0.05", report=report)  # fmt: skip
    assert result.returncode == 0, result.stdout + result.stderr
    doc = json.loads(report.read_text())
    assert doc["alert"]["name"] == "ApiAvailabilityFastBurn"
    assert doc["alert"]["firing"] is True
    assert doc["alert"]["seconds_to_firing"] >= 0


@pytest.mark.unit
def test_a_firing_alert_fails_a_clean_run_naming_it(tmp_path: Path) -> None:
    with stub_server(Stub(firing=["ApiAvailabilitySlowBurn"])) as stub:
        result = run_drill("--base-url", stub.url, "--rps", "200", "--rate", "0",
                           "--requests", "5", "--expect-no-alert", "--prom", stub.url,
                           "--poll-s", "0.05", report=tmp_path / "r.json")  # fmt: skip
    assert result.returncode == 1
    assert "ApiAvailabilitySlowBurn" in result.stdout + result.stderr


@pytest.mark.unit
def test_requests_go_to_the_api_health_route_by_default(tmp_path: Path) -> None:
    with stub_server(Stub()) as stub:
        run_drill("--base-url", stub.url, "--rps", "200", "--rate", "0", "--requests", "2",
                  report=tmp_path / "r.json")  # fmt: skip
    assert stub.paths == ["/api/healthz", "/api/healthz"]


@pytest.mark.unit
def test_the_script_never_changes_the_stack() -> None:
    """The drill drives the seam by header only: no subprocess, no Compose, no env writes."""
    text = INJECT.read_text(encoding="utf-8")
    for forbidden in ("subprocess", "docker", "os.environ[", "putenv"):
        assert forbidden not in text, forbidden
