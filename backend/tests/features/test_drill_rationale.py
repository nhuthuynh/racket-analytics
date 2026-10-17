"""Binds tests/features/drill_rationale.feature and limited_data_plan.feature (ST-057; FR-122,
FR-123; QD-PL-04, QD-PL-06). Pure domain: ``assemble`` then ``CitedPlan`` over the coach-reviewed
test library and test citations; no API and no database (IT-04-02b covers those)."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from racket.coaching.plan.domain import (
    CitedPlan,
    MissingCitation,
    PlanWeakness,
    Preferences,
    TrainingPlan,
    assemble,
)
from tests.unit.coaching.citation_helpers import all_citations, cite
from tests.unit.coaching.plan_helpers import reviewed_test_library

scenarios("drill_rationale.feature", "limited_data_plan.feature")

_IDS = {
    "unforced errors": "unforced_errors",
    "serve faults": "serve_faults",
    "errors under pressure": "errors_under_pressure",
}


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {"rallies": 13}


def _cited(ctx: dict[str, Any]) -> CitedPlan:
    cited = ctx["cited"]
    assert isinstance(cited, CitedPlan), cited
    return cited


def _for(ctx: dict[str, Any], name: str) -> list[Any]:
    found = [x for s in _cited(ctx).sessions for x in s if x.assignment.weakness_id == _IDS[name]]
    assert found, name
    return found


@given("the reviewed test library with warm-ups, wall, ball-machine and 4-player drills")
def reviewed_library(ctx: dict[str, Any]) -> None:
    ctx["library"] = reviewed_test_library()


@given(parsers.parse('the top weaknesses are "{a}" on "{ta}", "{b}" on "{tb}" and "{c}" on "{tc}"'))
def top_weaknesses(ctx: dict[str, Any], a: str, ta: str, b: str, tb: str, c: str, tc: str) -> None:
    ctx["weaknesses"] = [
        PlanWeakness(_IDS[name], target, rank)
        for rank, (name, target) in enumerate([(a, ta), (b, tb), (c, tc)], start=1)
    ]


@given("a solo player with a wall and no ball machine, 30 minutes per session, 3 sessions a week")
def solo_player(ctx: dict[str, Any]) -> None:
    ctx["prefs"] = Preferences(30, 3, 1, frozenset({"wall"}), "intermediate")


@given("the player's citations for every plan target")
def every_citation(ctx: dict[str, Any]) -> None:
    ctx["citations"] = all_citations()


@given(parsers.parse('the player has no citation for "{target}"'))
def no_citation(ctx: dict[str, Any], target: str) -> None:
    del ctx["citations"][target]


@given(parsers.parse('the player\'s "{target}" is {k:d} of {n:d} serves'))
def serve_citation(ctx: dict[str, Any], target: str, k: int, n: int) -> None:
    ctx["citations"][target] = cite(target, k, n)


@given(
    parsers.parse(
        'the player\'s "{target}" is {k:d} unforced errors over {games:d} games in {m:d} matches'
    )
)
def pooled_citation(ctx: dict[str, Any], target: str, k: int, games: int, m: int) -> None:
    matches = tuple(f"m{i}" for i in range(1, m + 1))
    ctx["citations"][target] = cite(target, k, games, rallies=k // m, matches=matches)


@given(parsers.parse('one short match of {rallies:d} rallies with no citation for "{target}"'))
def short_match_missing(ctx: dict[str, Any], rallies: int, target: str) -> None:
    ctx["rallies"], ctx["citations"] = rallies, all_citations()
    del ctx["citations"][target]


@given(parsers.parse('one short match of {rallies:d} rallies where "{target}" is low-sample'))
def short_match_low(ctx: dict[str, Any], rallies: int, target: str) -> None:
    ctx["rallies"], ctx["citations"] = rallies, all_citations()
    old = ctx["citations"][target]
    ctx["citations"][target] = cite(target, old.k, old.n, low_sample=True)


@given(parsers.parse('one short match of {rallies:d} rallies where only "{target}" is low-sample'))
def short_match_only_low(ctx: dict[str, Any], rallies: int, target: str) -> None:
    short_match_low(ctx, rallies, target)


@when("the plan is assembled and cited")
def assembled_and_cited(ctx: dict[str, Any]) -> None:
    plan = assemble(ctx["weaknesses"], ctx["prefs"], ctx["library"])
    assert isinstance(plan, TrainingPlan), plan
    try:
        ctx["cited"] = CitedPlan(plan, ctx["citations"], rallies=ctx["rallies"])
    except MissingCitation as refused:
        ctx["refused"] = refused


@then(parsers.parse('the plan is refused under "{rule}"'))
def refused_under(ctx: dict[str, Any], rule: str) -> None:
    assert "cited" not in ctx
    assert ctx["refused"].violations
    assert all(v.startswith(rule) for v in ctx["refused"].violations)


@then(parsers.parse('the refusal names the drill "{ref}"'))
def refusal_names(ctx: dict[str, Any], ref: str) -> None:
    assert any(ref in v for v in ctx["refused"].violations)


@then("every assignment cites a metric it targets, a value, n and at most 10 rallies")
def every_cited(ctx: dict[str, Any]) -> None:
    for session in _cited(ctx).sessions:
        for x in session:
            c = x.citation
            assert c.metric_id in x.assignment.drill.target_metrics
            assert c.n >= 1
            assert c.value is not None
            assert 1 <= len(c.rally_ids) <= 10


@then(parsers.parse('the drill for "{name}" says why "{text}"'))
def says_why(ctx: dict[str, Any], name: str, text: str) -> None:
    assert {x.why for x in _for(ctx, name)} == {text}


@then(
    parsers.parse(
        'the drill for "{name}" cites {shown:d} rallies and links to all {n:d} in {m:d} matches'
    )
)
def see_all(ctx: dict[str, Any], name: str, shown: int, n: int, m: int) -> None:
    for x in _for(ctx, name):
        assert len(x.citation.rally_ids) == shown
        assert x.citation.see_all == n
        assert len(x.citation.evidence) == m


@then(parsers.parse("the plan carries limited data from {rallies:d} rallies"))
def limited(ctx: dict[str, Any], rallies: int) -> None:
    limited_data = _cited(ctx).limited_data
    assert limited_data is not None
    assert limited_data.rallies == rallies


@then(parsers.parse('the plan says "{text}"'))
def limited_text(ctx: dict[str, Any], text: str) -> None:
    limited_data = _cited(ctx).limited_data
    assert limited_data is not None
    assert limited_data.text == text


@then("the plan carries no limited-data notice")
def no_limited(ctx: dict[str, Any]) -> None:
    assert _cited(ctx).limited_data is None
