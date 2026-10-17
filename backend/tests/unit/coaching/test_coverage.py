"""Drill coverage matrix (ST-059; FR-141; QD-DR-05; drill-review-checklist §3). Pure: drills
arrive as plan ``Drill`` values.

Negative cases first: an empty library names all 18 cells and the library size; a cell with
only 4-player drills, only ball-machine drills or one drill; draft, deprecated and superseded
versions do not count; AN-07 counts only through its share skill and is named without one; a
warm-up counts in the library but in no cell; fewer than 20 reviewed drills or 3 warm-ups
fail. Then a full library passes and renders the matrix in target x level order.
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.coaching.drills.coverage import TARGETS, check_coverage, render
from racket.coaching.plan.domain.model import LEVELS, Drill
from tests.unit.coaching.drill_helpers import a_drill

pytestmark = pytest.mark.unit

WARM_UPS = [
    a_drill(f"pb.test.warm-{n}", skills=["warm-up"], review_status="coach-reviewed") for n in "abc"
]
SHARES = ["AN-07", "share:fault", "share:forced-error"]


def drill(drill_id: str, version: int = 1, **over: Any) -> dict[str, Any]:
    """A reviewed pairs drill for every level, targeting AN-01 unless told otherwise."""
    base = {"level_min": "beginner", "level_max": "advanced", "target_metrics": ["AN-01"]}
    return a_drill(drill_id, version, **{**base, "review_status": "coach-reviewed", **over})


def full_library() -> list[dict[str, Any]]:
    """20 reviewed drills (3 warm-ups) with every cell at >= 2 drills; AN-05 has its own two."""
    core = [
        drill(
            f"pb.test.all-{n}", skills=SHARES, target_metrics=["AN-01", "AN-02", "AN-04", "AN-07"]
        )
        for n in "ab"
    ]
    an05 = [drill(f"pb.test.an05-{n}", target_metrics=["AN-05"]) for n in "ab"]
    filler = [drill(f"pb.test.filler-{n:02d}") for n in range(13)]
    return [*WARM_UPS, *core, *an05, *filler]


def edit(lib: list[dict[str, Any]], prefix: str, **over: Any) -> list[dict[str, Any]]:
    return [{**d, **over} if d["id"].startswith(prefix) else d for d in lib]


def gaps(docs: list[dict[str, Any]]) -> list[str]:
    return list(check_coverage(Drill.from_document(d) for d in docs).gaps)


# --------------------------------------------------------------- negatives first
def test_an_empty_library_names_every_cell_and_the_library_size() -> None:
    found = gaps([])
    for target in TARGETS:
        for level in LEVELS:
            for need in ("drills: 0", "players ≤ 2: 0", "no ball_machine: 0"):
                assert f"{target} × {level}: {need}" in found
    assert "library: 0 < 20 reviewed drills" in found
    assert "warm-ups: 0 < 3" in found
    assert len(found) == 18 * 3 + 2


def test_a_cell_with_only_four_player_drills_is_named() -> None:
    lib = edit(full_library(), "pb.test.an05", players=4, level_max="beginner")
    lib += [drill(f"pb.test.an05-up-{n}", target_metrics=["AN-05"], level_min="intermediate")
            for n in "ab"]  # fmt: skip
    assert gaps(lib) == ["AN-05 × beginner: players ≤ 2: 0"]


def test_a_cell_with_only_ball_machine_drills_is_named() -> None:
    lib = edit(full_library(), "pb.test.an05", needs=["ball_machine"])
    assert gaps(lib) == [f"AN-05 × {lv}: no ball_machine: 0" for lv in LEVELS]


def test_a_cell_with_one_drill_is_named_with_its_count() -> None:
    lib = [d for d in full_library() if d["id"] != "pb.test.an05-b"] + [drill("pb.test.extra")]
    assert gaps(lib) == [f"AN-05 × {lv}: drills: 1" for lv in LEVELS]


@pytest.mark.parametrize(
    "over",
    [{"review_status": "draft"}, {"deprecated_by": "pb.test.filler-00@1"}],
    ids=["draft", "deprecated"],
)
def test_draft_and_deprecated_drills_do_not_count(over: dict[str, Any]) -> None:
    lib = [*edit(full_library(), "pb.test.an05-b", **over), drill("pb.test.extra")]
    assert gaps(lib) == [f"AN-05 × {lv}: drills: 1" for lv in LEVELS]


def test_only_the_latest_version_counts() -> None:
    lib = [*full_library(), drill("pb.test.an05-b", 2)]
    assert gaps(lib) == [f"AN-05 × {lv}: drills: 1" for lv in LEVELS]


def test_an_an07_drill_counts_only_in_its_share_cell() -> None:
    lib = full_library() + [
        drill(f"pb.test.fault-{n}", skills=["AN-07", "share:fault"], target_metrics=["AN-07"])
        for n in "ab"
    ]
    report = check_coverage(Drill.from_document(d) for d in lib)
    cells = {(c.target, c.level): c.drills for c in report.cells}
    assert cells[("AN-07:fault", "beginner")] == 4
    assert cells[("AN-07:forced-error", "beginner")] == 2


def test_an_an07_drill_without_a_share_skill_is_named() -> None:
    lib = [*full_library(), drill("pb.test.no-share", skills=["AN-07"], target_metrics=["AN-07"])]
    assert gaps(lib) == ["pb.test.no-share@1: AN-07 without share skill"]


def test_a_drill_counts_only_in_its_level_range() -> None:
    lib = edit(full_library(), "pb.test.an05-b", level_min="advanced")
    assert gaps(lib) == [f"AN-05 × {lv}: drills: 1" for lv in ("beginner", "intermediate")]


def test_a_warm_up_counts_in_the_library_but_in_no_cell() -> None:
    lib = edit(full_library(), "pb.test.warm", target_metrics=["AN-05"])
    lib = [d for d in lib if d["id"] != "pb.test.an05-b"] + [drill("pb.test.extra")]
    assert gaps(lib) == [f"AN-05 × {lv}: drills: 1" for lv in LEVELS]
    report = check_coverage(Drill.from_document(d) for d in full_library())
    assert (report.counted, report.warm_ups) == (20, 3)


def test_fewer_than_20_reviewed_drills_fails() -> None:
    lib = [d for d in full_library() if d["id"] != "pb.test.filler-00"]
    assert gaps(lib) == ["library: 19 < 20 reviewed drills"]


def test_fewer_than_3_warm_ups_fails() -> None:
    lib = [d for d in full_library() if d["id"] != "pb.test.warm-a"] + [drill("pb.test.extra")]
    assert gaps(lib) == ["warm-ups: 2 < 3"]


# --------------------------------------------------------------- the full library passes
def test_a_full_library_has_no_gap() -> None:
    report = check_coverage(Drill.from_document(d) for d in full_library())
    assert report.ok
    assert report.gaps == ()
    assert [(c.target, c.level) for c in report.cells] == [
        (t, lv) for t in TARGETS for lv in LEVELS
    ]


def test_render_prints_a_header_and_one_row_per_cell() -> None:
    lines = render(check_coverage(Drill.from_document(d) for d in full_library()))
    assert lines[0].split() == ["target", "level", "drills", "players≤2", "no_ball_machine"]
    assert len(lines) == 19
    assert lines[1].split() == ["AN-01", "beginner", "15", "15", "15"]
    assert lines[-1].split() == ["AN-07:forced-error", "advanced", "2", "2", "2"]


def test_the_targets_are_the_plan_targets() -> None:
    from racket.coaching.plan.acl import PLAN_TARGETS

    assert TARGETS == PLAN_TARGETS
