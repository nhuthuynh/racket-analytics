"""ST-062 (FR-124; coaching-plan §5, §7): the ``TrainingPlan`` follow-through commands.

``mark_done`` / ``undo_done`` change one session's done state; ``swap`` ("Not for me") replaces
one assignment's drill with the first other eligible drill (``(id, version)`` order) that cites
the same plan target and keeps every QD-PL-01..03 rule with the session's other assignments,
then excludes the swapped-out drill from later swaps in that plan. Every accepted change returns
its event and adds 1 to ``version``; a no-op returns None and changes nothing; a refusal raises
and leaves the plan exactly as it was.

Negative cases first: no alternative, a done session, an unknown slot; then the drills a swap
must never pick; then the accepted commands and the rows mapping (done, reason, excluded drills).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from racket.coaching.plan.domain import (
    Drill,
    DrillAssignment,
    DrillSwapped,
    NoAlternative,
    PlanWeakness,
    Session,
    SessionDone,
    SessionDoneUndone,
    SessionMarkedDone,
    TrainingPlan,
    Unfitted,
)
from racket.coaching.plan.repository import from_rows, to_rows
from tests.unit.coaching.plan_helpers import TOP_3, drill, reviewed_test_library, solo_wall, warm_up

pytestmark = pytest.mark.unit

LIB = {d.id: d for d in reviewed_test_library()}
WARM = LIB["pb.test.shadow-warm-up"]
DINKS = LIB["pb.test.wall-dinks"]
SERVE = LIB["pb.test.serve-target"]
# AN-04 drills for a solo player with a wall, named so (id, version) order is drives < volleys
DRIVES = drill("pb.test.a-wall-drives", needs=("wall",), minutes=(8, 15))
VOLLEYS = drill("pb.test.wall-volleys", needs=("wall",), minutes=(8, 12))
CITED = frozenset({"AN-01", "AN-02", "AN-04", "AN-05", "AN-07:fault", "AN-07:forced-error"})
AT = datetime(2026, 10, 18, 9, 30, tzinfo=UTC)


def a(position: int, d: Drill, minutes: int, weakness: str | None) -> DrillAssignment:
    return DrillAssignment(position=position, drill=d, minutes=minutes, weakness_id=weakness)


def session(week: int, index: int) -> Session:
    return Session(
        week=week,
        index=index,
        minutes_budget=30,
        assignments=(
            a(1, WARM, 10, None),
            a(2, DINKS, 12, "unforced_errors"),
            a(3, SERVE, 8, "serve_faults"),
        ),
    )


def plan() -> TrainingPlan:
    return TrainingPlan(
        preferences=solo_wall(),
        weaknesses=TOP_3,
        unfitted=(Unfitted("errors_under_pressure"),),
        sessions=tuple(session(w, i) for w in (1, 2) for i in (1, 2, 3)),
    )


def snapshot(p: TrainingPlan) -> tuple[object, ...]:
    return (p.content(), p.version, p.excluded_drills, p.sessions)


def swap(p: TrainingPlan, library: list[Drill], position: int = 2, **kw: object) -> DrillSwapped:
    return p.swap(week=1, index=1, position=position, library=library, cited=CITED, **kw)  # type: ignore[arg-type]


# ------------------------------------------------------------------ swap refusals (negative first)
def test_swap_with_no_alternative_raises_and_leaves_the_plan_unchanged() -> None:
    p = plan()
    before = snapshot(p)
    with pytest.raises(NoAlternative):
        swap(p, [WARM, DINKS, SERVE])  # DINKS is the one AN-04 drill for a solo wall player
    assert snapshot(p) == before
    assert p.excluded_drills == frozenset()


def test_swap_in_a_done_session_is_refused_before_any_change() -> None:
    p = plan()
    p.mark_done(week=1, index=1, at=AT)
    before = snapshot(p)
    with pytest.raises(SessionDone):
        swap(p, [WARM, DINKS, SERVE, DRIVES])
    assert snapshot(p) == before


def test_swap_of_an_unknown_assignment_is_refused() -> None:
    p = plan()
    with pytest.raises(KeyError):
        p.swap(week=3, index=1, position=2, library=[DRIVES], cited=CITED)
    with pytest.raises(KeyError):
        p.swap(week=1, index=1, position=4, library=[DRIVES], cited=CITED)
    assert p.version == 1


@pytest.mark.parametrize(
    "never",
    [
        drill("pb.test.machine-only", needs=("ball_machine",)),  # QD-PL-02 setup
        drill("pb.test.pair-only", players=2),  # QD-PL-02 players
        drill("pb.test.draft", needs=("wall",), status="draft"),  # QD-PL-02 not reviewed
        drill("pb.test.retired", deprecated_by="pb.test.wall-dinks@1"),  # QD-PL-02 deprecated
        drill("pb.test.pros-only", levels=("advanced", "advanced")),  # QD-PL-02 level
        drill("pb.test.serve-only", targets=("AN-05",)),  # another metric
        drill("pb.test.long-only", minutes=(13, 20)),  # QD-PL-03 over the 40% cap
        warm_up("pb.test.another-warm-up"),  # a second warm-up (QD-PL-03)
        SERVE,  # already in the session
    ],
    ids=lambda d: d.id,
)
def test_swap_never_picks_a_drill_that_breaks_a_rule(never: Drill) -> None:
    p = plan()
    before = snapshot(p)
    with pytest.raises(NoAlternative):
        swap(p, [WARM, DINKS, SERVE, never])
    assert snapshot(p) == before


def test_swap_never_picks_a_drill_whose_target_has_no_citation() -> None:
    p = plan()
    serve_alt = drill("pb.test.serve-alt", targets=("AN-05",), minutes=(5, 10))
    with pytest.raises(NoAlternative):
        p.swap(
            week=1, index=1, position=3, library=[serve_alt], cited=CITED - {"AN-05"}
        )
    assert p.version == 1


# ------------------------------------------------------------------ swap accepted
def test_swap_picks_the_first_eligible_drill_and_keeps_the_weakness() -> None:
    p = plan()
    event = swap(p, [WARM, DINKS, SERVE, VOLLEYS, DRIVES], reason="Too hard on my wrist")
    x = p.sessions[0].assignments[1]
    assert (x.drill, x.minutes, x.weakness_id) == (DRIVES, 12, "unforced_errors")
    assert x.reason_not_for_me == "Too hard on my wrist"
    assert p.version == 2
    assert event == DrillSwapped(
        week=1,
        index=1,
        position=2,
        from_drill=DINKS.ref,
        to_drill=DRIVES.ref,
        target="AN-04",
        reason_given=True,
        version=2,
    )


def test_swap_changes_only_the_one_assignment() -> None:
    p = plan()
    swap(p, [DINKS, DRIVES])
    assert [s.assignments[1].drill for s in p.sessions] == [DRIVES] + [DINKS] * 5
    assert p.sessions[0].assignments[0] == a(1, WARM, 10, None)
    assert p.sessions[0].assignments[2] == a(3, SERVE, 8, "serve_faults")


def test_swapped_out_drill_is_not_offered_again_in_that_plan() -> None:
    p = plan()
    library = [WARM, DINKS, SERVE, VOLLEYS, DRIVES]
    assert swap(p, library).to_drill == DRIVES.ref
    assert swap(p, library).to_drill == VOLLEYS.ref
    before = snapshot(p)
    with pytest.raises(NoAlternative):  # DINKS and DRIVES were swapped out
        swap(p, library)
    assert snapshot(p) == before
    assert p.excluded_drills == frozenset({DINKS.ref, DRIVES.ref})
    other = p.swap(week=1, index=2, position=2, library=library, cited=CITED)
    assert other.to_drill == VOLLEYS.ref  # DRIVES is excluded plan-wide, not just in session 1


def test_swap_minutes_fit_the_room_left_in_the_session() -> None:
    p = plan()
    swap(p, [DINKS, VOLLEYS])
    assert p.sessions[0].assignments[1].minutes == 12  # min(duration_max 12, cap 12, room 12)
    assert p.sessions[0].total_minutes == 30


def test_swap_of_a_warm_up_picks_another_warm_up_with_the_same_cited_target() -> None:
    p = plan()
    serve_warm = warm_up("pb.test.a-serve-warm-up", targets=("AN-05",))
    wall_warm = LIB["pb.test.wall-warm-up"]
    event = swap(p, [DRIVES, serve_warm, WARM, wall_warm], position=1)
    x = p.sessions[0].assignments[0]
    assert (x.drill, x.minutes, x.weakness_id) == (wall_warm, 8, None)
    assert (event.target, event.reason_given) == ("AN-04", False)


def test_swap_without_a_reason_stores_none() -> None:
    p = plan()
    swap(p, [DRIVES])
    assert p.sessions[0].assignments[1].reason_not_for_me is None


def test_swap_does_not_change_the_plan_weaknesses_or_preferences() -> None:
    p = plan()
    swap(p, [DRIVES])
    assert (p.weaknesses, p.preferences, p.unfitted) == (
        TOP_3,
        solo_wall(),
        (Unfitted("errors_under_pressure"),),
    )
    assert all(isinstance(w, PlanWeakness) for w in p.weaknesses)


# ------------------------------------------------------------------ done and undo
def test_mark_done_of_an_unknown_session_is_refused() -> None:
    p = plan()
    with pytest.raises(KeyError):
        p.mark_done(week=1, index=4, at=AT)
    with pytest.raises(KeyError):
        p.undo_done(week=3, index=1)
    assert p.version == 1


def test_mark_done_sets_the_time_once_and_bumps_the_version_once() -> None:
    p = plan()
    assert p.mark_done(week=1, index=2, at=AT) == SessionMarkedDone(week=1, index=2, version=2)
    assert p.sessions[1].done_at == AT
    later = datetime(2026, 10, 19, tzinfo=UTC)
    assert p.mark_done(week=1, index=2, at=later) is None  # done twice: a no-op
    assert (p.sessions[1].done_at, p.version) == (AT, 2)
    assert [s.done_at for s in p.sessions if s.index != 2 or s.week != 1] == [None] * 5


def test_undo_clears_done_and_undo_when_not_done_is_a_no_op() -> None:
    p = plan()
    assert p.undo_done(week=2, index=1) is None
    assert p.version == 1
    p.mark_done(week=2, index=1, at=AT)
    assert p.undo_done(week=2, index=1) == SessionDoneUndone(week=2, index=1, version=3)
    assert (p.sessions[3].done_at, p.version) == (None, 3)


def test_done_state_is_not_plan_content() -> None:
    p = plan()
    digest = p.content_digest()
    p.mark_done(week=1, index=1, at=AT)
    assert p.content_digest() == digest


# ------------------------------------------------------------------ rows mapping
def test_done_reason_and_excluded_drills_survive_the_rows_round_trip() -> None:
    p = plan()
    p.mark_done(week=2, index=3, at=AT)
    swap(p, [DINKS, DRIVES], reason="No wall nearby")
    rows = to_rows(p, plan_id=uuid.UUID(int=1), owner_id=uuid.UUID(int=2))
    assert rows.plan["excluded_drills"] == [DINKS.ref]
    assert [s["done_at"] for s in rows.sessions] == [None] * 5 + [AT]
    assert [r["reason_not_for_me"] for r in rows.assignments][:3] == [None, "No wall nearby", None]
    library = {d.ref: d for d in [*reviewed_test_library(), DRIVES]}
    back = from_rows(rows, library)
    assert snapshot(back) == snapshot(p)
