"""Drill coverage by players x equipment profile (QA-VERIFY04R3-01; FR-124 "Not for me"; FR-141;
QD-DR-05; drill-review-checklist §3.1). Pure: drills arrive as plan ``Drill`` values.

G04-01 step 9 swapped a drill for a player alone with a wall (1 player, 30 min, 3 sessions,
equipment wall, intermediate) and got ``409 no_alternative``: the library held one fitting drill
per target. The profile axis counts, per target x level x profile, the drills that fit the
profile's preferences exactly as the plan does (``Drill.fits``, QD-PL-02) and that fit its
session's 40% cap (QD-PL-03), and needs >= 2 of them, so a swap always has a second drill.

Negative cases first (empty library, one drill, each way a drill fails the profile, the
counting rules); then a library with two solo-wall drills per target passes and renders.
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.coaching.drills.coverage import (
    PROFILES,
    SOLO_WALL,
    TARGETS,
    check_profiles,
    render_profiles,
)
from racket.coaching.plan.domain.model import Drill
from tests.unit.coaching.drill_helpers import a_drill

pytestmark = pytest.mark.unit

SHARES = ["AN-07", "share:fault", "share:forced-error"]
ALL = ["AN-01", "AN-02", "AN-04", "AN-05", "AN-07"]


def wall(drill_id: str, version: int = 1, **over: Any) -> dict[str, Any]:
    """A reviewed solo wall drill, beginner..intermediate, 8-15 min, hitting every target."""
    base = {
        "players": 1,
        "needs": ["wall"],
        "skills": SHARES,
        "target_metrics": ALL,
        "level_min": "beginner",
        "level_max": "intermediate",
        "duration_min": 8,
        "duration_max": 15,
        "review_status": "coach-reviewed",
    }
    return a_drill(drill_id, version, **{**base, **over})


def two_per_target() -> list[dict[str, Any]]:
    return [wall(f"pb.test.wall-{n}") for n in "ab"]


def edit(lib: list[dict[str, Any]], drill_id: str, **over: Any) -> list[dict[str, Any]]:
    return [{**d, **over} if d["id"] == drill_id else d for d in lib]


def gaps(docs: list[dict[str, Any]]) -> list[str]:
    return list(check_profiles(Drill.from_document(d) for d in docs).gaps)


def one_left(target: str = "") -> list[str]:
    targets = [target] if target else list(TARGETS)
    return [f"{t} × intermediate × solo+wall: drills: 1" for t in targets]


# --------------------------------------------------------------- negatives first
def test_an_empty_library_names_every_solo_wall_cell() -> None:
    assert gaps([]) == [f"{t} × intermediate × solo+wall: drills: 0" for t in TARGETS]


def test_one_solo_wall_drill_per_target_is_named_for_every_target() -> None:
    """VERIFY-04-r3: one fitting drill per metric, so every "Not for me" was 409."""
    assert gaps(two_per_target()[:1]) == one_left()


@pytest.mark.parametrize(
    "change",
    [
        {"players": 2},
        {"needs": ["wall", "half_court"]},
        {"needs": ["wall", "ball_machine"]},
        {"level_min": "advanced", "level_max": "advanced"},
        {"level_max": "beginner"},
        {"duration_min": 13},  # over the 30-minute session's 12-minute drill cap
        {"review_status": "draft"},
        {"deprecated_by": "pb.test.wall-a@1"},
        {"skills": ["warm-up", *SHARES]},
    ],
    ids=[
        "pairs",
        "court",
        "ball-machine",
        "advanced-only",
        "beginner-only",
        "too-long",
        "draft",
        "deprecated",
        "warm-up",
    ],
)
def test_a_drill_that_does_not_fit_the_profile_does_not_count(change: dict[str, Any]) -> None:
    assert gaps(edit(two_per_target(), "pb.test.wall-b", **change)) == one_left()


def test_a_superseded_version_does_not_count() -> None:
    lib = [*two_per_target(), wall("pb.test.wall-b", 2, players=2)]
    assert gaps(lib) == one_left()


def test_a_wall_free_solo_drill_counts() -> None:
    """``needs`` must be a subset of the profile's equipment, as in ``Drill.fits``."""
    assert gaps(edit(two_per_target(), "pb.test.wall-b", needs=[])) == []


def test_a_drill_counts_only_for_the_targets_it_hits() -> None:
    lib = edit(two_per_target(), "pb.test.wall-b", target_metrics=["AN-04"], skills=["AN-04"])
    assert gaps(lib) == [g for g in one_left() if not g.startswith("AN-04 ")]


def test_an_an07_drill_counts_only_in_its_share_cell() -> None:
    lib = edit(two_per_target(), "pb.test.wall-b", skills=["AN-07", "share:fault"])
    assert gaps(lib) == one_left("AN-07:forced-error")


# --------------------------------------------------------------- the profile and a full library
def test_the_solo_wall_profile_is_the_g04_01_step_3_preferences() -> None:
    assert PROFILES == (SOLO_WALL,)
    assert SOLO_WALL.name == "solo+wall"
    prefs = SOLO_WALL.preferences("intermediate")
    assert (prefs.players_available, prefs.equipment, prefs.level) == (
        1,
        frozenset({"wall"}),
        "intermediate",
    )
    assert (prefs.minutes_per_session, prefs.sessions_per_week, prefs.drill_cap) == (30, 3, 12)
    assert SOLO_WALL.levels == ("intermediate",)


def test_two_solo_wall_drills_per_target_pass_and_render_one_row_per_cell() -> None:
    report = check_profiles(Drill.from_document(d) for d in two_per_target())
    assert report.ok
    assert [(c.target, c.level, c.profile) for c in report.cells] == [
        (t, "intermediate", "solo+wall") for t in TARGETS
    ]
    lines = render_profiles(report)
    assert lines[0].split() == ["target", "level", "profile", "drills"]
    assert len(lines) == 1 + len(TARGETS)
    assert lines[1].split() == ["AN-01", "intermediate", "solo+wall", "2"]
    assert lines[-1].split() == ["AN-07:forced-error", "intermediate", "solo+wall", "2"]
