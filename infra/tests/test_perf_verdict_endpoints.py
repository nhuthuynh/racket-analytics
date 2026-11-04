"""ST-074 (NFR-010.1-.9; G05-01): ``perf_verdict.py --per-endpoint`` gates every R1 read on
its own p95, p99 and error rate, over the measured window only, at an achieved rate.

The R1 run (``backend/tests/perf/locustfile_r1.py``) names its reads ``match``,
``score-sheet``, ``dashboard:<route>`` and ``plan``; ``--per-endpoint
match,score-sheet,dashboard,plan`` gates each group (a group is the Locust name itself or every
``<group>:<route>`` name; a group's p95/p99 is its worst route). ``--warmup-s`` requires the
history file to show the locustfile's statistics reset at least that long after the run
started, so the stats file holds the measured window only. ``--min-rps`` gates the rate of
that window. Any missing figure fails closed. The nightly ``perf-r1`` job runs the G05-01
command of goal-scorecard §4 on a flags-on stack.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from conftest import REPO_ROOT
from perf_r1_fixtures import GROUPS, history_rows, stats_rows, write_run

pytestmark = pytest.mark.integration

SCRIPT = REPO_ROOT / "scripts" / "ci" / "perf_verdict.py"
NIGHTLY = REPO_ROOT / ".github" / "workflows" / "nightly-quality.yml"
SCORECARD = REPO_ROOT / "docs" / "sprints" / "05" / "goal-scorecard.md"
LOCUSTFILE = REPO_ROOT / "backend" / "tests" / "perf" / "locustfile_r1.py"
R1 = ("--rps", "50", "--min-rps", "49.5", "--warmup-s", "60", "--p95-ms", "300",
      "--p99-ms", "800", "--max-error-pct", "0.5", "--per-endpoint", GROUPS)  # fmt: skip
FLAGS = ("FEATURE_AGE_GATE", "FEATURE_RETENTION_SETTING", "FEATURE_TRAINING_CONSENT",
         "FEATURE_QUOTAS")  # fmt: skip


def verdict(stats: Path, *args: str) -> tuple[int, dict, str, str]:
    out = stats.parent / "verdict.json"
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--stats", str(stats), *args, "--json", str(out)],
        capture_output=True, text=True, check=False, timeout=60,
    )  # fmt: skip
    body = json.loads(out.read_text()) if out.exists() else {}
    return res.returncode, body, res.stdout, res.stderr


def _module():
    spec = importlib.util.spec_from_file_location("perf_verdict", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- negative cases first
def test_a_csv_with_one_slow_endpoint_fails(tmp_path: Path) -> None:
    rc, body, _, err = verdict(write_run(tmp_path, p95={"plan": 301}), *R1)
    assert rc == 1, body
    assert body["ok"] is False
    assert body["failed_endpoints"] == {"plan": ["p95"]}
    assert body["endpoints"]["plan"]["p95_ms"] == 301.0
    assert "FAIL plan: p95 301.0 ms > 300 ms" in err


def test_the_planted_p95_of_1_ms_fails_naming_every_endpoint(tmp_path: Path) -> None:
    # goal-scorecard G05-01 planted failure: --p95-ms 1 -> rc 1 naming the endpoint
    args = [a if a != "300" else "1" for a in R1]
    rc, body, _, err = verdict(write_run(tmp_path), *args)
    assert rc == 1
    assert sorted(body["failed_endpoints"]) == ["dashboard", "match", "plan", "score-sheet"]
    for group in ("match", "score-sheet", "dashboard", "plan"):
        assert f"FAIL {group}: p95" in err


def test_a_group_is_as_slow_as_its_slowest_route(tmp_path: Path) -> None:
    rc, body, _, err = verdict(write_run(tmp_path, p99={"dashboard:evidence": 801}), *R1)
    assert rc == 1
    assert body["failed_endpoints"] == {"dashboard": ["p99"]}
    assert body["endpoints"]["dashboard"]["p99_ms"] == 801.0
    assert body["endpoints"]["dashboard"]["routes"] == ["dashboard:stats", "dashboard:evidence"]
    assert "dashboard:evidence" in err


@pytest.mark.parametrize("value", ["N/A", ""])
def test_a_missing_percentile_fails_closed(tmp_path: Path, value: str) -> None:
    rc, body, _, _ = verdict(write_run(tmp_path, p95={"score-sheet": value}), *R1)
    assert rc == 1
    assert body["failed_endpoints"] == {"score-sheet": ["p95"]}


def test_an_endpoint_never_exercised_fails_closed(tmp_path: Path) -> None:
    rc, body, _, err = verdict(write_run(tmp_path, omit=("plan",)), *R1)
    assert rc == 1
    assert body["checks"]["all_endpoints"] is False
    assert body["missing"] == ["plan"]
    assert body["failed_endpoints"]["plan"] == ["no samples"]
    assert "FAIL plan: no samples" in err


def test_a_group_missing_one_of_its_routes_still_counts_the_rest(tmp_path: Path) -> None:
    # dashboard:evidence missing: dashboard is still exercised (stats), and gated on it
    rc, body, _, _ = verdict(write_run(tmp_path, omit=("dashboard:evidence",)), *R1)
    assert rc == 0, body["checks"]
    assert body["endpoints"]["dashboard"]["routes"] == ["dashboard:stats"]


def test_errors_over_the_limit_on_one_endpoint_fail_it(tmp_path: Path) -> None:
    # 16 of 3,000 = 0.533 % on match: the run's overall 0.107 % would hide it
    rc, body, _, err = verdict(write_run(tmp_path, failures={"match": 16}), *R1)
    assert rc == 1
    assert body["failed_endpoints"] == {"match": ["errors"]}
    assert body["endpoints"]["match"]["error_pct"] == pytest.approx(0.533, abs=0.001)
    assert "FAIL match: errors 0.533 % > 0.5 %" in err


def test_errors_over_the_limit_overall_fail_the_run(tmp_path: Path) -> None:
    rc, body, _, _ = verdict(
        write_run(tmp_path, failures=dict.fromkeys(("match", "plan"), 16)), *R1
    )
    assert rc == 1
    assert body["checks"]["error_pct"] is False
    assert body["error_pct"] == pytest.approx(32 / 15000 * 100, abs=0.001)


def test_a_rate_under_min_rps_is_not_a_pass(tmp_path: Path) -> None:
    rc, body, _, err = verdict(write_run(tmp_path, history=history_rows(rps=49.4)), *R1)
    assert rc == 1
    assert body["checks"]["achieved_rps"] is False
    assert body["achieved_rps"] == pytest.approx(49.4, abs=0.01)
    assert "achieved_rps" in err


def test_without_a_reset_the_warm_up_was_measured_and_the_run_fails(tmp_path: Path) -> None:
    rc, body, _, _ = verdict(write_run(tmp_path, history=history_rows(reset=False)), *R1)
    assert rc == 1
    assert body["checks"]["warmup_excluded"] is False
    assert body["window"] is None


def test_a_reset_before_the_warm_up_ended_fails(tmp_path: Path) -> None:
    # reset 50 s after the run started: 10 s of the 60 s warm-up are in the stats
    hist = history_rows(seed_s=0, warmup_s=50)
    rc, body, _, _ = verdict(write_run(tmp_path, history=hist), *R1)
    assert rc == 1
    assert body["checks"]["warmup_excluded"] is False
    assert body["window"]["warm_up_s"] == 50


def test_a_window_shorter_than_min_window_fails(tmp_path: Path) -> None:
    hist = history_rows(window_s=200)
    rc, body, _, _ = verdict(write_run(tmp_path, history=hist), *R1, "--min-window", "290")
    assert rc == 1
    assert body["checks"]["measurement_window"] is False
    assert body["window"]["seconds"] == 200


def test_warmup_without_a_history_file_cannot_be_judged(tmp_path: Path) -> None:
    rc, _, _, err = verdict(write_run(tmp_path, history=[]), *R1)
    assert rc == 2
    assert "r1-1_stats_history.csv" in err


def test_the_sprint_2_verdict_still_needs_its_state_file(tmp_path: Path) -> None:
    rc, _, _, err = verdict(write_run(tmp_path), "--rps", "50")
    assert rc == 2
    assert "--state" in err


# ---------------------------------------------------------------- positive
def test_every_endpoint_within_target_passes(tmp_path: Path) -> None:
    rc, body, _, err = verdict(write_run(tmp_path), *R1)
    assert rc == 0, (body["checks"], err)
    assert body["failed_endpoints"] == {}
    assert body["endpoints"]["plan"] == {
        "routes": ["plan"], "requests": 3000, "failures": 0, "error_pct": 0.0,
        "p95_ms": 120.0, "p99_ms": 400.0, "ok": True, "failed": [],
    }  # fmt: skip
    assert body["endpoints"]["dashboard"]["requests"] == 6000
    assert body["window"] == {"start": 1_793_000_080, "end": 1_793_000_380, "seconds": 300,
                              "warm_up_s": 80, "requests": 15000, "rps": 50.0}  # fmt: skip
    assert body["achieved_rps"] == 50.0
    assert body["thresholds"] == {"p95_ms": 300.0, "p99_ms": 800.0, "max_error_pct": 0.5,
                                  "min_rps": 49.5, "warmup_s": 60.0}  # fmt: skip


def test_the_thresholds_are_inclusive(tmp_path: Path) -> None:
    stats = write_run(
        tmp_path, p95=dict.fromkeys(("match", "plan"), 300), p99={"dashboard:stats": 800},
        failures={"score-sheet": 15}, history=history_rows(rps=49.5),
    )  # fmt: skip
    rc, body, _, err = verdict(stats, *R1)
    assert rc == 0, (body["checks"], err)
    assert body["endpoints"]["score-sheet"]["error_pct"] == 0.5


def test_min_rps_defaults_to_95_percent_of_rps(tmp_path: Path) -> None:
    args = [a for a in R1 if a not in ("--min-rps", "49.5")]
    rc, body, _, _ = verdict(write_run(tmp_path, history=history_rows(rps=48.0)), *args)
    assert rc == 0, body["checks"]
    assert body["thresholds"]["min_rps"] == 47.5


def test_without_warmup_the_whole_stats_file_is_the_window(tmp_path: Path) -> None:
    args = ("--rps", "50", "--per-endpoint", GROUPS)
    rc, body, _, _ = verdict(write_run(tmp_path, history=[]), *args)
    assert rc == 0, body["checks"]
    assert "warmup_excluded" not in body["checks"]
    assert body["achieved_rps"] == 50.0  # Aggregated Requests/s of the stats file


def test_the_summary_has_one_row_per_endpoint(tmp_path: Path) -> None:
    summary = tmp_path / "summary.md"
    stats = write_run(tmp_path, p95={"plan": 301})
    rc, _, _, _ = verdict(stats, *R1, "--summary", str(summary))
    assert rc == 1
    text = summary.read_text()
    assert "R1 reads per endpoint" in text
    assert "| plan | 3000 | 0.000 | 301.0 | 400.0 | FAIL p95 |" in text
    assert "| match | 3000 | 0.000 | 120.0 | 400.0 | pass |" in text


# ---------------------------------------------------------------- unit
@pytest.mark.unit
def test_groups_take_the_name_itself_or_its_prefixed_routes() -> None:
    mod = _module()
    rows = {r[1]: dict(zip(("Type", "Name"), r[:2], strict=True)) for r in stats_rows()}
    rows["planner"] = {"Type": "GET", "Name": "planner"}  # a prefix is not a group
    assert mod.group_routes(rows, "plan") == ["plan"]
    assert mod.group_routes(rows, "dashboard") == ["dashboard:stats", "dashboard:evidence"]
    assert mod.group_routes(rows, "coaching") == []


# ---------------------------------------------------------------- nightly perf-r1 wiring
def _scorecard_block() -> str:
    text = SCORECARD.read_text()
    return text.split("### G05-01", 1)[1].split("```", 2)[1]


def _commands(script: str) -> list[str]:
    """Shell lines with continuations joined and whitespace collapsed."""
    joined = re.sub(r"\\\n\s*", " ", script)
    return [" ".join(line.split()) for line in joined.splitlines() if line.strip()]


@pytest.mark.unit
def test_the_nightly_perf_r1_job_runs_the_g05_01_command_on_a_flags_on_stack() -> None:
    job = yaml.safe_load(NIGHTLY.read_text())["jobs"]["perf-r1"]
    env = job.get("env", {})
    assert {f: env.get(f) for f in FLAGS} == dict.fromkeys(FLAGS, "true")
    script = "\n".join(s.get("run", "") for s in job["steps"])
    ran = _commands(script)
    wanted = [c for c in _commands(_scorecard_block())
              if "locustfile_r1.py" in c or "perf_verdict.py" in c]  # fmt: skip
    assert len(wanted) == 2
    for command in wanted:
        assert command in ran, command
    assert "make up" in ran
    assert "make demo" in ran


@pytest.mark.unit
def test_perf_r1_does_not_block_the_nightly_publish_or_any_pr() -> None:
    wf = yaml.safe_load(NIGHTLY.read_text())
    assert "perf-r1" not in wf["jobs"]["publish"].get("needs", [])
    on = wf[True]  # PyYAML reads `on:` as True
    assert "pull_request" not in on
    assert "push" not in on


@pytest.mark.unit
def test_the_locustfile_names_every_gated_read() -> None:
    text = LOCUSTFILE.read_text()
    for name in ("match", "score-sheet", "dashboard:stats", "dashboard:evidence", "plan"):
        assert f'"{name}"' in text, name
    assert "reset_all" in text  # the warm-up is cut from the stats the verdict reads
