"""IT-04-02a (ST-056; FR-121; QD-PL-01..03): plan assembly over the real ``content/drills`` library.

Boundary: the drill files on disk, checked by the drills module (``racket-drill-lint`` rules and
lock, the ST-053 seam) and translated by ``Drill.from_document``, then ``assemble``.

* The library on disk is lint-clean, and every drill version in it translates with its fields.
* Over a grid of preferences x weakness sets, assembly from the real library never breaks a plan
  rule (independent checker ``plan_problems``) and uses only coach-reviewed/verified,
  non-deprecated drills. While the library holds no reviewed warm-up (the starter drills arrive
  with ST-058a..c) that means "no_plan_fits"; the assertion is derived from the files, so it holds
  unchanged once reviewed drills land.
* Positive control: the same real drills, marked reviewed in memory and given one test warm-up,
  are placed; the 4-player full-court drill only when the player has 4 players and a full court,
  and a deprecated version never.
"""

from __future__ import annotations

import itertools
import json
from typing import Any

import pytest

from racket.coaching.drills.lint import lint_path
from racket.coaching.plan.domain import (
    Drill,
    Infeasible,
    PlanWeakness,
    Preferences,
    TrainingPlan,
    assemble,
)
from racket.sports.pickleball.metrics import load_dictionary
from tests.support.paths import REPO
from tests.unit.coaching.plan_helpers import plan_problems, warm_up

pytestmark = pytest.mark.integration

LIBRARY = REPO / "content" / "drills"
REVIEWED = ("coach-reviewed", "verified")


def _documents() -> list[dict[str, Any]]:
    files = sorted(p for p in LIBRARY.rglob("*.json") if p.name != "schema.json")
    return [json.loads(p.read_text(encoding="utf-8")) for p in files]


def _library() -> list[Drill]:
    return [Drill.from_document(doc) for doc in _documents()]


def _prefs(players: int, equipment: tuple[str, ...], minutes: int, sessions: int) -> Preferences:
    return Preferences(
        minutes_per_session=minutes,
        sessions_per_week=sessions,
        players_available=players,
        equipment=frozenset(equipment),
        level="intermediate",
    )


SETUPS = [
    (1, ()),
    (1, ("wall",)),
    (2, ("half_court",)),
    (4, ("full_court", "half_court", "wall", "ball_machine", "partner_feeder")),
]
TIMES = [(15, 1), (30, 3), (60, 5)]
WEAKNESS_SETS = [
    (PlanWeakness("unforced_errors", "AN-04", 1),),
    (
        PlanWeakness("serve_faults", "AN-05", 1),
        PlanWeakness("unforced_errors", "AN-04", 2),
        PlanWeakness("errors_under_pressure", "AN-07:forced-error", 3),
    ),
]
GRID = list(itertools.product(SETUPS, TIMES, range(len(WEAKNESS_SETS))))


def test_it_04_02a_the_real_library_is_lint_clean_and_translates() -> None:
    metrics = frozenset(entry.id for entry in load_dictionary().entries)
    assert lint_path(LIBRARY, metrics) == []
    docs = _documents()
    assert docs, f"no drill files under {LIBRARY}"
    for doc, d in zip(docs, _library(), strict=True):
        assert d.ref == f"{doc['id']}@{doc['version']}"
        assert (d.players, d.needs) == (doc["players"], frozenset(doc["needs"]))
        assert (d.duration_min, d.duration_max) == (doc["duration_min"], doc["duration_max"])
        assert d.target_metrics == tuple(doc["target_metrics"])
        assert d.review_status == doc["review_status"]
        assert d.deprecated == ("deprecated_by" in doc)


@pytest.mark.parametrize(("setup", "time", "ws"), GRID)
def test_it_04_02a_assembly_over_the_real_library_keeps_every_rule(
    setup: tuple[int, tuple[str, ...]], time: tuple[int, int], ws: int
) -> None:
    library = _library()
    prefs = _prefs(setup[0], setup[1], *time)
    weaknesses = WEAKNESS_SETS[ws]
    result = assemble(weaknesses, prefs, library)
    assert plan_problems(result, prefs, weaknesses, library) == []
    reviewed_warm_up = any(d.is_warm_up and d.is_reviewed and not d.deprecated for d in library)
    if not reviewed_warm_up:
        assert result == Infeasible("no_plan_fits")
    if isinstance(result, TrainingPlan):
        used = [x.drill for s in result.sessions for x in s.assignments]
        assert all(d.review_status in REVIEWED and not d.deprecated for d in used)


def _reviewed_copy() -> list[Drill]:
    docs = [{**doc, "review_status": "coach-reviewed"} for doc in _documents()]
    return [Drill.from_document(doc) for doc in docs] + [warm_up("pb.test.shadow-warm-up")]


@pytest.mark.parametrize(("setup", "time", "ws"), GRID)
def test_it_04_02a_reviewed_copy_of_the_real_library_is_placed_within_the_rules(
    setup: tuple[int, tuple[str, ...]], time: tuple[int, int], ws: int
) -> None:
    library = _reviewed_copy()
    prefs = _prefs(setup[0], setup[1], *time)
    weaknesses = WEAKNESS_SETS[ws]
    result = assemble(weaknesses, prefs, library)
    assert plan_problems(result, prefs, weaknesses, library) == []
    if "half_court" not in setup[1] or time[0] < 30:
        return  # no real drill fits a court-less setup or a 6-minute cap; plan_problems checked it
    assert isinstance(result, TrainingPlan)
    used = {x.drill.ref for s in result.sessions for x in s.assignments}
    assert not used & {"pb.fixture.drop-ladder@1", "pb.fixture.drop-ladder@2"}  # deprecated
    if setup[0] < 4 or "full_court" not in setup[1]:
        assert "pb.fixture.drop-and-advance@1" not in used
    assert used & {"pb.fixture.drop-ladder@3", "pb.fixture.serve-target@1"}


def test_it_04_02a_full_setup_gets_the_four_player_drill() -> None:
    library = _reviewed_copy()
    prefs = _prefs(*SETUPS[-1], 60, 5)
    result = assemble(WEAKNESS_SETS[0], prefs, library)
    assert isinstance(result, TrainingPlan)
    used = {x.drill.ref for s in result.sessions for x in s.assignments}
    assert "pb.fixture.drop-and-advance@1" in used
    assert [u.weakness_id for u in result.unfitted] == []


def test_it_04_02a_same_library_files_give_the_same_plan() -> None:
    prefs = _prefs(2, ("half_court",), 30, 3)
    digests = {
        p.content_digest()
        for p in (assemble(WEAKNESS_SETS[1], prefs, _reviewed_copy()) for _ in range(3))
        if isinstance(p, TrainingPlan)
    }
    assert len(digests) == 1
