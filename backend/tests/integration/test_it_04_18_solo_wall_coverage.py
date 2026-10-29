"""IT-04-18 (QA-VERIFY04R3-01; FR-124, FR-141; QD-DR-05; G04-01 step 9): a player alone with a
wall can always say "Not for me", over the real ``content/drills`` files.

Boundaries: CLI <-> files (``racket-drill-coverage`` prints the solo+wall rows and fails naming
a solo+wall cell with fewer than 2 drills) and files -> plan domain (``Drill.from_document``,
``assemble``, ``TrainingPlan.swap``) with the G04-01 step 3 preferences.

Negative first: a copy of the library with only ``pb.drive.wall-margin`` left as the solo+wall
AN-04 drill (the VERIFY-04-r3 library) fails naming that cell. Then the library passes with >= 2
drills in every solo+wall row, and for each plan target a plan for {1 player, 30 min, 3
sessions/week, wall, intermediate} that trains it with a second weakness swaps each of its drills
for another drill citing the same target (VERIFY-04-r3 got ``409 no_alternative`` there).
Written red first.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from racket.coaching.plan.domain import (
    Drill,
    DrillSwapped,
    PlanWeakness,
    Preferences,
    TrainingPlan,
    assemble,
)
from tests.integration.test_it_04_13_drill_coverage_cli import LIBRARY, fails, matrix_rows, run

pytestmark = pytest.mark.integration

TARGETS = ("AN-01", "AN-02", "AN-04", "AN-05", "AN-07:fault", "AN-07:forced-error")
_SOLO_WALL_ROW = re.compile(r"^(AN-\d{2}(?::[a-z-]+)?)\s+intermediate\s+solo\+wall\s+(\d+)$")
G04_01 = Preferences(
    minutes_per_session=30,
    sessions_per_week=3,
    players_available=1,
    equipment=frozenset({"wall"}),
    level="intermediate",
)


def solo_wall_rows(out: str) -> dict[str, int]:
    return {
        m.group(1): int(m.group(2))
        for m in (_SOLO_WALL_ROW.match(line) for line in out.splitlines())
        if m
    }


def _documents(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    files = sorted(p for p in root.rglob("*.json") if p.name != "schema.json")
    return [(p, json.loads(p.read_text(encoding="utf-8"))) for p in files]


# ---------------------------------------------------------------- negative case first
def test_it_04_18_a_library_with_one_solo_wall_an04_drill_fails_naming_the_cell(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    copy = tmp_path / "drills"
    shutil.copytree(LIBRARY, copy)
    for path, doc in _documents(copy):
        solo_wall = doc["players"] == 1 and set(doc["needs"]) <= {"wall"}
        warm_up = "warm-up" in doc["skills"]
        an04 = "AN-04" in doc["target_metrics"]
        if solo_wall and not warm_up and an04 and doc["id"] != "pb.drive.wall-margin":
            path.unlink()
    rc, out = run(capsys, copy)
    assert rc == 1, out
    assert "FAIL AN-04 × intermediate × solo+wall: drills: 1" in fails(out), out


# ---------------------------------------------------------------- the library passes
def test_it_04_18_the_library_has_two_solo_wall_drills_per_target(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc, out = run(capsys, LIBRARY)
    assert rc == 0, out
    assert fails(out) == [], out
    assert matrix_rows(out) == 18, out  # the target x level matrix is unchanged
    rows = solo_wall_rows(out)
    assert sorted(rows) == sorted(TARGETS), out
    assert all(n >= 2 for n in rows.values()), rows


def _swap_cases() -> list[tuple[str, int]]:
    """(target, session number) for every session of a two-weakness plan (see the test)."""
    return [(t, n) for t in TARGETS for n in range(G04_01.sessions_per_week * 2)]


@pytest.mark.parametrize(("target", "n"), _swap_cases())
def test_it_04_18_a_solo_wall_plan_swaps_its_weakness_drill_for_the_same_target(
    target: str, n: int
) -> None:
    """G04-01 shape: the plan trains more than one weakness (rank 1 ``target``, rank 2 the next
    target), so each session holds one drill of ``target`` at most; every one of them swaps,
    each on a fresh plan (a swapped-out drill is never offered again in its plan)."""
    library = [Drill.from_document(doc) for _, doc in _documents(LIBRARY)]
    other = TARGETS[(TARGETS.index(target) + 1) % len(TARGETS)]
    weaknesses = [PlanWeakness("w-1", target, 1), PlanWeakness("w-2", other, 2)]
    plan = assemble(weaknesses, G04_01, library)
    assert isinstance(plan, TrainingPlan), plan
    assert plan.unfitted == (), plan.unfitted
    session = plan.sessions[n]
    for x in session.assignments:
        if x.weakness_id != "w-1":
            continue
        swapped = plan.swap(
            week=session.week,
            index=session.index,
            position=x.position,
            library=library,
            cited=set(TARGETS),
        )
        assert isinstance(swapped, DrillSwapped)
        assert (swapped.from_drill, swapped.target) == (x.drill.ref, target)
        assert swapped.to_drill != x.drill.ref
        new = plan.sessions[n].assignments[x.position - 1]
        assert new.drill.ref == swapped.to_drill
        assert new.drill.fits(G04_01)
        assert target in new.drill.plan_targets
        assert plan.sessions[n].total_minutes <= G04_01.minutes_budget
        plan = assemble(weaknesses, G04_01, library)


# ---------------------------------------------------------------- PE-R1-1: every pair of targets
NEW_SERVE_DRILL = "pb.serve.wall-serve-and-ready"


def test_it_04_18_two_serve_targets_sharing_their_only_two_drills_fail_naming_the_pair(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """PE-R1-1 negative first: AN-01 and AN-05 cited by the same two solo wall drills (the
    library before the third serve drill) leave a two-weakness session nothing to swap to."""
    copy = tmp_path / "drills"
    shutil.copytree(LIBRARY, copy)
    shutil.rmtree(copy / NEW_SERVE_DRILL, ignore_errors=True)
    rc, out = run(capsys, copy)
    assert rc == 1, out
    assert "FAIL AN-01 with AN-05 × intermediate × solo+wall: drills: 1" in fails(out), out
    assert "FAIL AN-05 with AN-01 × intermediate × solo+wall: drills: 1" in fails(out), out


def _pair_cases() -> list[tuple[str, str, int]]:
    """(rank 1, rank 2, session number) for every ordered pair of distinct targets."""
    pairs = [(t, u) for t in TARGETS for u in TARGETS if t != u]
    return [(t, u, n) for t, u in pairs for n in range(G04_01.sessions_per_week * 2)]


@pytest.mark.parametrize(("target", "other", "n"), _pair_cases())
def test_it_04_18_every_weakness_drill_of_any_two_weakness_solo_wall_plan_swaps(
    target: str, other: str, n: int
) -> None:
    """PE-R1-1: for every ordered pair of targets, each weakness drill of each session swaps
    for another drill citing the same target, each on a fresh plan."""
    library = [Drill.from_document(doc) for _, doc in _documents(LIBRARY)]
    weaknesses = [PlanWeakness("w-1", target, 1), PlanWeakness("w-2", other, 2)]
    plan = assemble(weaknesses, G04_01, library)
    assert isinstance(plan, TrainingPlan), plan
    assert plan.unfitted == (), plan.unfitted
    session = plan.sessions[n]
    assert sum(x.weakness_id is not None for x in session.assignments) <= 2
    for x in session.assignments:
        if x.weakness_id is None:
            continue
        plan = assemble(weaknesses, G04_01, library)
        swapped = plan.swap(
            week=session.week,
            index=session.index,
            position=x.position,
            library=library,
            cited=set(TARGETS),
        )
        assert isinstance(swapped, DrillSwapped)
        assert swapped.to_drill != x.drill.ref
        new = plan.sessions[n].assignments[x.position - 1]
        assert new.drill.fits(G04_01)
        assert swapped.target in new.drill.plan_targets
        assert plan.sessions[n].total_minutes <= G04_01.minutes_budget
