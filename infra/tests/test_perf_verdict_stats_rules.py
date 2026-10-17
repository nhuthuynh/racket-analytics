"""C4-LOCUST unit (ST-054 SRE half; NFR-010 "dashboard", NFR-041): the dashboard read rules
of ``scripts/ci/perf_verdict.py`` and the ``perf-baseline`` wiring.

Rules: a dashboard read (GET stats, GET evidence) passes when, on its own route, p95 <= 300 ms,
p99 <= 800 ms and availability (non-failed / all) >= 99.5%. A route with no samples, an
"N/A" percentile or zero requests fails closed.
"""

from __future__ import annotations

import importlib.util
from types import ModuleType

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

SCRIPT = REPO_ROOT / "scripts" / "ci" / "perf_verdict.py"
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
LOCUSTFILE = REPO_ROOT / "backend" / "tests" / "perf" / "locustfile_sprint04.py"


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("perf_verdict_rules", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pv = _module()


def rows(**routes: tuple) -> dict[str, dict[str, str]]:
    """``name=(requests, failures, p95, p99)`` -> the Locust stats rows perf_verdict reads."""
    return {
        n: {"Name": n, "Request Count": str(r), "Failure Count": str(f), "95%": str(p95),
            "99%": str(p99)}
        for n, (r, f, p95, p99) in routes.items()
    }  # fmt: skip


def checks(**routes: tuple) -> dict[str, bool]:
    return pv.dashboard_checks(pv.dashboard_reads(rows(**routes), ("stats", "evidence")))


OK = (600, 0, 120, 400)


# ---------------------------------------------------------------- negative cases first
def test_p95_over_300_ms_fails() -> None:
    assert checks(stats=(600, 0, 301, 400), evidence=OK)["dashboard_p95"] is False


def test_p99_over_800_ms_fails() -> None:
    assert checks(stats=OK, evidence=(600, 0, 120, 801))["dashboard_p99"] is False


def test_availability_below_99_5_percent_on_one_route_fails() -> None:
    # 4 of 600 failed = 99.33%, even when the whole run is above 99.5%
    assert checks(stats=OK, evidence=(600, 4, 120, 400))["dashboard_availability"] is False


def test_a_route_with_no_samples_fails_every_dashboard_gate() -> None:
    c = checks(stats=OK)  # no evidence row at all
    assert c == {"dashboard_p95": False, "dashboard_p99": False, "dashboard_availability": False}


def test_a_route_whose_percentiles_are_not_available_fails_closed() -> None:
    c = checks(stats=OK, evidence=(0, 0, "N/A", "N/A"))
    assert c["dashboard_p95"] is False
    assert c["dashboard_p99"] is False
    assert c["dashboard_availability"] is False


def test_failed_routes_are_named_per_gate() -> None:
    reads = pv.dashboard_reads(
        rows(stats=(600, 0, 310, 900), evidence=(600, 4, 120, 400)), ("stats", "evidence")
    )
    assert pv.dashboard_failed(reads) == {
        "dashboard_p95": ["stats"],
        "dashboard_p99": ["stats"],
        "dashboard_availability": ["evidence"],
    }


def test_the_perf_job_gates_stats_and_evidence_with_the_sprint_4_locustfile() -> None:
    steps = yaml.safe_load(CI.read_text())["jobs"]["perf-baseline"]["steps"]
    text = "\n".join(s.get("run", "") for s in steps)
    assert "-f backend/tests/perf/locustfile_sprint04.py" in text
    assert "--dashboard-reads stats,evidence" in text


def test_the_locustfile_takes_its_routes_from_the_harness_contracts_only() -> None:
    text = LOCUSTFILE.read_text()
    assert "import statscontract" in text
    assert "/stats" not in text  # routes live only in scripts/measure/statscontract.py
    assert '"stats"' in text
    assert '"evidence"' in text


# ---------------------------------------------------------------- positive
def test_reads_exactly_at_the_thresholds_pass() -> None:
    c = checks(stats=(600, 3, 300, 800), evidence=(1000, 5, 300.0, 800.0))
    assert all(c.values()), c


def test_the_route_figures_are_reported() -> None:
    reads = pv.dashboard_reads(rows(stats=(600, 3, 120, 400)), ("stats",))
    assert reads["stats"] == {
        "requests": 600, "failures": 3, "availability": 0.995, "p95_ms": 120.0, "p99_ms": 400.0,
    }  # fmt: skip


def test_no_dashboard_reads_adds_no_gate() -> None:
    assert pv.dashboard_checks(pv.dashboard_reads({}, ())) == {}
