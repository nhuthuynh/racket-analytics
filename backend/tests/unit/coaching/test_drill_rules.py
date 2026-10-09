"""Drill schema and lint (ST-053; FR-140; QD-DR-01..03). Pure: drills arrive as parsed JSON.

TDD order of sprint-03 §5 ``DrillLint``: unknown target metric, progression cycle, duration
46 min, criterion without a number, no source and no rationale; then the valid drill passes.
Immutability against the lock is in ``test_drill_lock.py``.
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


# --------------------------------------------------------------- FR-140 rules, negatives first
def test_an_unknown_target_metric_fails_naming_drill_and_metric() -> None:
    problems = lint_drills({"d.json": a_drill(target_metrics=["AN-99"])}, METRICS)
    assert [(p.drill, p.reason) for p in problems] == [("pb.test.drop-ladder", "unknown metric")]
    assert "AN-99" in problems[0].detail


def test_an_unknown_metric_in_skills_also_fails() -> None:
    assert lint(a_drill(skills=["AN-98", "third_shot_drop"])) == [
        ("pb.test.drop-ladder", "unknown metric")
    ]


def test_a_drill_that_is_its_own_progression_is_a_cycle() -> None:
    problems = lint_drills({"d.json": a_drill(progressions=["pb.test.drop-ladder"])}, METRICS)
    assert [(p.drill, p.reason) for p in problems] == [("pb.test.drop-ladder", "progression cycle")]
    assert "pb.test.drop-ladder -> pb.test.drop-ladder" in problems[0].detail


def test_a_longer_progression_cycle_is_named() -> None:
    a = a_drill("pb.test.a", progressions=["pb.test.b"])
    b = a_drill("pb.test.b", progressions=["pb.test.c"])
    c = a_drill("pb.test.c", progressions=["pb.test.a"])
    found = lint(a, b, c)
    assert found == [("pb.test.a", "progression cycle")]


def test_progression_and_regression_pointing_at_each_other_is_not_a_cycle() -> None:
    a = a_drill("pb.test.a", progressions=["pb.test.b"])
    b = a_drill("pb.test.b", regressions=["pb.test.a"])
    assert lint(a, b) == []


def test_a_regression_cycle_fails() -> None:
    assert lint(a_drill(regressions=["pb.test.drop-ladder"])) == [
        ("pb.test.drop-ladder", "regression cycle")
    ]


def test_an_unknown_progression_or_regression_fails() -> None:
    assert lint(a_drill(progressions=["pb.test.nope"], regressions=["pb.test.gone"])) == [
        ("pb.test.drop-ladder", "unknown progression"),
        ("pb.test.drop-ladder", "unknown regression"),
    ]


@pytest.mark.parametrize("field", ["duration_min", "duration_max"])
def test_a_duration_of_46_minutes_fails(field: str) -> None:
    assert ("pb.test.drop-ladder", "duration over 45") in lint(a_drill(**{field: 46}))


def test_45_minutes_is_allowed() -> None:
    assert lint(a_drill(duration_min=45, duration_max=45)) == []


def test_duration_min_above_max_fails() -> None:
    assert lint(a_drill(duration_min=20, duration_max=10)) == [
        ("pb.test.drop-ladder", "duration range")
    ]


@pytest.mark.parametrize("criterion", ["Most drops land in the kitchen", "eight of ten", ""])
def test_a_success_criterion_without_a_number_fails(criterion: str) -> None:
    assert lint(a_drill(success_criterion=criterion)) == [
        ("pb.test.drop-ladder", "criterion no number")
    ]


def test_neither_source_nor_rationale_fails() -> None:
    drill = a_drill()
    del drill["coach_rationale"]
    assert lint(drill) == [("pb.test.drop-ladder", "no source")]


def test_blank_source_and_rationale_count_as_missing() -> None:
    assert lint(a_drill(coach_rationale="  ", source="")) == [("pb.test.drop-ladder", "no source")]


def test_a_rationale_must_be_labelled_judgment() -> None:
    assert lint(a_drill(coach_rationale="Because it works")) == [
        ("pb.test.drop-ladder", "rationale not labelled")
    ]


def test_a_source_alone_is_enough() -> None:
    drill = a_drill(source="QD/QD-DR-01")
    del drill["coach_rationale"]
    assert lint(drill) == []


def test_the_valid_drill_passes() -> None:
    assert lint(a_drill()) == []


# --------------------------------------------------------------- schema (QD-DR-01)
@pytest.mark.parametrize(
    ("change", "path"),
    [
        ({"target_metrics": []}, "target_metrics"),
        ({"players": 5}, "players"),
        ({"level_min": "pro"}, "level_min"),
        ({"needs": ["trampoline"]}, "needs[0]"),
        ({"version": 0}, "version"),
        ({"id": "Drop Ladder"}, "id"),
        ({"review_status": "approved"}, "review_status"),
        ({"surprise": 1}, "surprise"),
    ],
)
def test_schema_violations_name_the_field(change: dict[str, Any], path: str) -> None:
    problems = lint_drills({"d.json": a_drill(**change)}, METRICS)
    assert [p.reason for p in problems] == ["schema"]
    assert path in problems[0].detail


def test_a_missing_required_field_is_named() -> None:
    drill = a_drill()
    del drill["setup"]
    problems = lint_drills({"d.json": drill}, METRICS)
    assert [p.reason for p in problems] == ["schema"]
    assert "setup" in problems[0].detail


def test_a_document_that_is_not_an_object_is_refused() -> None:
    problems = lint_drills({"d.json": ["not", "a", "drill"]}, METRICS)
    assert [(p.source, p.reason) for p in problems] == [("d.json", "schema")]


def test_level_min_above_level_max_fails() -> None:
    assert lint(a_drill(level_min="advanced", level_max="beginner")) == [
        ("pb.test.drop-ladder", "level range")
    ]


def test_the_same_id_and_version_twice_fails() -> None:
    docs = {"a.json": a_drill(), "b.json": a_drill(name="Other")}
    assert [p.reason for p in lint_drills(docs, METRICS)] == ["duplicate version"]


# --------------------------------------------------------------- deprecated_by
def test_deprecated_by_must_name_an_existing_drill_version() -> None:
    assert lint(a_drill(deprecated_by="pb.test.drop-ladder@2")) == [
        ("pb.test.drop-ladder", "unknown deprecated_by")
    ]


def test_a_deprecated_version_with_its_successor_passes() -> None:
    v1 = a_drill(deprecated_by="pb.test.drop-ladder@2")
    v2 = a_drill(version=2, success_criterion="9 of 10 drops bounce in the kitchen")
    assert lint(v1, v2) == []
