"""Binds tests/features/scheduled_red.feature (CI-SCHEDULED-RED, PRC-9.1): the scheduled-red
report and the merge check, run as scripts on the recorded payloads of runs 43007950254 and
43206773425, the merge check over HTTP against the local GitHub API stub."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from github_stub import GitHubStub, serve, workflow_run
from pytest_bdd import given, parsers, scenarios, then, when
from test_scheduled_red import (
    NIGHTLY,
    RECORDED,
    red_lines,
    run_merge_ready,
    run_report,
    sched,
)

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("scheduled_red.feature")


@pytest.fixture
def runs() -> list[dict[str, Any]]:
    return []


@pytest.fixture
def stub() -> GitHubStub:
    return GitHubStub(page_size=100)


@given(parsers.parse("the recorded scheduled run {run_id:d}"))
def recorded_run(runs: list[dict[str, Any]], run_id: int) -> None:
    runs.append(json.loads((RECORDED / f"run_{run_id}.json").read_text()))


@given(parsers.parse('a scheduled "{name}" run {run_id:d} on main that ended "{conclusion}"'))
def planted_run(runs: list[dict[str, Any]], name: str, run_id: int, conclusion: str) -> None:
    path = NIGHTLY if name == "Nightly quality" else ".github/workflows/ci.yml"
    runs.append(sched(run_id, conclusion, name=name, path=path))


@given("an open pull request whose head is green and approved")
def green_approved_pr(stub: GitHubStub) -> None:
    """The stub's default PR: green check runs and both tier 1 approvals on the head."""


@given(parsers.parse('a dispatched CI run on the head that ended "{conclusion}"'))
def dispatched(stub: GitHubStub, conclusion: str) -> None:
    run = workflow_run(3, 3, event="workflow_dispatch", conclusion=conclusion)
    run["path"] = ".github/workflows/ci.yml"
    stub.workflow_runs.append(run)


@when("the scheduled-red report runs", target_fixture="result")
def report(runs: list[dict[str, Any]], tmp_path: Path) -> subprocess.CompletedProcess[str]:
    files = []
    for i, run in enumerate(runs):
        path = tmp_path / f"run_{i}.json"
        path.write_text(json.dumps(run))
        files.append(str(path))
    return run_report("--payload", *files)


@when("the orchestrator runs the merge check on the head", target_fixture="result")
def merge_check(stub: GitHubStub, runs: list[dict[str, Any]]) -> subprocess.CompletedProcess[str]:
    stub.scheduled_runs = list(runs)
    with serve(stub):
        return run_merge_ready(stub)


@then(parsers.parse("it exits {code:d}"))
def exits(result: subprocess.CompletedProcess[str], code: int) -> None:
    assert result.returncode == code, result.stdout + result.stderr


@then(parsers.parse('it prints a red line naming "{name}", run {run_id:d} and "{conclusion}"'))
def red_line(result: subprocess.CompletedProcess[str], name: str, run_id: int, conclusion: str):
    [red] = red_lines(result.stdout.splitlines())
    assert name in red
    assert str(run_id) in red
    assert conclusion in red


@then("it prints no red line")
def no_red_line(result: subprocess.CompletedProcess[str]) -> None:
    assert red_lines(result.stdout.splitlines()) == [], result.stdout


@then(parsers.parse('the merge is refused naming "{word}"'))
def refused(result: subprocess.CompletedProcess[str], word: str) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert word in result.stdout


@then("the merge is allowed")
def allowed(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert "merge-ready: yes" in result.stdout
