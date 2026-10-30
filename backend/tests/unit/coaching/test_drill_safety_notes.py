"""The safety-note rule of the drill lint (QA-VERIFY04R3-09; FR-140; QD-DR-04; checklist C5).

A reviewed drill (``coach-reviewed`` or ``verified``) that is not deprecated and is tagged with a
movement skill (``footwork`` or ``movement``) must have a non-blank ``safety_notes``. Drafts are
not in the reviewed library, and a deprecated version keeps its locked content. Pure: drills
arrive as parsed JSON. Negative cases first; written red first.
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.coaching.drills.rules import lint_drills
from tests.unit.coaching.drill_helpers import METRICS, a_drill

pytestmark = pytest.mark.unit

NOTE = "Turn and run back for a ball overhead, never backpedal. Stop if dizzy or in pain."


def lint(*drills: dict[str, Any]) -> list[tuple[str, str]]:
    docs = {f"{d.get('id')}@{d.get('version')}.json": d for d in drills}
    return [(p.drill or "", p.reason) for p in lint_drills(docs, METRICS)]


# --------------------------------------------------------------- negatives first
@pytest.mark.parametrize("status", ["coach-reviewed", "verified"])
@pytest.mark.parametrize("tag", ["footwork", "movement"])
def test_a_reviewed_movement_drill_without_a_safety_note_fails(status: str, tag: str) -> None:
    drill = a_drill(skills=["AN-04", tag], review_status=status, safety_notes="")
    assert lint(drill) == [("pb.test.drop-ladder", "no safety note")]


def test_a_blank_safety_note_counts_as_missing() -> None:
    drill = a_drill(skills=["AN-04", "footwork"], review_status="coach-reviewed", safety_notes=" ")
    assert lint(drill) == [("pb.test.drop-ladder", "no safety note")]


def test_the_problem_names_the_movement_skill() -> None:
    drill = a_drill(skills=["AN-04", "footwork"], review_status="coach-reviewed")
    problems = lint_drills({"d.json": drill}, METRICS)
    assert [p.reason for p in problems] == ["no safety note"]
    assert "footwork" in problems[0].detail


def test_the_latest_reviewed_version_still_needs_a_note_when_an_older_one_is_deprecated() -> None:
    v1 = a_drill(
        skills=["AN-04", "footwork"],
        review_status="coach-reviewed",
        deprecated_by="pb.test.drop-ladder@2",
    )
    v2 = a_drill(version=2, skills=["AN-04", "footwork"], review_status="coach-reviewed")
    assert lint(v1, v2) == [("pb.test.drop-ladder", "no safety note")]


# --------------------------------------------------------------- outside the rule
def test_a_draft_movement_drill_without_a_note_passes() -> None:
    assert lint(a_drill(skills=["AN-04", "footwork"], review_status="draft")) == []


def test_a_deprecated_reviewed_version_keeps_its_locked_content() -> None:
    v1 = a_drill(
        skills=["AN-04", "footwork"],
        review_status="coach-reviewed",
        deprecated_by="pb.test.drop-ladder@2",
    )
    v2 = a_drill(
        version=2, skills=["AN-04", "footwork"], review_status="coach-reviewed", safety_notes=NOTE
    )
    assert lint(v1, v2) == []


def test_a_reviewed_drill_without_a_movement_skill_needs_no_note() -> None:
    assert lint(a_drill(review_status="coach-reviewed")) == []


def test_a_reviewed_movement_drill_with_a_note_passes() -> None:
    drill = a_drill(skills=["AN-04", "footwork"], review_status="verified", safety_notes=NOTE)
    assert lint(drill) == []
