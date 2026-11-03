"""Binds tests/features/flow_metrics.feature (QA-FLOW-METRICS, G05-11): the flow metrics run
as the verifier runs them, over HTTP against the local GitHub REST stub."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from flow_stub import FlowStub, commit, pr, serve
from pytest_bdd import given, parsers, scenarios, then, when
from test_flow_metrics import COST, decisions, run_script

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("flow_metrics.feature")

MERGED = pr(1, "T-1", "2026-11-03T10:00:00Z", "2026-11-03T12:00:00Z")


@pytest.fixture
def stub() -> FlowStub:
    return FlowStub()


@pytest.fixture
def files() -> dict[str, str]:
    return {}


@given("a ticket PR merged into main with a cost table in its decisions file")
def merged_with_table(stub: FlowStub, files: dict[str, str]) -> None:
    stub.pulls.append(MERGED)
    stub.commits[1] = [commit("2026-11-03T09:00:00Z")]
    files["T-1"] = COST


@given("a ticket PR merged into main whose decisions file has no cost table")
def merged_without_table(stub: FlowStub, files: dict[str, str]) -> None:
    stub.pulls.append(MERGED)
    stub.commits[1] = [commit("2026-11-03T09:00:00Z")]
    files["T-1"] = "| Date | Decision |\n|---|---|\n| x | y |\n"


@given("a ticket PR closed without a merge")
def closed_unmerged(stub: FlowStub) -> None:
    stub.pulls.append(pr(2, "T-2", "2026-11-03T10:00:00Z", None))


@given(parsers.parse('a decisions file records "{line}"'))
def stage_line(files: dict[str, str], line: str) -> None:
    files["EM-STATUS"] = f"## Stage counts\n\n{line}\n"


@given("the GitHub API fails")
def github_fails(stub: FlowStub) -> None:
    stub.fail_status = 500


@when("the flow metrics are measured", target_fixture="result")
def measured(
    stub: FlowStub, files: dict[str, str], tmp_path: Path
) -> subprocess.CompletedProcess[str]:
    decisions(tmp_path, files)
    with serve(stub):
        return run_script(stub, tmp_path, "--since", "2026-11-03")


def report(tmp_path: Path) -> dict[str, object]:
    return json.loads((tmp_path / "flow.json").read_text())


@then(parsers.parse("throughput is {n:d}"))
def throughput(tmp_path: Path, n: int) -> None:
    assert report(tmp_path)["throughput"] == n


@then("the measurement is complete")
def complete(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert "flow-metrics: measured, complete" in result.stdout


@then(parsers.parse('the measurement is incomplete, naming "{text}"'))
def incomplete(result: subprocess.CompletedProcess[str], text: str) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert "flow-metrics: measured, incomplete" in result.stdout
    assert text in result.stdout


@then(parsers.parse('{n:d} WIP breach is reported for "{stage}"'))
def breach(result: subprocess.CompletedProcess[str], tmp_path: Path, n: int, stage: str) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    wip = report(tmp_path)["wip_breaches"]
    assert isinstance(wip, dict)
    assert wip["count"] == n
    assert [r["stage"] for r in wip["rows"]] == [stage]


@then("the measurement is unknown")
def unknown(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 2, result.stdout + result.stderr
    assert "flow-metrics: unknown" in result.stdout
