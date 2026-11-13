"""CI-SCHEDULED-RED (PRC-9.1): a red scheduled CI or Nightly quality run on `main` is reported by
`scripts/measure/scheduled_red.py` with its run id, and `scripts/ci/merge_ready.py` refuses while
the latest scheduled CI run on `main` is red; a green scheduled run clears it.

Red first on the recorded payload of run 43007950254 (main b7bf0b7f, 2026-11-11, `failure`).
Unit tests drive the pure rule; integration tests run the scripts as the EM and the merge step
do, the report on recorded payload files and over HTTP against the local GitHub API stub.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from conftest import SCRIPTS_DIR
from github_stub import HEAD_SHA, REPO, GitHubStub, serve, workflow_run

SCRIPT = SCRIPTS_DIR / "measure" / "scheduled_red.py"
MERGE_READY = SCRIPTS_DIR / "ci" / "merge_ready.py"
RECORDED = Path(__file__).parent / "fixtures" / "scheduled"
RED_RUN = 43007950254  # scheduled CI, b7bf0b7f, 2026-11-11: failure
GREEN_RUN = 43206773425  # scheduled CI, 2f947974, 2026-11-12: success
NIGHTLY = ".github/workflows/nightly-quality.yml"


def recorded(run_id: int) -> dict[str, Any]:
    return json.loads((RECORDED / f"run_{run_id}.json").read_text())


def sched(
    run_id: int,
    conclusion: str | None,
    *,
    name: str = "CI",
    path: str = ".github/workflows/ci.yml",
    event: str = "schedule",
    branch: str = "main",
    status: str = "completed",
    created_at: str = "2026-11-12T03:17:00Z",
) -> dict[str, Any]:
    """A workflow run as GET /actions/runs lists it (the fields the rule reads)."""
    return {
        "id": run_id,
        "name": name,
        "path": path,
        "event": event,
        "head_branch": branch,
        "head_sha": f"{run_id:040d}"[-40:],
        "status": status,
        "conclusion": conclusion,
        "created_at": created_at,
        "html_url": f"https://github.com/{REPO}/actions/runs/{run_id}",
    }


def load(path: Path = SCRIPT, name: str = "scheduled_red") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def red_lines(lines: list[str]) -> list[str]:
    return [line for line in lines if line.startswith("scheduled-red: RED ")]


# ------------------------------------------------------------------ unit: the report rule
@pytest.mark.unit
def test_the_recorded_red_scheduled_ci_run_is_a_red_line_naming_its_run_id() -> None:
    lines = load().report([recorded(RED_RUN)])
    [red] = red_lines(lines)
    assert "CI" in red
    assert str(RED_RUN) in red
    assert "failure" in red
    assert "b7bf0b7f" in red


@pytest.mark.unit
def test_a_later_green_scheduled_ci_run_clears_the_red_line() -> None:
    lines = load().report([recorded(RED_RUN), recorded(GREEN_RUN)])
    assert red_lines(lines) == []
    assert any(str(GREEN_RUN) in line for line in lines)


@pytest.mark.unit
@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "timed_out", "startup_failure"])
def test_every_red_conclusion_is_reported(conclusion: str) -> None:
    [red] = red_lines(load().report([sched(7, conclusion)]))
    assert conclusion in red


@pytest.mark.unit
def test_a_red_nightly_quality_run_is_reported_under_its_own_name() -> None:
    run = sched(51, "timed_out", name="Nightly quality", path=NIGHTLY)
    [red] = red_lines(load().report([run, sched(50, "success")]))
    assert "Nightly quality" in red
    assert "51" in red


@pytest.mark.unit
@pytest.mark.parametrize(
    "run",
    [
        sched(9, "failure", event="push"),
        sched(9, "failure", branch="s06/x"),
        sched(9, None, status="in_progress"),
        sched(9, "failure", name="Dependency audit", path=".github/workflows/dependency-audit.yml"),
    ],
    ids=["push", "other-branch", "in-progress", "unwatched-workflow"],
)
def test_runs_that_are_not_a_completed_scheduled_ci_or_nightly_run_on_main_are_ignored(
    run: dict[str, Any],
) -> None:
    assert red_lines(load().report([sched(8, "success"), run])) == []


@pytest.mark.unit
def test_the_newest_completed_run_decides_even_when_it_was_listed_first() -> None:
    newer_red = sched(20, "failure", created_at="2026-11-13T03:17:00Z")
    older_green = sched(10, "success", created_at="2026-11-12T03:17:00Z")
    assert len(red_lines(load().report([newer_red, older_green]))) == 1


@pytest.mark.unit
def test_only_a_red_scheduled_ci_run_blocks_a_merge() -> None:
    mod = load()
    assert str(RED_RUN) in (mod.block_reason([recorded(RED_RUN)]) or "")
    assert mod.block_reason([recorded(RED_RUN), recorded(GREEN_RUN)]) is None
    nightly = sched(51, "failure", name="Nightly quality", path=NIGHTLY)
    assert mod.block_reason([nightly]) is None
    assert mod.block_reason([]) is None


# ------------------------------------------------------------------ integration: the scripts
def run_report(*args: str, api: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in {"GITHUB_TOKEN", "GH_TOKEN"}}
    if api:
        env["GITHUB_API_URL"] = api
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )


@pytest.mark.integration
def test_replaying_the_recorded_red_payload_exits_1_with_its_run_id() -> None:
    result = run_report("--payload", str(RECORDED / f"run_{RED_RUN}.json"))
    assert result.returncode == 1, result.stdout + result.stderr
    assert str(RED_RUN) in "".join(red_lines(result.stdout.splitlines()))


@pytest.mark.integration
def test_replaying_both_recorded_payloads_exits_0() -> None:
    files = [str(RECORDED / f"run_{r}.json") for r in (RED_RUN, GREEN_RUN)]
    result = run_report("--payload", *files)
    assert result.returncode == 0, result.stdout + result.stderr
    assert red_lines(result.stdout.splitlines()) == []


@pytest.mark.integration
def test_an_unreadable_payload_fails_closed_with_exit_2(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert run_report("--payload", str(bad)).returncode == 2


@pytest.mark.integration
def test_the_live_report_reads_scheduled_runs_on_main_over_http() -> None:
    stub = GitHubStub(scheduled_runs=[recorded(RED_RUN)], page_size=100)
    with serve(stub):
        result = run_report("--repo", REPO, api=stub.url)
    assert result.returncode == 1, result.stdout + result.stderr
    assert str(RED_RUN) in "".join(red_lines(result.stdout.splitlines()))
    asked = [p for p, _ in stub.requests if "/actions/runs" in p]
    assert asked
    assert all("event=schedule" in p and "branch=main" in p for p in asked)


def run_merge_ready(stub: GitHubStub) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in {"GITHUB_TOKEN", "GH_TOKEN"}}
    env["GITHUB_API_URL"] = stub.url
    return subprocess.run(
        [sys.executable, str(MERGE_READY), "--repo", REPO, "--pr", "7", "--sha", HEAD_SHA],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )


@pytest.mark.integration
def test_merge_ready_refuses_while_the_latest_scheduled_ci_run_is_red_naming_it() -> None:
    stub = GitHubStub(scheduled_runs=[recorded(RED_RUN)], page_size=100)
    with serve(stub):
        result = run_merge_ready(stub)
    assert result.returncode == 1, result.stdout + result.stderr
    assert str(RED_RUN) in result.stdout


@pytest.mark.integration
def test_merge_ready_allows_once_a_green_scheduled_ci_run_followed() -> None:
    stub = GitHubStub(scheduled_runs=[recorded(RED_RUN), recorded(GREEN_RUN)], page_size=100)
    with serve(stub):
        result = run_merge_ready(stub)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.integration
def test_a_green_dispatched_ci_run_on_the_head_lets_the_fix_merge() -> None:
    dispatched = workflow_run(3, 3, event="workflow_dispatch", conclusion="success")
    dispatched["path"] = ".github/workflows/ci.yml"
    stub = GitHubStub(scheduled_runs=[recorded(RED_RUN)], page_size=100)
    stub.workflow_runs.append(dispatched)
    with serve(stub):
        result = run_merge_ready(stub)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.integration
def test_a_failed_dispatched_ci_run_on_the_head_does_not_lift_the_block() -> None:
    dispatched = workflow_run(3, 3, event="workflow_dispatch", conclusion="failure")
    dispatched["path"] = ".github/workflows/ci.yml"
    stub = GitHubStub(scheduled_runs=[recorded(RED_RUN)], page_size=100)
    stub.workflow_runs.append(dispatched)
    with serve(stub):
        result = run_merge_ready(stub)
    assert result.returncode == 1
    assert str(RED_RUN) in result.stdout
