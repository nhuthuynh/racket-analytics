"""Binds tests/features/close_checks.feature (EM-CLOSE-CHECKS, PRC-6.1-6.3, G05-12): the
Sprint 5 close checks run as the orchestrator and the verifier run them, over HTTP against the
local GitHub REST stub."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from close_checks_stub import CloseStub, pr, serve
from pytest_bdd import given, parsers, scenarios, then, when
from test_close_checks import CLOSE, READY, VERIFY_MERGED, VERIFY_OPEN, blockers, ledger, run, status

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("close_checks.feature")


@pytest.fixture
def stub() -> CloseStub:
    return CloseStub()


@pytest.fixture
def inputs() -> dict[str, object]:
    return {"ledger": [], "blockers": [], "status": status()}


@given("a merged VERIFY-05 PR")
def verify_merged(stub: CloseStub) -> None:
    stub.pulls.append(VERIFY_MERGED)


@given("an open VERIFY-05 PR")
def verify_open(stub: CloseStub) -> None:
    stub.pulls.append(VERIFY_OPEN)


@given(parsers.parse('the ledger holds "{finding}" as "{disposition}"'))
def ledger_row(inputs: dict[str, list[tuple[str, str, str]]], finding: str, disposition: str) -> None:
    inputs["ledger"].append((finding, "major", disposition))


@given(parsers.parse("merged Sprint 5 PRs {a:d} and {b:d}"))
def merged_prs(stub: CloseStub, a: int, b: int) -> None:
    stub.pulls += [pr(a, f"T-{a}"), pr(b, f"T-{b}")]


@given(parsers.parse("the status map lists PR {a:d}"))
def map_one(inputs: dict[str, object], a: int) -> None:
    inputs["status"] = status(a)


@given(parsers.parse("the status map lists PRs {a:d} and {b:d}"))
def map_two(inputs: dict[str, object], a: int, b: int) -> None:
    inputs["status"] = status(a, b)


@given(parsers.parse('an Open blocker row names the {state} cause "#{n:d}"'))
def blocker_row(
    stub: CloseStub, inputs: dict[str, list[tuple[str, str]]], state: str, n: int
) -> None:
    stub.issues[n] = state
    inputs["blockers"].append((f"Planted blocker. Cause: #{n}", "Open"))


@given("the GitHub API fails")
def github_fails(stub: CloseStub) -> None:
    stub.fail_status = 500


def _write(tmp_path: Path, name: str, text: str) -> str:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


@when("the retro trigger is checked", target_fixture="result")
def trigger(
    stub: CloseStub, inputs: dict[str, object], tmp_path: Path
) -> subprocess.CompletedProcess[str]:
    led = _write(tmp_path, "review-rounds.md", ledger(*inputs["ledger"]))  # type: ignore[misc]
    with serve(stub):
        return run(READY, stub, "--ledger", led)


@when("the close is checked", target_fixture="result")
def close(
    stub: CloseStub, inputs: dict[str, object], tmp_path: Path
) -> subprocess.CompletedProcess[str]:
    args = [
        "--status",
        _write(tmp_path, "status.json", json.dumps(inputs["status"])),
        "--ledger",
        _write(tmp_path, "review-rounds.md", ledger(*inputs["ledger"])),  # type: ignore[misc]
        "--blockers",
        _write(tmp_path, "blockers.md", blockers(*inputs["blockers"])),  # type: ignore[misc]
    ]
    with serve(stub):
        return run(CLOSE, stub, *args)


@then(parsers.parse('the retro is not ready, naming "{text}"'))
def not_ready(result: subprocess.CompletedProcess[str], text: str) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert "retro-ready: not ready" in result.stdout
    assert text in result.stdout


@then("the retro is ready")
def ready(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert "retro-ready: ready" in result.stdout


@then(parsers.parse('the close is not met, naming "{text}"'))
def not_met(result: subprocess.CompletedProcess[str], text: str) -> None:
    assert result.returncode == 1, result.stdout + result.stderr
    assert "retro05-check: not met" in result.stdout
    assert text in result.stdout


@then("the close is met")
def met(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert "retro05-check: met" in result.stdout


@then("the close is unknown")
def unknown(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 2, result.stdout + result.stderr
    assert "retro05-check: unknown" in result.stdout
