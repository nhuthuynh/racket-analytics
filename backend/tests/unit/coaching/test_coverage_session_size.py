"""The session-size coverage rule (ST-081a; FR-141.R1, FR-124.R1-R2; drill-review-checklist
§3.1.1; COACH-5 §3-§4). Pure: drills arrive as plan ``Drill`` values.

A single-weakness plan (case a) or a session of 3 or more drills whose drills overlap (case b)
can hold S drills of one target, where S = floor((minutes_per_session - 5) / m) and m is the
smallest ``duration_min`` among the profile's counted drills. So each target x level x profile
cell needs >= S + 1 swap-counted drills (counted, fitting, ``duration_min`` <= m) for the first
"Not for me" per target per plan to swap. 3 for ``solo+wall`` at 30 minutes.

Negative cases first: the first red is a single-weakness solo-wall cell with 2 drills, which the
pair rule passes and this rule reports as a gap.
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.coaching.drills.coverage import (
    SOLO_WALL,
    TARGETS,
    Profile,
    check_profile_pairs,
    check_profiles,
    check_session_size,
    render_session_size,
    session_size,
)
from racket.coaching.plan.domain.model import Drill
from tests.unit.coaching.drill_helpers import a_drill

pytestmark = pytest.mark.unit

SHARES = ["AN-07", "share:fault", "share:forced-error"]
ALL = ["AN-01", "AN-02", "AN-04", "AN-05", "AN-07"]


def wall(drill_id: str, **over: Any) -> dict[str, Any]:
    """A reviewed solo wall drill, beginner..intermediate, 10-15 min, hitting every target."""
    base = {
        "players": 1,
        "needs": ["wall"],
        "skills": SHARES,
        "target_metrics": ALL,
        "level_min": "beginner",
        "level_max": "intermediate",
        "duration_min": 10,
        "duration_max": 15,
        "review_status": "coach-reviewed",
    }
    return a_drill(drill_id, 1, **{**base, **over})


def per_target(n: int, **over: Any) -> list[dict[str, Any]]:
    return [wall(f"pb.test.wall-{chr(ord('a') + k)}", **over) for k in range(n)]


def disjoint(n: int) -> list[dict[str, Any]]:
    """n drills per target, each citing that target only (no two targets share a drill)."""
    out = []
    for t in TARGETS:
        metric, _, share = t.partition(":")
        skills = [metric, f"share:{share}"] if share else [metric]
        slug = t.lower().replace(":", "-")
        out += [
            wall(f"pb.test.{slug}-{k}", skills=skills, target_metrics=[metric]) for k in range(n)
        ]
    return out


def drills(docs: list[dict[str, Any]]) -> list[Drill]:
    return [Drill.from_document(d) for d in docs]


def gaps(docs: list[dict[str, Any]], *profiles: Profile) -> list[str]:
    return list(check_session_size(drills(docs), profiles or (SOLO_WALL,)).gaps)


def short(n: int, need: int = 3, profile: str = "solo+wall", targets: tuple[str, ...] = TARGETS):
    return [
        f"{t} × intermediate × {profile}: drills: {n} < {need} (single-weakness swap)"
        for t in targets
    ]


# --------------------------------------------------------------- negatives first
def test_a_single_weakness_solo_wall_cell_with_two_drills_is_reported_as_a_gap() -> None:
    """First red (sprint-05 §5): the pair rule and the >= 2 rule pass this library, yet a
    single-weakness plan holds both drills in one session and "Not for me" answers 409."""
    lib = disjoint(2)
    assert check_profiles(drills(lib)).ok
    assert check_profile_pairs(drills(lib)) == ()
    assert gaps(lib) == short(2)


def test_an_empty_library_names_every_solo_wall_cell() -> None:
    assert gaps([]) == short(0)


def test_a_drill_longer_than_the_shortest_slot_does_not_count() -> None:
    """QA-R2-1: a slot's room can be 10 under a 12-minute cap, so a third drill of
    ``duration_min`` 12 fits the cap but not the swap guarantee."""
    lib = [*per_target(2), wall("pb.test.wall-z-long", duration_min=12)]
    assert check_profiles(drills(lib)).ok  # the cap filter counts it
    assert gaps(lib) == short(2)


@pytest.mark.parametrize(
    "change",
    [
        {"players": 2},
        {"needs": ["wall", "half_court"]},
        {"level_max": "beginner"},
        {"review_status": "draft"},
        {"skills": ["warm-up", *SHARES]},
    ],
    ids=["pairs", "court", "beginner-only", "draft", "warm-up"],
)
def test_a_drill_that_does_not_fit_the_profile_does_not_count(change: dict[str, Any]) -> None:
    lib = [*per_target(2), wall("pb.test.wall-c", **change)]
    assert gaps(lib) == short(2)


def test_a_longer_session_needs_more_drills_per_cell() -> None:
    """Case b: a 45-minute session holds S = floor(40 / 10) = 4 weakness drills, so 3 drills
    per target leave no swap when all of them cite the target."""
    long = Profile("solo+wall+45", 1, frozenset({"wall"}), ("intermediate",), 45)
    assert gaps(per_target(3), long) == short(3, 5, "solo+wall+45")


def test_s_comes_from_the_shortest_counted_drill() -> None:
    """m = 8 makes S = floor(25 / 8) = 3 for 30 minutes, so the cell needs 4."""
    assert gaps(per_target(3, duration_min=8)) == short(3, 4)


def test_an_an07_drill_counts_only_in_its_share_cell() -> None:
    lib = [*per_target(2), wall("pb.test.wall-c", skills=["AN-07", "share:fault"])]
    assert gaps(lib) == short(2, targets=("AN-07:forced-error",))


# --------------------------------------------------------------- the rule and a full library
def test_session_size_is_the_weakness_drills_one_session_holds() -> None:
    assert session_size(30, 10) == 2
    assert session_size(30, 8) == 3
    assert session_size(45, 10) == 4
    assert session_size(30, 12) == 2


def test_disjoint_drills_pass_with_three_per_target() -> None:
    assert gaps(disjoint(3)) == []


def test_three_ten_minute_solo_wall_drills_per_target_pass_and_render() -> None:
    report = check_session_size(drills(per_target(3)))
    assert report.ok
    assert [(c.target, c.level, c.profile, c.drills, c.need) for c in report.cells] == [
        (t, "intermediate", "solo+wall", 3, 3) for t in TARGETS
    ]
    lines = render_session_size(report)
    assert lines[0].split() == ["target", "level", "profile", "swap-counted", "need"]
    assert len(lines) == 1 + len(TARGETS)
    assert lines[1].split() == ["AN-01", "intermediate", "solo+wall", "3", "3"]
