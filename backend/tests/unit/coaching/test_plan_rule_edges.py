"""QA-VERIFY04R3-07 (G04-11 c): the plan rules at their edges (ST-056, ST-062; QD-PL-01..03;
api-sprint-04 §2.1; coaching-plan §3, §5, §7).

Each test pins one boundary or one message the existing suites left open: which preference is
named, the inclusive ends of the minute ranges, the week totals of QD-PL-01, which slot a command
names when it refuses, and how a swap sizes the new drill (its own maximum, the 40% cap and the
room left in the session). Negative cases first.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

import pytest

from racket.coaching.plan.domain import (
    Drill,
    InvalidPreferences,
    NoAlternative,
    PlanInvariantBroken,
    Preferences,
    Session,
    SessionDone,
    TrainingPlan,
    Unfitted,
    violations,
)
from racket.coaching.plan.domain.model import citable_targets, warm_up_minutes
from racket.coaching.plan.repository import from_rows, to_rows
from racket.coaching.plan.scope import ScopeMemo
from tests.unit.coaching.plan_helpers import TOP_3, drill, solo_wall
from tests.unit.coaching.test_plan_follow_through import CITED, DINKS, LIB, SERVE, WARM, a, plan

pytestmark = [pytest.mark.unit, pytest.mark.coaching]

AT = datetime(2026, 10, 18, 9, 30, tzinfo=UTC)
IVY = uuid.UUID(int=1)
WALL_WARM_UP = LIB["pb.test.wall-warm-up"]  # a second solo warm-up, 5-8 minutes
VALID = {
    "minutes_per_session": 30,
    "sessions_per_week": 3,
    "players_available": 1,
    "equipment": frozenset({"wall"}),
    "level": "intermediate",
}


def custom_plan(minutes: int, *slots: tuple[Drill, int]) -> TrainingPlan:
    """A solo-wall plan of ``minutes`` per session, every session the warm-up then ``slots``
    (weakness drills of the top two weaknesses, in that order)."""
    weakness = ("unforced_errors", "serve_faults")
    rows = (a(1, WARM, 10, None), *(a(n + 2, d, m, weakness[n]) for n, (d, m) in enumerate(slots)))
    return TrainingPlan(
        preferences=solo_wall(minutes=minutes),
        weaknesses=TOP_3,
        unfitted=(Unfitted("errors_under_pressure"),),
        sessions=tuple(Session(w, i, minutes, rows) for w in (1, 2) for i in (1, 2, 3)),
    )


# ------------------------------------------------------------------ preferences
@pytest.mark.parametrize(
    ("change", "named"),
    [
        ({"minutes_per_session": 14}, "minutes_per_session"),
        ({"sessions_per_week": 8}, "sessions_per_week"),
        ({"weekly_minutes": 44}, "weekly_minutes"),  # < 3 sessions x 15 minutes
        ({"players_available": 5}, "players_available"),
        ({"equipment": frozenset({"trampoline"})}, "equipment"),
        ({"level": "pro"}, "level"),
    ],
)
def test_each_invalid_preference_is_named(change: dict[str, object], named: str) -> None:
    with pytest.raises(InvalidPreferences) as refused:
        Preferences(**{**VALID, **change})  # type: ignore[arg-type]
    assert str(refused.value) == named


def test_every_invalid_preference_is_named_in_one_message() -> None:
    with pytest.raises(InvalidPreferences) as refused:
        Preferences(**{**VALID, "minutes_per_session": 181, "level": "pro"})  # type: ignore[arg-type]
    assert str(refused.value) == "minutes_per_session, level"


def test_a_broken_plan_names_every_violation() -> None:
    assert str(PlanInvariantBroken(["rule a", "rule b"])) == "rule a; rule b"


# ------------------------------------------------------------------ drills and minutes
def test_a_warm_up_capped_at_exactly_its_minimum_still_fits() -> None:
    assert warm_up_minutes(WARM, 5) == 5
    assert warm_up_minutes(WARM, 4) is None


def test_an_an_07_drill_cites_its_share_target() -> None:
    faults = drill("pb.test.faults", targets=("AN-05", "AN-07"), skills=("share:fault",))
    assert citable_targets(faults) == ["AN-05", "AN-07:fault"]


# ------------------------------------------------------------------ plan rules
def _session(week: int, index: int) -> Session:
    return Session(week, index, 30, (a(1, WARM, 10, None), a(2, DINKS, 12, "unforced_errors")))


def test_qd_pl_01_names_the_week_over_its_weekly_total() -> None:
    sessions = [_session(1, i) for i in (1, 2, 3, 4, 5)] + [_session(2, i) for i in (1, 2, 3)]
    sessions += [_session(3, i) for i in (1, 2, 3, 4, 5)]  # weeks after week 2 are not counted
    found = violations(solo_wall(minutes=30), TOP_3[:1], (), sessions)
    assert [v for v in found if v.startswith("QD-PL-01: week")] == [
        "QD-PL-01: week 1 totals 110 > 90 minutes"
    ]


def test_an_empty_session_does_not_start_with_a_warm_up() -> None:
    found = violations(
        solo_wall(sessions=1), (), (), [Session(1, 1, 30, ()), Session(2, 1, 30, ())]
    )
    assert found == [
        "QD-PL-03: week 1 session 1 does not start with a warm-up",
        "QD-PL-03: week 2 session 1 does not start with a warm-up",
    ]


def test_a_rule_broken_by_one_drill_names_its_slot() -> None:
    over_cap = Session(1, 1, 30, (a(1, WARM, 10, None), a(2, DINKS, 13, "unforced_errors")))
    found = violations(solo_wall(sessions=1), TOP_3[:1], (), [over_cap, _session(2, 1)])
    assert found == ["QD-PL-03: week 1 session 1 drill 2 pb.test.wall-dinks@1 13 min > 40% cap 12"]


def test_a_five_minute_warm_up_keeps_the_rules() -> None:
    short = Session(1, 1, 30, (a(1, WARM, 5, None), a(2, DINKS, 12, "unforced_errors")))
    assert violations(solo_wall(sessions=1), TOP_3[:1], (), [short, _session(2, 1)]) == []


# ------------------------------------------------------------------ replace_drill
def test_replace_drill_names_the_slot_it_cannot_find() -> None:
    p = plan()
    with pytest.raises(KeyError, match="no assignment at week 1 session 1 position 4"):
        p.replace_drill(week=1, index=1, position=4, drill=SERVE, minutes=8)
    assert p.version == 1


def test_replace_drill_reaches_the_first_and_the_last_position() -> None:
    p = plan()
    p.replace_drill(week=1, index=1, position=1, drill=WALL_WARM_UP, minutes=8)
    serve_alt = drill("pb.test.serve-alt", targets=("AN-05",), minutes=(5, 10))
    p.replace_drill(week=1, index=1, position=3, drill=serve_alt, minutes=8)
    first = p.sessions[0].assignments
    assert [x.drill.ref for x in first] == [
        "pb.test.wall-warm-up@1",
        "pb.test.wall-dinks@1",
        "pb.test.serve-alt@1",
    ]
    assert [x.weakness_id for x in first] == [None, "unforced_errors", "serve_faults"]
    assert len(p.sessions) == 6
    assert p.sessions[1] == plan().sessions[1]
    assert p.version == 3


# ------------------------------------------------------------------ swap refusals name the slot
def test_swap_refusals_name_the_slot_or_the_drill() -> None:
    p = plan()
    with pytest.raises(KeyError, match="no session at week 3 session 1"):
        p.swap(week=3, index=1, position=2, library=[], cited=CITED)
    with pytest.raises(KeyError, match="no assignment at week 1 session 1 position 0"):
        p.swap(week=1, index=1, position=0, library=[], cited=CITED)
    with pytest.raises(NoAlternative, match=re.escape("pb.test.wall-dinks@1 cites nothing")):
        p.swap(week=1, index=1, position=2, library=[], cited=frozenset())
    with pytest.raises(
        NoAlternative, match=re.escape("no other drill for pb.test.wall-dinks@1 cites AN-04")
    ):
        p.swap(week=1, index=1, position=2, library=[], cited=CITED)
    p.mark_done(week=1, index=2, at=AT)
    with pytest.raises(SessionDone, match="week 1 session 2 is done"):
        p.swap(week=1, index=2, position=2, library=[], cited=CITED)


# ------------------------------------------------------------------ swap sizing
def _swap(p: TrainingPlan, *library: Drill) -> int:
    p.swap(week=1, index=1, position=2, library=list(library), cited=CITED)
    return p.sessions[0].assignments[1].minutes


def test_a_swap_gives_no_more_than_the_new_drill_s_maximum() -> None:
    p = custom_plan(30, (DINKS, 12), (SERVE, 8))
    assert _swap(p, drill("pb.test.b-short", needs=("wall",), minutes=(8, 10))) == 10


def test_a_swap_gives_no_more_than_the_40_percent_cap() -> None:
    p = custom_plan(40, (DINKS, 12), (SERVE, 8))  # cap 16, room 22
    assert _swap(p, drill("pb.test.b-long", needs=("wall",), minutes=(8, 20))) == 16


def test_a_swap_gives_no_more_than_the_room_left_in_the_session() -> None:
    p = custom_plan(30, (DINKS, 10), (SERVE, 10))  # cap 12, room 10
    assert _swap(p, drill("pb.test.b-mid", needs=("wall",), minutes=(8, 15))) == 10


def test_a_swap_takes_a_drill_whose_minimum_is_exactly_the_room() -> None:
    p = custom_plan(30, (DINKS, 12), (SERVE, 8))  # cap 12, room 12
    assert _swap(p, drill("pb.test.b-exact", needs=("wall",), minutes=(12, 15))) == 12


def test_a_drill_too_long_for_the_room_is_passed_over_for_the_next_one() -> None:
    p = custom_plan(30, (DINKS, 12), (SERVE, 8))
    too_long = drill("pb.test.a-too-long", needs=("wall",), minutes=(13, 20))
    fits = drill("pb.test.b-fits", needs=("wall",), minutes=(8, 10))
    assert _swap(p, too_long, fits) == 10
    assert p.sessions[0].assignments[1].drill is fits


# ------------------------------------------------------------------ rows and the scope memo
def test_rows_keep_the_library_version_and_the_unfitted_reason() -> None:
    p = TrainingPlan(
        preferences=solo_wall(),
        weaknesses=TOP_3,
        unfitted=(Unfitted("errors_under_pressure", "no_ball_machine"),),
        sessions=plan().sessions,
        library_version="sha256:lib",
    )
    rows = to_rows(p, plan_id=uuid.uuid4(), owner_id=IVY)
    assert rows.plan["limited_data"] is False
    back = from_rows(rows, {d.ref: d for d in LIB.values()})
    assert back.library_version == "sha256:lib"
    assert back.unfitted == (Unfitted("errors_under_pressure", "no_ball_machine"),)


def test_an_assignment_outside_the_plan_s_sessions_is_named() -> None:
    rows = to_rows(plan(), plan_id=uuid.uuid4(), owner_id=IVY)
    stray = {**rows.assignments[0], "id": uuid.UUID(int=99), "session_id": uuid.uuid4()}
    rows.assignments.append(stray)
    with pytest.raises(ValueError, match=f"assignment {uuid.UUID(int=99)} is not in a session"):
        from_rows(rows, {d.ref: d for d in LIB.values()})


def test_a_scope_memo_needs_room_for_one_owner_and_one_is_enough() -> None:
    with pytest.raises(ValueError, match=r"^capacity must be at least 1$"):
        ScopeMemo[str](capacity=0)
    memo = ScopeMemo[str](capacity=1)
    memo.put(IVY, (), "facts")
    assert memo.get(IVY, ()) == "facts"
    assert len(memo) == 1
