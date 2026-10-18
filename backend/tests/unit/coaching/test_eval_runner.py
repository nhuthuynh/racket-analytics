"""ST-060 pass^3 (NFR-005a): a case passes only when every run passes every grader and all runs
are byte-identical. The planner is a stub here; IT-04-16 runs the real one over the real library.
Negative cases first."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from tests.unit.coaching.eval_helpers import (
    DOCS,
    EVAL_LIBRARY,
    EVALUATE,
    case,
    first_drill,
    valid_output,
)

pytestmark = pytest.mark.unit


def _library() -> Any:
    return EVAL_LIBRARY.load()(root="unit", docs=dict(DOCS), drills=(), version="sha256:test")


def _evaluate(planner: Any, runs: int = 3) -> Any:
    return EVALUATE.load()([case()], _library(), runs=runs, planner=planner)


def test_runs_that_differ_fail_pass3_and_name_the_case() -> None:
    calls: list[int] = []

    def flaky(_case: Any, _library: Any) -> dict[str, Any]:
        calls.append(1)
        out = valid_output()
        if len(calls) == 2:
            first_drill(out)["minutes"] = 11  # still a valid plan, but not the same bytes
        return out

    report = _evaluate(flaky)
    assert len(calls) == 3
    [result] = report.results
    assert not result.passed
    assert any(f.startswith("pass^3:") for f in result.failures), result.failures
    assert report.exit_code == 1
    assert any(line.startswith("FAIL unit-1") for line in report.lines())


def test_a_grader_failure_in_one_run_fails_the_case() -> None:
    def broken(_case: Any, _library: Any) -> dict[str, Any]:
        out = valid_output()
        first_drill(out)["minutes"] = 13  # over the 40% cap, every run
        return out

    report = _evaluate(broken)
    [result] = report.results
    assert not result.passed
    assert any(f.startswith("QD-PL-03:") for f in result.failures)
    assert report.exit_code == 1


def test_a_run_that_raises_fails_the_case_and_the_rest_still_run() -> None:
    def crash(_case: Any, _library: Any) -> dict[str, Any]:
        raise RuntimeError("boom")

    report = _evaluate(crash)
    [result] = report.results
    assert not result.passed
    assert any("RuntimeError: boom" in f for f in result.failures), result.failures
    assert report.exit_code == 1


def test_fewer_than_one_run_is_refused() -> None:
    with pytest.raises(ValueError, match="runs"):
        _evaluate(lambda c, lib: valid_output(), runs=0)


def test_three_identical_valid_runs_pass() -> None:
    frozen = valid_output()
    report = _evaluate(lambda _c, _lib: copy.deepcopy(frozen))
    [result] = report.results
    assert result.passed, result.failures
    assert result.runs == 3
    assert len(set(result.digests)) == 1
    assert report.exit_code == 0
    assert report.lines()[-1] == "pass^3: 1 of 1 cases passed all 3 runs (100%)"
