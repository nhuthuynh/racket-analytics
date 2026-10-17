"""Binds tests/features/training_plan.feature (ST-056; FR-121; QD-PL-01..03).

Pure domain: ``racket.coaching.plan.domain.assemble`` over a coach-reviewed test library
(``tests.unit.coaching.plan_helpers``); no API and no database.
"""

from __future__ import annotations

import random
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from racket.coaching.plan.domain import (
    NO_DRILL_FITS,
    Infeasible,
    PlanWeakness,
    Preferences,
    TrainingPlan,
    assemble,
)
from tests.unit.coaching.plan_helpers import plan_problems, plan_targets, reviewed_test_library

scenarios("training_plan.feature")

_IDS = {
    "unforced errors": "unforced_errors",
    "serve faults": "serve_faults",
    "errors under pressure": "errors_under_pressure",
}


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


def _plan(ctx: dict[str, Any]) -> TrainingPlan:
    plan = ctx["plan"]
    assert isinstance(plan, TrainingPlan), plan
    return plan


def _assignments(ctx: dict[str, Any]) -> list[Any]:
    return [a for s in _plan(ctx).sessions for a in s.assignments]


@given("the reviewed test library with warm-ups, wall, ball-machine and 4-player drills")
def reviewed_library(ctx: dict[str, Any]) -> None:
    ctx["library"] = reviewed_test_library()


@given("the library has no warm-up drill")
def no_warm_up(ctx: dict[str, Any]) -> None:
    ctx["library"] = [d for d in ctx["library"] if "warm-up" not in d.skills]


@given(parsers.parse('the top weaknesses are "{a}" on "{ta}", "{b}" on "{tb}" and "{c}" on "{tc}"'))
def top_weaknesses(ctx: dict[str, Any], a: str, ta: str, b: str, tb: str, c: str, tc: str) -> None:
    ctx["weaknesses"] = [
        PlanWeakness(_IDS[name], target, rank)
        for rank, (name, target) in enumerate([(a, ta), (b, tb), (c, tc)], start=1)
    ]


@given(
    parsers.parse(
        "a solo player with a wall and {machine}, {minutes:d} minutes per session, "
        "{sessions:d} sessions a week"
    )
)
def solo_player(ctx: dict[str, Any], machine: str, minutes: int, sessions: int) -> None:
    equipment = {"wall"} | ({"ball_machine"} if machine == "a ball machine" else set())
    ctx["prefs"] = Preferences(
        minutes_per_session=minutes,
        sessions_per_week=sessions,
        players_available=1,
        equipment=frozenset(equipment),
        level="intermediate",
    )


@given(
    parsers.parse(
        "a player with {players:d} players, every setup, {minutes:d} minutes per session, "
        "{sessions:d} sessions a week and {weekly:d} minutes a week"
    )
)
def group_player(
    ctx: dict[str, Any], players: int, minutes: int, sessions: int, weekly: int
) -> None:
    ctx["prefs"] = Preferences(
        minutes_per_session=minutes,
        sessions_per_week=sessions,
        players_available=players,
        equipment=frozenset({"wall", "half_court", "full_court", "ball_machine", "partner_feeder"}),
        level="intermediate",
        weekly_minutes=weekly,
    )


@when("the plan is assembled")
def assembled(ctx: dict[str, Any]) -> None:
    ctx["plan"] = assemble(ctx["weaknesses"], ctx["prefs"], ctx["library"])
    assert plan_problems(ctx["plan"], ctx["prefs"], ctx["weaknesses"], ctx["library"]) == []


@when("the plan is assembled 3 times, each time from the library in a different order")
def assembled_three_times(ctx: dict[str, Any]) -> None:
    plans = []
    for seed in range(3):
        library = list(ctx["library"])
        random.Random(seed).shuffle(library)  # noqa: S311 - a fixed shuffle, not crypto
        plans.append(assemble(list(reversed(ctx["weaknesses"])), ctx["prefs"], library))
    ctx["plans"] = plans


@then(parsers.parse("the plan has {n:d} sessions over 2 weeks"))
def session_count(ctx: dict[str, Any], n: int) -> None:
    sessions = _plan(ctx).sessions
    assert len(sessions) == n
    assert {s.week for s in sessions} == {1, 2}


