"""IT-04-18 (QA-VERIFY04R3-01; FR-124, FR-141; QD-DR-05; G04-01 step 9): a player alone with a
wall can always say "Not for me", over the real ``content/drills`` files.

Boundaries: CLI <-> files (``racket-drill-coverage`` prints the solo+wall rows and fails naming
a solo+wall cell with fewer than 2 drills) and files -> plan domain (``Drill.from_document``,
``assemble``, ``TrainingPlan.swap``) with the G04-01 step 3 preferences.

Negative first: a copy of the library with only ``pb.drive.wall-margin`` left as the solo+wall
AN-04 drill (the VERIFY-04-r3 library) fails naming that cell. Then the library passes with >= 2
drills in every solo+wall row, and for each plan target a plan for {1 player, 30 min, 3
sessions/week, wall, intermediate} swaps its weakness drill for another drill citing the same
target (VERIFY-04-r3 got ``409 no_alternative`` there). Written red first.
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
        if solo_wall and not warm_up and "AN-04" in doc["target_metrics"]:
            if doc["id"] != "pb.drive.wall-margin":
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


@pytest.mark.parametrize("target", TARGETS)
def test_it_04_18_a_solo_wall_plan_swaps_its_weakness_drill_for_the_same_target(
    target: str,
) -> None:
    library = [Drill.from_document(doc) for _, doc in _documents(LIBRARY)]
    weakness = PlanWeakness(f"w-{target}", target, 1)
    plan = assemble([weakness], G04_01, library)
    assert isinstance(plan, TrainingPlan), plan
    first = plan.sessions[0]
    old = first.assignments[1]
    assert old.weakness_id == weakness.id
    swapped = plan.swap(
        week=first.week, index=first.index, position=2, library=library, cited=set(TARGETS)
    )
    assert isinstance(swapped, DrillSwapped)
    assert (swapped.from_drill, swapped.target) == (old.drill.ref, target)
    assert swapped.to_drill != old.drill.ref
    new = plan.sessions[0].assignments[1]
    assert new.drill.ref == swapped.to_drill
    assert new.drill.fits(G04_01) and target in new.drill.plan_targets
    assert plan.sessions[0].total_minutes <= 30
