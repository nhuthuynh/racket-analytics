"""Drill immutability against ``library.lock`` (ST-053; FR-140: deprecated, never deleted;
edits bump the version; QD-DR-02). Pure: drills arrive as parsed JSON.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from racket.coaching.drills.lock import check_library, content_digest, lock_entries, lock_update
from tests.unit.coaching.drill_helpers import METRICS, a_drill

pytestmark = pytest.mark.unit


def lint(*drills: dict[str, Any], lock: dict[str, str]) -> list[tuple[str, str]]:
    docs = {f"{d.get('id')}@{d.get('version')}.json": d for d in drills}
    return [(p.drill or "", p.reason) for p in check_library(docs, METRICS, lock)]


def test_a_locked_drill_version_without_a_file_fails() -> None:
    v1, v2 = a_drill(deprecated_by="pb.test.drop-ladder@2"), a_drill(version=2)
    lock = lock_entries([v1, v2])
    assert lint(v2, lock=lock) == [("pb.test.drop-ladder", "deleted drill")]


def test_an_edit_without_a_version_bump_fails() -> None:
    drill = a_drill()
    lock = lock_entries([drill])
    edited = a_drill(success_criterion="7 of 10 drops bounce in the kitchen")
    assert lint(edited, lock=lock) == [("pb.test.drop-ladder", "edited without version bump")]


def test_status_and_deprecation_are_not_content_edits() -> None:
    drill = a_drill()
    lock = lock_entries([drill, a_drill(version=2)])
    later = a_drill(review_status="coach-reviewed", deprecated_by="pb.test.drop-ladder@2")
    assert lint(later, a_drill(version=2), lock=lock) == []


def test_a_drill_not_yet_in_the_lock_fails() -> None:
    assert lint(a_drill(), lock={}) == [("pb.test.drop-ladder", "not in lock")]


def test_content_digest_ignores_key_order() -> None:
    drill = a_drill()
    reordered = dict(reversed(list(copy.deepcopy(drill).items())))
    assert content_digest(drill) == content_digest(reordered)


# --------------------------------------------------------------- the lock only grows
def test_lock_update_adds_a_new_version_and_keeps_the_old_entries() -> None:
    v1, v2 = a_drill(deprecated_by="pb.test.drop-ladder@2"), a_drill(version=2)
    lock = lock_entries([v1])
    grown = lock_update({"v1.json": v1, "v2.json": v2}, METRICS, lock)
    assert grown == {**lock, **lock_entries([v2])}


def test_lock_update_refuses_an_edit_or_a_deletion() -> None:
    drill = a_drill()
    lock = lock_entries([drill])
    edited = a_drill(success_criterion="7 of 10 drops bounce in the kitchen")
    assert lock_update({"d.json": edited, "n.json": a_drill("pb.test.new")}, METRICS, lock) is None
    assert lock_update({"n.json": a_drill("pb.test.new")}, METRICS, lock) is None


def test_lock_update_refuses_a_library_with_rule_failures() -> None:
    assert lock_update({"d.json": a_drill(duration_max=50)}, METRICS, {}) is None


def test_lock_update_has_nothing_to_add_to_a_clean_library() -> None:
    drill = a_drill()
    assert lock_update({"d.json": drill}, METRICS, lock_entries([drill])) is None
