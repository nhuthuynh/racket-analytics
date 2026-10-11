"""Unit tests for CI-STALL-SCENARIO-RACE: the gated E2E step names the tests a global timeout
interrupts, and the stall-report scenario sets its global timeout past the measured start-up."""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from e2e_stall_harness import gated_reporters, global_timeout_s, read_marker, resolve_reporters

pytestmark = pytest.mark.unit

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
WEB = REPO_ROOT / "web"
REPORTER = "./e2e/helpers/interrupted-tests-reporter.ts"


@pytest.mark.parametrize("start_up", [-0.1, math.nan, math.inf])
def test_a_meaningless_start_up_is_refused_rather_than_turned_into_a_timeout(
    start_up: float,
) -> None:
    with pytest.raises(ValueError, match="start-up"):
        global_timeout_s(start_up)


@pytest.mark.parametrize(
    ("start_up", "seconds"),
    [(0.0, 5), (1.2, 5), (1.67, 6), (2.0, 6), (4.1, 13), (5.69, 18)],
)
def test_the_global_timeout_is_at_least_5_seconds_and_three_times_the_start_up(
    start_up: float, seconds: int
) -> None:
    assert global_timeout_s(start_up) == seconds


def test_the_gated_step_names_the_tests_a_global_timeout_interrupts() -> None:
    reporters = gated_reporters(CI).split(",")
    assert REPORTER in reporters, reporters
    assert (WEB / REPORTER).is_file()
    # The list reporter still prints each test with its duration; html keeps the report.
    assert {"list", "html"} <= set(reporters), reporters


def test_reporter_paths_resolve_against_web_and_built_ins_stay_by_name() -> None:
    resolved = resolve_reporters(f"github,list,{REPORTER},html", WEB).split(",")
    assert resolved[:2] == ["github", "list"]
    assert resolved[2] == str((WEB / REPORTER).resolve())
    assert resolved[3] == "html"


def test_the_marker_is_read_only_once_it_is_complete(tmp_path: Path) -> None:
    marker = tmp_path / "second-test-started"
    assert read_marker(marker) is None
    marker.write_text("")
    assert read_marker(marker) is None
    marker.write_text("1791659943320 4242")
    assert read_marker(marker) == (1791659943.32, 4242)
