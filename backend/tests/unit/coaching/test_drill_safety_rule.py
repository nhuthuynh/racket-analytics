"""QD-DR-04 safety-notes rule of the drill lint (FIX-04-1d; drill-review-checklist C5). Pure.

Negatives first: a reviewed drill whose content involves lobs, diving, sprints or footwork and
has empty (or blank) safety notes fails, naming the drill and "safety notes missing"; then the
drills the rule does not cover (draft, deprecated, no trigger, notes given) pass.
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.coaching.drills.rules import lint_drills
from tests.unit.coaching.drill_helpers import METRICS, a_drill

pytestmark = pytest.mark.unit


def lint(*drills: dict[str, Any]) -> list[tuple[str, str]]:
    docs = {f"{d.get('id')}@{d.get('version')}.json": d for d in drills}
    return [(p.drill or "", p.reason) for p in lint_drills(docs, METRICS)]


def reviewed(**over: Any) -> dict[str, Any]:
    return a_drill(**{"review_status": "coach-reviewed", **over})


@pytest.mark.parametrize(
    "over",
    [
        {"skills": ["AN-04", "footwork"]},
        {"summary": "Retreat for overhead lobs and smash them back."},
        {"setup": ["Sprint from the baseline to the kitchen line"]},
        {"setup": ["Dive for the wide ball"]},
        {"name": "Diving gets"},
        {"success_criterion": "8 of 10 lobs land in the back third"},
    ],
    ids=["skill-footwork", "summary-lob", "setup-sprint", "setup-dive", "name-diving", "criterion"],
)
def test_a_reviewed_drill_with_a_trigger_and_no_safety_notes_fails(over: dict[str, Any]) -> None:
    assert lint(reviewed(**over)) == [("pb.test.drop-ladder", "safety notes missing")]


def test_the_failure_names_the_trigger_word() -> None:
    problems = lint_drills({"d.json": reviewed(skills=["AN-04", "footwork"])}, METRICS)
    assert "footwork" in problems[0].detail
    assert "QD-DR-04" in problems[0].detail


def test_blank_safety_notes_count_as_missing() -> None:
    assert lint(reviewed(skills=["AN-04", "footwork"], safety_notes="   ")) == [
        ("pb.test.drop-ladder", "safety notes missing")
    ]


def test_a_verified_drill_is_covered_too() -> None:
    assert lint(reviewed(skills=["AN-04", "footwork"], review_status="verified")) == [
        ("pb.test.drop-ladder", "safety notes missing")
    ]


def test_a_reviewed_drill_with_safety_notes_passes() -> None:
    assert lint(reviewed(skills=["AN-04", "footwork"], safety_notes="Stop if in pain.")) == []


def test_a_draft_drill_with_a_trigger_passes() -> None:
    assert lint(a_drill(skills=["AN-04", "footwork"])) == []


def test_a_deprecated_reviewed_drill_passes() -> None:
    old = reviewed(skills=["AN-04", "footwork"], deprecated_by="pb.test.drop-ladder@2")
    new = reviewed(version=2, skills=["AN-04", "footwork"], safety_notes="Stop if in pain.")
    assert lint(old, new) == []


def test_a_reviewed_drill_without_a_trigger_passes() -> None:
    assert lint(reviewed()) == []
