"""Binds tests/features/ci_e2e_stall_report.feature (CI-E2E-JOURNEYS-TIMEOUT; NFR-074): the
real Playwright of web/ (web/node_modules, installed by the infra-tests job) runs a stand-in
spec with the gated E2E step's reporters, read from ci.yml, and a short global timeout. No
browser is launched: the stand-in tests do not use a page.

CI-STALL-SCENARIO-RACE: the global timeout is set past the measured start-up of the second test
(e2e_stall_harness.global_timeout_s), and the interrupted test must be named by a line the run
prints before it exits, not by the worker's answer to the runner's stop, which Playwright 1.56.1
does not wait for once the global timeout has passed."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from e2e_stall_harness import (
    MAX_GLOBAL_TIMEOUT_S,
    Run,
    StandIn,
    gated_reporters,
    global_timeout_s,
    resolve_reporters,
)
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("ci_e2e_stall_report.feature")

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
WEB = REPO_ROOT / "web"
PLAYWRIGHT = WEB / "node_modules" / ".bin" / "playwright"
SECOND_TEST_WAIT_S = 120


@pytest.fixture
def playwright() -> Path:
    # Fails, never skips: the infra-tests job installs web/ (pnpm install --frozen-lockfile).
    assert PLAYWRIGHT.exists(), f"{PLAYWRIGHT} missing: run pnpm install --frozen-lockfile in web/"
    return PLAYWRIGHT


@pytest.fixture
def reporters() -> str:
    return resolve_reporters(gated_reporters(CI), WEB)


@given(
    "the gated Playwright step's reporters from the CI workflow, with a global timeout of at "
    "least 5 seconds set past the measured start-up of the second test",
    target_fixture="global_timeout",
)
def global_timeout(tmp_path: Path, playwright: Path, reporters: str) -> int:
    warm_up = StandIn(tmp_path / "warm-up", playwright, WEB, SECOND_TEST_WAIT_S)
    start_up = warm_up.measure_start_up(reporters)
    seconds = global_timeout_s(start_up)
    assert seconds <= MAX_GLOBAL_TIMEOUT_S, f"runner too slow: start-up {start_up:.1f}s"
    return seconds


def _run(tmp_path: Path, playwright: Path, reporters: str, timeout: int, freeze: bool) -> Run:
    stand_in = StandIn(tmp_path / "run", playwright, WEB, SECOND_TEST_WAIT_S)
    return stand_in.run(reporters, timeout, freeze_worker=freeze)


@when(
    parsers.parse(
        "Playwright runs a spec whose first test passes and whose second test waits "
        "for {seconds:d} seconds"
    ),
    target_fixture="result",
)
def run(tmp_path: Path, playwright: Path, reporters: str, global_timeout: int, seconds: int) -> Run:
    assert seconds == SECOND_TEST_WAIT_S
    return _run(tmp_path, playwright, reporters, global_timeout, freeze=False)


@when(
    parsers.parse(
        "Playwright runs a spec whose first test passes and whose second test waits "
        "for {seconds:d} seconds, with its worker frozen from the second test's start until "
        "the run has ended"
    ),
    target_fixture="result",
)
def run_frozen(
    tmp_path: Path, playwright: Path, reporters: str, global_timeout: int, seconds: int
) -> Run:
    assert seconds == SECOND_TEST_WAIT_S
    result = _run(tmp_path, playwright, reporters, global_timeout, freeze=True)
    assert result.frozen is not None, (result.cmd, result.out)
    assert result.frozen < global_timeout, ("frozen too late", result.frozen, global_timeout)
    return result


@then("the second test had started before the global timeout")
def second_started(result: Run) -> None:
    assert result.second_started is not None, (result.cmd, result.out)
    assert result.second_started < result.global_timeout, (result.second_started, result.out)


@then(parsers.parse("the run fails within {seconds:d} seconds of its global timeout"))
def fails_fast(result: Run, seconds: int) -> None:
    assert result.rc != 0, result.out
    assert result.elapsed < result.global_timeout + seconds, (result.elapsed, result.out)
    assert result.elapsed < SECOND_TEST_WAIT_S, (result.elapsed, result.out)


@then("the output names the second test as the one the timeout stopped")
def names_stopped(result: Run) -> None:
    out = result.out
    expected = f"Timed out waiting {result.global_timeout}s for the test suite to run"
    assert expected in out, out
    named = r"Interrupted by the global timeout: stall\.spec\.ts:\d+:\d+ \u203a second test waits"
    assert re.search(named, out), out


@then("the output prints the first test with its duration")
def prints_duration(result: Run) -> None:
    assert re.search(r"first test passes \(\d+(\.\d+)?m?s\)", result.out), result.out


@then("the HTML report is written")
def html_report(result: Run) -> None:
    index = result.report / "index.html"
    assert index.is_file(), (result.cmd, result.out)
