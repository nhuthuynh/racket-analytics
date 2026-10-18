"""ST-062 (FR-124; coaching-plan §5, §7): the ``TrainingPlan`` follow-through commands.

``mark_done`` / ``undo_done`` change one session's done state. Every accepted change returns its
event and adds 1 to ``version``; a no-op returns None and changes nothing; a refusal raises and
leaves the plan exactly as it was. The "Not for me" swap is ST-062-part2.

Negative cases first: an unknown session; then the accepted commands and the rows mapping.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from racket.coaching.plan.domain import (
    Drill,
    DrillAssignment,
    Session,
    SessionDoneUndone,
    SessionMarkedDone,
    TrainingPlan,
    Unfitted,
)
from racket.coaching.plan.repository import from_rows, to_rows
from tests.unit.coaching.plan_helpers import TOP_3, reviewed_test_library, solo_wall

pytestmark = pytest.mark.unit

LIB = {d.id: d for d in reviewed_test_library()}
WARM = LIB["pb.test.shadow-warm-up"]
DINKS = LIB["pb.test.wall-dinks"]
SERVE = LIB["pb.test.serve-target"]
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
    return (p.content(), p.version, p.sessions)


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
def test_done_state_survives_the_rows_round_trip() -> None:
    p = plan()
    p.mark_done(week=2, index=3, at=AT)
    rows = to_rows(p, plan_id=uuid.UUID(int=1), owner_id=uuid.UUID(int=2))
    assert [s["done_at"] for s in rows.sessions] == [None] * 5 + [AT]
    back = from_rows(rows, {d.ref: d for d in reviewed_test_library()})
    assert snapshot(back) == snapshot(p)
