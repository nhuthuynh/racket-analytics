"""Drill coverage for the rankable reference patterns (ST-173b; FR-173.R3; FR-173.R1). Pure:
drills arrive as plan ``Drill`` values.

Each rankable new pattern (AN-09, AN-13) x level x players (1, 2, 4) x equipment (wall, no wall,
ball machine) cell needs >= 1 counted drill that the plan could assign there: ``Drill.fits`` the
cell's preferences (QD-PL-02) and its ``duration_min`` fits the drill cap (QD-PL-03), so a ranked
weakness never gets "no exercise yet for this gap" for want of a drill. Gaps read
``AN-13 × intermediate × 1 player × wall: no fitting drill``.

Negative cases first (empty library, each way a drill misses a cell, the counting rules); then a
library with one solo wall and one solo court drill per pattern passes and renders. Written red
first.
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.coaching.drills.coverage import (
    EQUIPMENT_SETUPS,
    PATTERN_TARGETS,
    PLAYER_COUNTS,
    check_patterns,
    render_patterns,
)
from racket.coaching.plan.domain.model import LEVELS, Drill
from tests.unit.coaching.drill_helpers import a_drill

pytestmark = pytest.mark.unit

NEW = ["AN-09", "AN-13"]


def drill(drill_id: str, version: int = 1, **over: Any) -> dict[str, Any]:
    """A reviewed solo drill for every level, 8-12 min, hitting both new patterns at a wall."""
    base = {
        "players": 1,
        "needs": ["wall"],
        "level_min": "beginner",
        "level_max": "advanced",
        "duration_min": 8,
        "duration_max": 12,
        "skills": ["dink"],
        "target_metrics": NEW,
        "review_status": "coach-reviewed",
    }
    return a_drill(drill_id, version, **{**base, **over})


def full_library() -> list[dict[str, Any]]:
    """One solo wall drill and one solo half-court drill per new pattern: every cell has one."""
    return [drill("pb.test.wall"), drill("pb.test.court", needs=["half_court"])]


def without(lib: list[dict[str, Any]], drill_id: str) -> list[dict[str, Any]]:
    return [d for d in lib if d["id"] != drill_id]


def edit(lib: list[dict[str, Any]], drill_id: str, **over: Any) -> list[dict[str, Any]]:
    return [{**d, **over} if d["id"] == drill_id else d for d in lib]


def gaps(docs: list[dict[str, Any]]) -> list[str]:
    return list(check_patterns(Drill.from_document(d) for d in docs).gaps)


def cells(pattern: str, players: tuple[int, ...], setup: str, levels: Any = LEVELS) -> list[str]:
    word = {1: "1 player", 2: "2 players", 4: "4 players"}
    return [f"{pattern} × {lv} × {word[p]} × {setup}: no fitting drill"
            for lv in levels for p in players]  # fmt: skip


# --------------------------------------------------------------- negatives first
def test_an_empty_library_names_every_pattern_level_players_equipment_cell() -> None:
    found = gaps([])
    assert len(found) == 2 * 3 * 3 * 3
    assert "AN-13 × intermediate × 1 player × wall: no fitting drill" in found
    assert "AN-09 × advanced × 4 players × ball machine: no fitting drill" in found


def test_a_library_without_a_solo_wall_an13_drill_names_that_cell() -> None:
    """FR-173.R3 negative example: the only AN-13 wall drill needs 2 players."""
    lib = [*edit(full_library(), "pb.test.wall", target_metrics=["AN-09"]),
           drill("pb.test.wall-pairs", players=2, target_metrics=["AN-13"])]  # fmt: skip
    assert gaps(lib) == cells("AN-13", (1,), "wall")


def test_a_drill_counts_for_its_pattern_only() -> None:
    lib = edit(full_library(), "pb.test.wall", target_metrics=["AN-09"])
    assert gaps(lib) == cells("AN-13", (1, 2, 4), "wall")


def test_a_court_drill_does_not_fit_a_wall_alone() -> None:
    assert gaps(without(full_library(), "pb.test.wall")) == [
        g for p in ("AN-09", "AN-13") for g in cells(p, (1, 2, 4), "wall")
    ]


def test_a_ball_machine_drill_fits_only_where_a_ball_machine_is() -> None:
    lib = edit(full_library(), "pb.test.court", needs=["half_court", "ball_machine"])
    assert gaps(lib) == [g for p in ("AN-09", "AN-13") for g in cells(p, (1, 2, 4), "no wall")]


def test_a_four_player_drill_fits_only_four_players() -> None:
    lib = edit(full_library(), "pb.test.court", players=4)
    expected = [
        g for p in ("AN-09", "AN-13") for s in ("no wall", "ball machine")
        for g in cells(p, (1, 2), s)
    ]  # fmt: skip
    assert sorted(gaps(lib)) == sorted(expected)


def test_a_drill_counts_only_in_its_level_range() -> None:
    lib = edit(full_library(), "pb.test.court", level_max="intermediate")
    expected = [
        g for p in ("AN-09", "AN-13") for s in ("no wall", "ball machine")
        for g in cells(p, (1, 2, 4), s, ("advanced",))
    ]  # fmt: skip
    assert sorted(gaps(lib)) == sorted(expected)


def test_a_drill_longer_than_the_drill_cap_does_not_count() -> None:
    lib = edit(full_library(), "pb.test.court", duration_min=25, duration_max=30)
    expected = [
        g for p in ("AN-09", "AN-13") for s in ("no wall", "ball machine")
        for g in cells(p, (1, 2, 4), s)
    ]  # fmt: skip
    assert sorted(gaps(lib)) == sorted(expected)


@pytest.mark.parametrize(
    "over",
    [
        {"review_status": "draft"},
        {"skills": ["warm-up"]},
        {"deprecated_by": "pb.test.wall@2"},
    ],
    ids=["draft", "warm-up", "deprecated"],
)
def test_draft_warm_up_and_deprecated_drills_do_not_count(over: dict[str, Any]) -> None:
    lib = edit(full_library(), "pb.test.wall", **over)
    assert gaps(lib) == [g for p in ("AN-09", "AN-13") for g in cells(p, (1, 2, 4), "wall")]


def test_only_the_latest_version_counts() -> None:
    lib = [*full_library(), drill("pb.test.wall", 2, target_metrics=["AN-09"])]
    assert gaps(lib) == cells("AN-13", (1, 2, 4), "wall")


# --------------------------------------------------------------- happy path
def test_a_full_library_has_no_gap_and_renders_one_row_per_cell() -> None:
    report = check_patterns(Drill.from_document(d) for d in full_library())
    assert report.ok
    assert len(report.cells) == 54
    assert all(c.drills >= 1 for c in report.cells)
    lines = render_patterns(report)
    assert len(lines) == 1 + 54
    assert lines[0].split() == ["pattern", "level", "players", "equipment", "drills"]
    assert lines[1].split() == ["AN-09", "beginner", "1", "wall", "1"]


def test_the_axes_are_the_ones_fr_173_names() -> None:
    assert PATTERN_TARGETS == ("AN-09", "AN-13")
    assert PLAYER_COUNTS == (1, 2, 4)
    assert [name for name, _ in EQUIPMENT_SETUPS] == ["wall", "no wall", "ball machine"]