@then("no session uses a drill that needs a ball machine")
def no_ball_machine(ctx: dict[str, Any]) -> None:
    assert [a.drill.ref for a in _assignments(ctx) if "ball_machine" in a.drill.needs] == []


@then("some session uses a drill that needs a ball machine")
def some_ball_machine(ctx: dict[str, Any]) -> None:
    assert any("ball_machine" in a.drill.needs for a in _assignments(ctx))


@then(parsers.parse("no session uses a drill for more than {n:d} player"))
def players_at_most(ctx: dict[str, Any], n: int) -> None:
    assert [a.drill.ref for a in _assignments(ctx) if a.drill.players > n] == []


@then("only coach-reviewed or verified drills that are not deprecated are used")
def reviewed_only(ctx: dict[str, Any]) -> None:
    used = _assignments(ctx)
    assert used
    assert {a.drill.review_status for a in used} <= {"coach-reviewed", "verified"}
    assert not any(a.drill.deprecated for a in used)


@then(parsers.parse('the weakness "{name}" is named "{text}"'))
def weakness_named(ctx: dict[str, Any], name: str, text: str) -> None:
    unfitted = {u.weakness_id: u for u in _plan(ctx).unfitted}
    assert _IDS[name] in unfitted
    assert unfitted[_IDS[name]].text == text == NO_DRILL_FITS


@then(parsers.parse('no session has a drill for "{name}"'))
def no_drill_for(ctx: dict[str, Any], name: str) -> None:
    assert [a.drill.ref for a in _assignments(ctx) if a.weakness_id == _IDS[name]] == []
    target = next(w.target for w in ctx["weaknesses"] if w.id == _IDS[name])
    assert not any(target in plan_targets(a.drill) for a in _assignments(ctx))


@then(parsers.parse("every session lasts at most {minutes:d} minutes"))
def session_minutes(ctx: dict[str, Any], minutes: int) -> None:
    totals = [s.total_minutes for s in _plan(ctx).sessions]
    assert max(totals) <= minutes
    assert min(totals) > 0


@then("every drill can be done by one player without a ball machine")
def solo_drills(ctx: dict[str, Any]) -> None:
    used = _assignments(ctx)
    assert all(a.drill.players == 1 and "ball_machine" not in a.drill.needs for a in used)


@then(parsers.parse("each week's sessions total at most {minutes:d} minutes"))
def weekly_minutes(ctx: dict[str, Any], minutes: int) -> None:
    for week in (1, 2):
        total = sum(s.total_minutes for s in _plan(ctx).sessions if s.week == week)
        assert 0 < total <= minutes


@then(parsers.parse('the first drill of every session is a "{skill}" drill of 5 to 10 minutes'))
def warm_up_first(ctx: dict[str, Any], skill: str) -> None:
    for s in _plan(ctx).sessions:
        first = s.assignments[0]
        assert skill in first.drill.skills
        assert 5 <= first.minutes <= 10
        assert first.weakness_id is None


@then(parsers.parse('no other drill of a session is a "{skill}" drill'))
def one_warm_up(ctx: dict[str, Any], skill: str) -> None:
    for s in _plan(ctx).sessions:
        assert not any(skill in a.drill.skills for a in s.assignments[1:])
        assert len(s.assignments) >= 2


@then(parsers.parse("no drill is given more than {minutes:d} minutes"))
def drill_cap(ctx: dict[str, Any], minutes: int) -> None:
    given = [a.minutes for a in _assignments(ctx)]
    assert max(given) == minutes


@then(parsers.parse('no plan is made, with the reason "{reason}"'))
def no_plan(ctx: dict[str, Any], reason: str) -> None:
    assert ctx["plan"] == Infeasible(reason)


@then("the 3 plans are identical and have the same content digest")
def identical(ctx: dict[str, Any]) -> None:
    first, *rest = ctx["plans"]
    assert isinstance(first, TrainingPlan)
    for other in rest:
        assert isinstance(other, TrainingPlan)
        assert other.content() == first.content()
        assert other.content_digest() == first.content_digest()
