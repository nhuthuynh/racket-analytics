"""Binds tests/features/plan_eval.feature (ST-060; NFR-005a). The real planner (``run_case``)
over the real library and eval set; the negative scenarios wrap it in a planner that plants one
violation, so the graders and pass^3 must catch what the real workflow never produces."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support.contract import Seam
from tests.support.paths import BACKEND, REPO

scenarios("plan_eval.feature")

pytestmark = pytest.mark.coaching

CASES = BACKEND / "tests" / "evals" / "plan_cases"
LIBRARY = REPO / "content" / "drills"
LOAD_CASES = Seam("racket.coaching.evals.cases:load_cases", "ST-060", "load_cases(dir)")
LOAD_LIBRARY = Seam("racket.coaching.evals.library:load_library", "ST-060", "load_library(dir)")
RUN_CASE = Seam("racket.coaching.evals.runner:run_case", "ST-060", "run_case(case, library)")
EVALUATE = Seam("racket.coaching.evals.runner:evaluate", "ST-060")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {"planner": RUN_CASE.load()}


@given(parsers.parse('the eval case "{case_id}"'))
def one_case(ctx: dict[str, Any], case_id: str) -> None:
    ctx["cases"] = [c for c in LOAD_CASES.load()(CASES) if c.id == case_id]
    assert len(ctx["cases"]) == 1, case_id


@given("the eval set")
def eval_set(ctx: dict[str, Any]) -> None:
    ctx["cases"] = LOAD_CASES.load()(CASES)


def _weakness_rows(out: dict[str, Any]) -> list[dict[str, Any]]:
    return [x for s in out["plan"]["sessions"] for x in s["assignments"] if x["weakness_id"]]


@given("a planner that starts every session of its plan with a weakness drill instead of a warm-up")
def no_warm_up(ctx: dict[str, Any]) -> None:
    real = ctx["planner"]

    def planted(case: Any, library: Any) -> dict[str, Any]:
        out: dict[str, Any] = real(case, library)
        for s in out["plan"]["sessions"]:
            s["assignments"] = [{**x, "position": i} for i, x in enumerate(s["assignments"][1:], 1)]
        return out

    ctx["planner"] = planted


@given("a planner that cites one more serve than the stats show")
def inflated_n(ctx: dict[str, Any]) -> None:
    real = ctx["planner"]

    def planted(case: Any, library: Any) -> dict[str, Any]:
        out: dict[str, Any] = real(case, library)
        _weakness_rows(out)[0]["citation"]["n"] += 1
        return out

    ctx["planner"] = planted


@given("a planner whose second run gives a different plan")
def flaky(ctx: dict[str, Any]) -> None:
    real, calls = ctx["planner"], []

    def planted(case: Any, library: Any) -> dict[str, Any]:
        out: dict[str, Any] = real(case, library)
        calls.append(case.id)
        if len(calls) == 2:
            out["plan"]["sessions"].reverse()
        return out

    ctx["planner"] = planted


@when("the eval runs 3 times")
def runs(ctx: dict[str, Any]) -> None:
    library = LOAD_LIBRARY.load()(LIBRARY)
    ctx["report"] = EVALUATE.load()(ctx["cases"], library, runs=3, planner=ctx["planner"])


@then(parsers.parse('the case "{case_id}" fails under "{grader}"'))
def fails_under(ctx: dict[str, Any], case_id: str, grader: str) -> None:
    [result] = [r for r in ctx["report"].results if r.case_id == case_id]
    assert not result.passed
    assert any(f.startswith(f"{grader}:") for f in result.failures), result.failures
    assert any(line.startswith(f"FAIL {case_id}") for line in ctx["report"].lines())


@then(parsers.parse("the eval exits {rc:d}"))
def exits(ctx: dict[str, Any], rc: int) -> None:
    assert ctx["report"].exit_code == rc, "\n".join(ctx["report"].lines())


@then(parsers.parse("at least {n:d} cases ran"))
def at_least(ctx: dict[str, Any], n: int) -> None:
    assert len(ctx["report"].results) >= n


@then("every case passed all 3 runs with byte-identical output")
def all_pass(ctx: dict[str, Any]) -> None:
    for r in ctx["report"].results:
        assert r.passed, (r.case_id, r.failures)
        assert r.runs == 3, r.case_id
        assert len(set(r.digests)) == 1, r.case_id
