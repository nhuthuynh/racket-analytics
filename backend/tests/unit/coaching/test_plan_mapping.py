"""Unit tests for the TrainingPlan <-> rows mapping (ST-061a; coaching-plan §9). No database.

``to_rows`` turns the aggregate into the row dicts of migration 0018 (owner on every row);
``from_rows`` rebuilds the aggregate from them, so the root guards its invariants again on load.
Negative cases first: a drill reference the library does not hold, and rows that would break a
plan rule, never become a plan.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import replace

import pytest

from racket.coaching.plan.domain import (
    Drill,
    PlanInvariantBroken,
    Preferences,
    TrainingPlan,
    assemble,
)
from racket.coaching.plan.repository import PlanRows, UnknownDrill, from_rows, to_rows
from tests.unit.coaching.plan_helpers import TOP_3, reviewed_test_library, solo_wall

pytestmark = pytest.mark.unit

PLAN_ID = uuid.UUID(int=1)
OWNER = uuid.UUID(int=2)
GROUP = Preferences(
    minutes_per_session=60,
    sessions_per_week=3,
    players_available=4,
    equipment=frozenset({"wall", "half_court", "full_court", "ball_machine", "partner_feeder"}),
    level="intermediate",
    weekly_minutes=150,
)


def _plan(prefs: Preferences) -> TrainingPlan:
    plan = assemble(list(TOP_3), prefs, reviewed_test_library())
    assert isinstance(plan, TrainingPlan), plan
    return plan


def _library() -> dict[str, Drill]:
    return {d.ref: d for d in reviewed_test_library()}


def _ids() -> Callable[[], uuid.UUID]:
    counter = iter(range(100, 10_000))
    return lambda: uuid.UUID(int=next(counter))


def test_a_drill_the_library_does_not_hold_is_refused() -> None:
    rows = to_rows(_plan(solo_wall()), plan_id=PLAN_ID, owner_id=OWNER, new_id=_ids())
    library = _library()
    gone = rows.assignments[0]["drill_ref"]
    del library[gone]
    with pytest.raises(UnknownDrill, match=gone):
        from_rows(rows, library)


def test_rows_that_break_a_plan_rule_are_refused_on_load() -> None:
    rows = to_rows(_plan(solo_wall()), plan_id=PLAN_ID, owner_id=OWNER, new_id=_ids())
    first = dict(rows.assignments[0], minutes=29)  # a 29-minute warm-up breaks QD-PL-01/03
    broken = replace(rows, assignments=[first, *rows.assignments[1:]])
    with pytest.raises(PlanInvariantBroken):
        from_rows(broken, _library())


def test_rows_of_another_plan_are_refused() -> None:
    rows = to_rows(_plan(solo_wall()), plan_id=PLAN_ID, owner_id=OWNER, new_id=_ids())
    stray = dict(rows.sessions[0], plan_id=uuid.UUID(int=99))
    with pytest.raises(ValueError, match="plan"):
        from_rows(replace(rows, sessions=[stray, *rows.sessions[1:]]), _library())


# Fixed ids: str(Preferences) embeds a frozenset whose order follows PYTHONHASHSEED,
# so xdist workers would collect different ids and abort the run.
@pytest.mark.parametrize(
    "prefs",
    [solo_wall(), solo_wall(20, 2), GROUP],
    ids=["solo-wall-30min-3x", "solo-wall-20min-2x", "group-of-4-60min-3x"],
)
def test_rows_map_back_to_an_identical_plan(prefs: Preferences) -> None:
    plan = _plan(prefs)
    back = from_rows(to_rows(plan, plan_id=PLAN_ID, owner_id=OWNER, new_id=_ids()), _library())
    assert back.preferences == plan.preferences  # weekly_minutes None stays None
    assert back.weaknesses == plan.weaknesses
    assert back.unfitted == plan.unfitted
    assert back.sessions == plan.sessions
    assert (back.library_version, back.version) == (plan.library_version, plan.version)
    assert back.content_digest() == plan.content_digest()


def test_a_changed_version_maps_back() -> None:
    plan = _plan(solo_wall())
    plan.version = 7
    back = from_rows(to_rows(plan, plan_id=PLAN_ID, owner_id=OWNER, new_id=_ids()), _library())
    assert back.version == 7


def test_every_row_names_the_owner_and_the_ids_are_unique() -> None:
    plan = _plan(solo_wall())
    rows = to_rows(plan, plan_id=PLAN_ID, owner_id=OWNER, new_id=_ids())
    assert isinstance(rows, PlanRows)
    assert rows.plan["id"] == PLAN_ID
    every = [rows.plan, *rows.sessions, *rows.assignments]
    assert {r["owner_id"] for r in every} == {OWNER}
    ids = [r["id"] for r in every]
    assert len(set(ids)) == len(ids)
    assert len(rows.sessions) == len(plan.sessions)
    assert len(rows.assignments) == sum(len(s.assignments) for s in plan.sessions)
    session_ids = {s["id"] for s in rows.sessions}
    assert {a["session_id"] for a in rows.assignments} == session_ids
    assert rows.plan["content_digest"] == plan.content_digest()
    assert rows.plan["stale"] is False


def test_preferences_are_stored_as_plain_json() -> None:
    rows = to_rows(_plan(GROUP), plan_id=PLAN_ID, owner_id=OWNER, new_id=_ids())
    assert rows.plan["preferences"] == {
        "minutes_per_session": 60,
        "sessions_per_week": 3,
        "weekly_minutes": 150,
        "players_available": 4,
        "equipment": ["ball_machine", "full_court", "half_court", "partner_feeder", "wall"],
        "level": "intermediate",
    }
    solo = to_rows(_plan(solo_wall()), plan_id=PLAN_ID, owner_id=OWNER, new_id=_ids())
    assert solo.plan["preferences"]["weekly_minutes"] is None
