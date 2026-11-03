"""QA-FLOW-METRICS (story PRC-05; atomic items PRC-5.1-5.5; goal metric G05-11; ADR 0056
decisions 1 and 3): `scripts/measure/flow_metrics.py` reports the flow and cost-per-PR values
from the GitHub REST API (no GraphQL) and the sprint's decisions files.

Unit tests drive the pure `measure()` on stubbed REST JSON; integration tests run the script
over real HTTP against `flow_stub.py`. Negative cases first. The values are reported, never
targets [ASB/AGL-02]; only "measured and complete" decides the exit code.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from conftest import SCRIPTS_DIR
from flow_stub import REPO, FlowStub, commit, pr, run, serve

SCRIPT = SCRIPTS_DIR / "measure" / "flow_metrics.py"
NOW = "2026-11-10T12:00:00Z"
COST = (
    "## Cost per PR (ADR 0056 decision 1)\n\n"
    "| Round | Wall time (min) | total_cost_usd / tokens |\n|---|---|---|\n"
    "| Author build | 40 | not measured |\n| Review round 1 | 10 | 0.42 |\n"
)


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("flow_metrics", SCRIPT)
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ts(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


def decisions(tmp_path: Path, files: dict[str, str]) -> Path:
    d = tmp_path / "decisions"
    d.mkdir(exist_ok=True)
    for name, text in files.items():
        (d / f"{name}.md").write_text(f"# {name} decisions\n\n{text}")
    return d


def measure(
    tmp_path: Path,
    pulls: list[dict[str, Any]],
    commits: dict[int, list[dict[str, Any]]] | None = None,
    runs: list[dict[str, Any]] | None = None,
    files: dict[str, str] | None = None,
    **window: Any,
) -> dict[str, Any]:
    fm = load()
    return fm.measure(
        closed=[p for p in pulls if p["state"] == "closed"],
        open_prs=[p for p in pulls if p["state"] == "open"],
        commits=commits or {},
        runs=runs or [],
        decisions_dir=decisions(tmp_path, files or {}),
        window=fm.Window(**window),
        now=ts(NOW),
    )


# ------------------------------------------------------------------ unit: PRC-5.2 throughput


@pytest.mark.unit
def test_a_pr_with_no_merge_time_is_excluded_from_throughput(tmp_path: Path) -> None:
    pulls = [
        pr(1, "T-1", "2026-11-03T10:00:00Z", "2026-11-03T12:00:00Z"),
        pr(2, "T-2", "2026-11-03T10:00:00Z", None),  # closed, never merged
    ]
    report = measure(tmp_path, pulls, {1: [commit("2026-11-03T09:00:00Z")]}, files={"T-1": COST})
    assert report["throughput"] == 1
    assert [p["number"] for p in report["merged"]] == [1]


@pytest.mark.unit
def test_throughput_counts_only_merges_into_main_inside_the_window(tmp_path: Path) -> None:
    pulls = [
        pr(1, "T-1", "2026-11-02T10:00:00Z", "2026-11-02T23:59:59Z"),  # before --since
        pr(2, "T-2", "2026-11-03T10:00:00Z", "2026-11-03T11:00:00Z"),
        pr(3, "T-3", "2026-11-03T10:00:00Z", "2026-11-03T11:00:00Z", base="s05/other"),
        pr(4, "T-4", "2026-11-04T10:00:00Z", "2026-11-05T00:00:00Z"),  # at --until: excluded
        pr(9, "T-9", "2026-11-03T10:00:00Z", "2026-11-03T11:00:00Z"),  # above --pr-to
    ]
    report = measure(
        tmp_path, pulls, since=ts("2026-11-03T00:00:00Z"), until=ts("2026-11-05T00:00:00Z"), pr_to=8
    )
    assert report["throughput"] == 1
    assert [p["number"] for p in report["merged"]] == [2]


# ------------------------------------------------------------------ unit: PRC-5.1 cycle time


@pytest.mark.unit
def test_cycle_time_runs_from_the_earliest_commit_to_the_merge(tmp_path: Path) -> None:
    pulls = [
        pr(1, "T-1", "2026-11-03T10:00:00Z", "2026-11-03T12:00:00Z"),
        pr(2, "T-2", "2026-11-03T10:00:00Z", "2026-11-04T10:00:00Z"),
        pr(3, "T-3", "2026-11-03T10:00:00Z", "2026-11-03T14:00:00Z"),
    ]
    commits = {
        1: [commit("2026-11-03T11:00:00Z"), commit("2026-11-03T08:00:00Z")],  # 4 h
        2: [commit("2026-11-03T10:00:00Z")],  # 24 h
        3: [commit("2026-11-03T08:00:00Z")],  # 6 h
    }
    report = measure(tmp_path, pulls, commits)
    assert report["cycle_time_h"] == {"n": 3, "median": 6.0, "max": 24.0}
    # Open -> merge (working-agreement §10 "PR time-to-merge"; sprint-report §2 column).
    assert report["time_to_merge_h"] == {"n": 3, "median": 4.0, "mean": 10.0, "max": 24.0}


@pytest.mark.unit
def test_a_merged_pr_without_commits_has_no_cycle_time_and_is_named(tmp_path: Path) -> None:
    pulls = [pr(1, "T-1", "2026-11-03T10:00:00Z", "2026-11-03T12:00:00Z")]
    report = measure(tmp_path, pulls, {1: []})
    assert report["cycle_time_h"] == {"n": 0, "median": None, "max": None}
    assert report["merged"][0]["cycle_time_h"] is None


# ------------------------------------------------------------------ unit: PRC-5.3 age


@pytest.mark.unit
def test_work_item_age_of_each_open_ticket_pr_is_named_when_over_the_median(
    tmp_path: Path,
) -> None:
    pulls = [
        pr(1, "T-1", "2026-11-09T10:00:00Z", "2026-11-09T12:00:00Z"),  # cycle 4 h
        pr(5, "T-5", "2026-11-10T09:00:00Z", state="open"),
        pr(6, "T-6", "2026-11-10T09:00:00Z", state="open", base="other"),  # not into main
        pr(7, "T-7", "2026-11-10T09:00:00Z", state="open"),
    ]
    commits = {
        1: [commit("2026-11-09T08:00:00Z")],
        5: [commit("2026-11-10T10:00:00Z")],  # 2 h old
        7: [commit("2026-11-09T12:00:00Z")],  # 24 h old
    }
    report = measure(tmp_path, pulls, commits)
    assert report["work_item_age"] == [
        {"number": 5, "ticket": "T-5", "age_h": 2.0, "over_median_cycle_time": False},
        {"number": 7, "ticket": "T-7", "age_h": 24.0, "over_median_cycle_time": True},
    ]


# ------------------------------------------------------------------ unit: PRC-5.4 WIP breaches


@pytest.mark.unit
def test_a_stage_count_above_its_limit_is_a_breach_with_its_reason(tmp_path: Path) -> None:
    files = {
        "A": "## Stage counts\n\nIn progress 4 · in review 3 · awaiting QA 2 · awaiting merge 1.\n",
        "B": "In progress 5 · in review 4 · awaiting QA 0 · awaiting merge 0."
        " Reason: two hotfixes\n",
        "C": "in progress 1, in review 0, awaiting qa 3, awaiting merge 0\n",
    }
    report = measure(tmp_path, [], files=files)
    wip = report["wip_breaches"]
    assert wip["stage_lines"] == 3
    assert wip["count"] == 3
    assert [(r["file"], r["stage"], r["count"], r["limit"]) for r in wip["rows"]] == [
        ("B.md", "in progress", 5, 4),
        ("B.md", "in review", 4, 3),
        ("C.md", "awaiting QA", 3, 2),
    ]
    assert wip["rows"][0]["reason"] == "Reason: two hotfixes"
    assert wip["rows"][2]["reason"] is None
    assert wip["rows"][0]["line"] == 3


# ------------------------------------------------------------------ unit: PRC-5.5 cost tables


@pytest.mark.unit
def test_cost_table_completeness_names_missing_tables_and_not_measured_rounds(
    tmp_path: Path,
) -> None:
    pulls = [
        pr(1, "T-1", "2026-11-03T10:00:00Z", "2026-11-03T12:00:00Z"),  # table
        pr(2, "T-2", "2026-11-03T10:00:00Z", "2026-11-03T12:00:00Z"),  # file, no table
        pr(3, "T-3", "2026-11-03T10:00:00Z", "2026-11-03T12:00:00Z"),  # no file
        pr(4, None, "2026-11-03T10:00:00Z", "2026-11-03T12:00:00Z"),  # no ticket id
        pr(5, "T-5", "2026-11-03T10:00:00Z", "2026-11-03T12:00:00Z"),  # heading, no rows
    ]
    files = {
        "T-1": COST,
        "T-2": "| Date | Decision |\n|---|---|\n| x | y |\n",
        "T-5": "## Cost per PR\n\n| Round | Wall time (min) |\n|---|---|\n",
    }
    cost = measure(tmp_path, pulls, files=files)["cost_tables"]
    assert cost["merged"] == 5
    assert cost["with_table"] == 1
    assert cost["share"] == 0.2
    assert cost["missing"] == ["#2 T-2", "#3 T-3", "#4 (no ticket id)", "#5 T-5"]
    assert cost["not_measured"] == ["T-1: Author build"]


@pytest.mark.unit
def test_the_report_is_complete_only_when_every_merged_ticket_has_a_cost_table(
    tmp_path: Path,
) -> None:
    pulls = [pr(1, "T-1", "2026-11-03T10:00:00Z", "2026-11-03T12:00:00Z")]
    assert measure(tmp_path, pulls, files={"T-1": COST})["complete"] is True
    assert measure(tmp_path, pulls, files={"T-1": "no table"})["complete"] is False


# ------------------------------------------------------------------ unit: CI minutes


@pytest.mark.unit
def test_ci_minutes_per_pr_sum_its_branch_runs_between_open_and_merge(tmp_path: Path) -> None:
    p = pr(1, "T-1", "2026-11-03T10:00:00Z", "2026-11-03T12:00:00Z", head="s05/t-1")
    runs = [
        run("s05/t-1", "2026-11-03T10:05:00Z", "2026-11-03T10:17:30Z", run_id=1),  # 12.5 min
        run("s05/t-1", "2026-11-03T11:00:00Z", "2026-11-03T11:10:00Z", run_id=2),  # 10 min
        run("s05/t-1", "2026-11-03T13:00:00Z", "2026-11-03T13:10:00Z", run_id=3),  # after merge
        run("s05/other", "2026-11-03T11:00:00Z", "2026-11-03T11:30:00Z", run_id=4),
    ]
    report = measure(tmp_path, [p], runs=runs)
    assert report["ci_minutes"] == [{"number": 1, "ticket": "T-1", "runs": 2, "minutes": 22.5}]
    assert report["ci_minutes_total"] == 22.5


# ------------------------------------------------------------------ integration: over HTTP


def run_script(stub: FlowStub, tmp_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in {"GITHUB_TOKEN", "GH_TOKEN"}}
    env["GITHUB_API_URL"] = stub.url
    d = tmp_path / "decisions"
    d.mkdir(exist_ok=True)
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            REPO,
            "--decisions",
            str(d),
            "--now",
            NOW,
            "--json",
            str(tmp_path / "flow.json"),
            *extra,
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


def sprint_stub() -> FlowStub:
    return FlowStub(
        pulls=[
            pr(1, "T-1", "2026-11-03T10:00:00Z", "2026-11-03T12:00:00Z", head="s05/t-1"),
            pr(2, "T-2", "2026-11-03T10:00:00Z", "2026-11-04T10:00:00Z", head="s05/t-2"),
            pr(3, "T-3", "2026-11-03T10:00:00Z", None, head="s05/t-3"),  # closed unmerged
            pr(4, "T-4", "2026-11-03T10:00:00Z", "2026-11-03T14:00:00Z", head="s05/t-4"),
            pr(5, "T-5", "2026-11-10T09:00:00Z", state="open", head="s05/t-5"),
        ],
        commits={
            1: [commit("2026-11-03T08:00:00Z")],
            2: [commit("2026-11-03T10:00:00Z"), commit("2026-11-03T11:00:00Z")],
            4: [commit("2026-11-03T08:00:00Z")],
            5: [commit("2026-11-10T10:00:00Z")],
        },
        runs=[run("s05/t-1", "2026-11-03T10:05:00Z", "2026-11-03T10:17:30Z")],
    )


@pytest.mark.integration
def test_script_measures_over_rest_pages_and_writes_the_json(tmp_path: Path) -> None:
    stub = sprint_stub()
    d = decisions(tmp_path, {"T-1": COST, "T-2": COST, "T-4": COST})
    with serve(stub):
        result = run_script(stub, tmp_path, "--since", "2026-11-03")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "flow-metrics: measured, complete" in result.stdout
    report = json.loads((tmp_path / "flow.json").read_text())
    assert report["throughput"] == 3
    assert report["cycle_time_h"] == {"n": 3, "median": 6.0, "max": 24.0}
    assert report["work_item_age"][0]["number"] == 5
    assert report["ci_minutes_total"] == 12.5
    assert report["cost_tables"]["share"] == 1.0
    assert d.is_dir()
    # REST only (PRC-5.1): every request is a GET under /repos/{repo}/, none to GraphQL, and
    # paging uses ?page=N (two items a page in the stub), never a Link URL.
    assert stub.requests
    assert all(r.startswith(f"/repos/{REPO}/") for r in stub.requests), stub.requests
    assert any("state=closed" in r and "page=3" in r for r in stub.requests)


@pytest.mark.integration
def test_script_exits_1_when_a_merged_ticket_has_no_cost_table(tmp_path: Path) -> None:
    stub = sprint_stub()
    decisions(tmp_path, {"T-1": COST, "T-2": COST})
    with serve(stub):
        result = run_script(stub, tmp_path, "--since", "2026-11-03")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "flow-metrics: measured, incomplete" in result.stdout
    assert "#4 T-4" in result.stdout


@pytest.mark.integration
def test_script_exits_2_when_github_cannot_be_read(tmp_path: Path) -> None:
    stub = FlowStub(fail_status=500)
    with serve(stub):
        result = run_script(stub, tmp_path)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "flow-metrics: unknown (GitHub could not be read" in result.stdout
    assert not (tmp_path / "flow.json").exists()


@pytest.mark.unit
def test_working_agreement_section_10_calls_the_script_not_graphql() -> None:
    text = (SCRIPTS_DIR.parent / "docs" / "process" / "working-agreement.md").read_text()
    section = text.split("## 10. Metrics reviewed each sprint", 1)[1].split("\n## ", 1)[0]
    assert "gh pr list" not in section
    assert "scripts/measure/flow_metrics.py" in section


@pytest.mark.integration
def test_script_reads_commits_only_for_prs_in_the_window(tmp_path: Path) -> None:
    """A sprint's run must not page the commits of every PR the repository ever merged."""
    stub = sprint_stub()
    stub.pulls.append(pr(8, "OLD-8", "2026-10-01T10:00:00Z", "2026-10-01T12:00:00Z"))
    decisions(tmp_path, {"T-1": COST, "T-2": COST, "T-4": COST})
    with serve(stub):
        result = run_script(stub, tmp_path, "--since", "2026-11-03")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not [r for r in stub.requests if "/pulls/8/" in r], stub.requests
