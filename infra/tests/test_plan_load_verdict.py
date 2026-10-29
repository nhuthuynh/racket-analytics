"""SRE-VERIFY04R3-01 (G04-02 c; NFR-019 read side): the ``perf-baseline`` job loads
``GET /me/plan`` with Locust at 50 RPS and ``scripts/ci/plan_load_verdict.py`` gates it at the
goal's targets: p95 <= 300 ms, p99 <= 800 ms, availability >= 99.5% and >= 95% of the rate
over a >= 60 s steady window. The Locust CSVs are built here in the 2.46.7 column names.
Negative cases first; the first one is the run VERIFY-04-r3 measured (p95 3,229 ms, p99
4,322 ms, 34.4 RPS), which the gate must fail.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

SCRIPT = REPO_ROOT / "scripts" / "ci" / "plan_load_verdict.py"
CI = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text())


def _write(path: Path, rows: list[dict[str, object]]) -> Path:
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return path


def run(
    tmp: Path,
    *,
    p95: object,
    p99: object,
    rps: float,
    n: int = 3000,
    failures: int = 0,
    window_s: int = 70,
    seeded: bool = True,
) -> tuple[int, dict, str]:
    stats = _write(
        tmp / "plan_stats.csv",
        [
            {"Name": "plan", "Request Count": n, "Failure Count": failures, "95%": p95, "99%": p99},
            {"Name": "Aggregated", "Request Count": n, "Failure Count": failures, "95%": p95,
             "99%": p99},
        ],
    )  # fmt: skip
    history = _write(
        tmp / "plan_stats_history.csv",
        [
            {"Timestamp": 1000, "User Count": 10, "Name": "Aggregated", "Total Request Count": 0},
            {"Timestamp": 1020, "User Count": 50, "Name": "Aggregated", "Total Request Count": 0},
            {"Timestamp": 1020 + window_s, "User Count": 50, "Name": "Aggregated",
             "Total Request Count": int(rps * window_s)},
        ],
    )  # fmt: skip
    state = tmp / "plan_state.json"
    state.write_text(json.dumps({"seeded": seeded}))
    out = tmp / "verdict.json"
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--stats", str(stats), "--history", str(history),
         "--state", str(state), "--rps", "50", "--users", "50", "--json", str(out)],
        capture_output=True, text=True, check=False, timeout=60,
    )  # fmt: skip
    body = json.loads(out.read_text()) if out.exists() else {}
    return res.returncode, body, res.stdout + res.stderr


# ---------------------------------------------------------------- negative cases first
def test_the_run_verify_04_r3_measured_fails_the_gate(tmp_path: Path) -> None:
    rc, body, out = run(tmp_path, p95=3229, p99=4322, rps=34.4)
    assert rc == 1, out
    assert body["checks"] == {
        "seeded": True,
        "p95": False,
        "p99": False,
        "availability": True,
        "achieved_rps": False,
        "window": True,
    }


@pytest.mark.parametrize(
    ("kwargs", "gate"),
    [
        ({"p95": 301, "p99": 500, "rps": 50.0}, "p95"),
        ({"p95": 100, "p99": 801, "rps": 50.0}, "p99"),
        ({"p95": 100, "p99": 500, "rps": 50.0, "failures": 16}, "availability"),
        ({"p95": 100, "p99": 500, "rps": 47.4}, "achieved_rps"),
        ({"p95": 100, "p99": 500, "rps": 50.0, "window_s": 59}, "window"),
        ({"p95": 100, "p99": 500, "rps": 50.0, "seeded": False}, "seeded"),
        ({"p95": "N/A", "p99": "N/A", "rps": 50.0, "n": 0}, "p95"),
    ],
)
def test_one_missed_target_fails_the_run(tmp_path: Path, kwargs: dict, gate: str) -> None:
    rc, body, out = run(tmp_path, **kwargs)
    assert rc == 1, out
    assert body["checks"][gate] is False


def test_a_missing_stats_file_refuses_with_rc_2(tmp_path: Path) -> None:
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--stats", str(tmp_path / "none.csv"),
         "--history", str(tmp_path / "none_history.csv"), "--state", str(tmp_path / "s.json"),
         "--rps", "50", "--users", "50"],
        capture_output=True, text=True, check=False, timeout=60,
    )  # fmt: skip
    assert res.returncode == 2, res.stdout + res.stderr


# ---------------------------------------------------------------- positive
def test_a_run_at_the_thresholds_meets_the_goal(tmp_path: Path) -> None:
    rc, body, out = run(tmp_path, p95=300, p99=800, rps=47.5, failures=15)
    assert rc == 0, out
    assert all(body["checks"].values())
    assert body["plan"]["p95_ms"] == 300.0


# ---------------------------------------------------------------- the CI Locust job runs it
def test_the_locust_job_loads_get_me_plan_at_50_rps_and_gates_it() -> None:
    steps = CI["jobs"]["perf-baseline"]["steps"]
    script = "\n".join(str(s.get("run", "")) for s in steps)
    assert "locustfile_plan.py" in script
    assert "-u 50 -r 50" in script
    assert "plan_load_verdict.py" in script
    assert "--rps 50 " in script.split("plan_load_verdict.py", 1)[1]
