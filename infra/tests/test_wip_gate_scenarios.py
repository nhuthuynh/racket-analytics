"""Binds tests/features/wip_gate.feature (QA-WIP-GATE, PRC-12.1, G06-10): the WIP gate runs as
the orchestrator runs it before a "start ticket" step, over HTTP against the local GitHub REST
stub."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from test_wip_gate import run_script
from wip_stub import WipStub, serve

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("wip_gate.feature")


@pytest.fixture
def stub() -> WipStub:
    return WipStub()


def _next(stub: WipStub) -> int:
    return len(stub.pulls) + 1


@given(parsers.re(r"(?P<n>\d+) ticket PRs? (?:is|are) in review"))
def in_review(stub: WipStub, n: str) -> None:
    for _ in range(int(n)):
        stub.in_review(_next(stub))


@given(parsers.re(r"(?P<n>\d+) ticket PRs? (?:is|are) in progress"))
def in_progress(stub: WipStub, n: str) -> None:
    for _ in range(int(n)):
        stub.in_progress(_next(stub))


@given("the GitHub API fails")
def github_fails(stub: WipStub) -> None:
    stub.fail_status = 500


@when("the orchestrator asks to start a ticket", target_fixture="result")
def ask(stub: WipStub, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    with serve(stub):
        return run_script(stub, tmp_path)


@then(parsers.parse('the start is refused, naming "{stage}"'))
def refused(result: subprocess.CompletedProcess[str], stage: str) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert f"wip-gate: start refused: {stage} " in result.stdout


@then("the start is allowed")
def allowed(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert "wip-gate: start allowed" in result.stdout


@then(parsers.parse('the stage counts read "{line}"'))
def stage_counts(result: subprocess.CompletedProcess[str], line: str) -> None:
    assert line in result.stdout


@then("the start is refused as unknown")
def unknown(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 2
    assert "wip-gate: unknown" in result.stdout
