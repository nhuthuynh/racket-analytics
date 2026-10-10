"""Drill immutability against the base branch's lock (ST-053 review round 1, PE-R1-ST053-01;
FR-140; QD-DR-02). A PR may grow ``library.lock``, never remove or rewrite an entry the base
branch already has, so a deletion or an in-place edit cannot pass by changing the lock with it.
Also the lock text format (PE-R1-ST053-02, SBE-R1-01). Pure: drills and locks arrive parsed.
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.coaching.drills.lock import (
    LOCK_SCHEMA,
    base_lock_problems,
    check_library,
    lock_entries,
    lock_update,
    parse_lock,
    render_lock,
)
from tests.unit.coaching.drill_helpers import METRICS, a_drill

pytestmark = pytest.mark.unit

ID = "pb.test.drop-ladder"
EDIT = "7 of 10 drops bounce in the kitchen"


def lint(
    *drills: dict[str, Any], lock: dict[str, str], base: dict[str, str]
) -> list[tuple[str, str]]:
    docs = {f"{d.get('id')}@{d.get('version')}.json": d for d in drills}
    return sorted((p.drill or "", p.reason) for p in check_library(docs, METRICS, lock, base))


# ---------------------------------------------------------------- negative cases first
def test_deleting_a_base_version_with_its_lock_line_fails() -> None:
    v1, v2 = a_drill(deprecated_by=f"{ID}@2"), a_drill(version=2)
    base = lock_entries([v1, v2])
    lock = lock_entries([v2])  # the PR dropped the @1 line along with the file
    assert lint(v2, lock=lock, base=base) == [(ID, "deleted drill"), (ID, "lock entry removed")]


def test_an_in_place_edit_with_a_rewritten_lock_line_fails() -> None:
    drill, edited = a_drill(), a_drill(success_criterion=EDIT)
    base = lock_entries([drill])
    lock = lock_entries([edited])  # the PR rewrote the digest to match the edit
    assert lint(edited, lock=lock, base=base) == [
        (ID, "edited without version bump"),
        (ID, "lock entry changed"),
    ]


def test_a_lock_rebuilt_from_the_files_left_fails() -> None:
    v1, v2 = a_drill(deprecated_by=f"{ID}@2"), a_drill(version=2)
    base = lock_entries([v1, v2])
    assert (ID, "lock entry removed") in lint(v2, lock={}, base=base)


def test_base_lock_problems_name_the_lock_and_the_version() -> None:
    drill = a_drill()
    base = lock_entries([drill])
    [removed] = base_lock_problems({}, base)
    assert (removed.source, removed.drill, removed.reason) == (
        "library.lock",
        ID,
        "lock entry removed",
    )
    assert f"{ID}@1" in removed.detail


def test_lock_update_refuses_to_cover_a_base_deletion_or_edit() -> None:
    drill, edited = a_drill(), a_drill(success_criterion=EDIT)
    base = lock_entries([drill])
    new = a_drill("pb.test.new")
    assert (
        lock_update({"d.json": edited, "n.json": new}, METRICS, lock_entries([edited]), base)
        is None
    )
    assert lock_update({"n.json": new}, METRICS, {}, base) is None


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        '{"schema": "drill-library-lock/v0", "drills": {}}',
        f'{{"schema": "{LOCK_SCHEMA}"}}',
        f'{{"schema": "{LOCK_SCHEMA}", "drills": {{"a@1": 1}}}}',
    ],
)
def test_a_lock_that_is_not_a_v1_lock_is_refused(text: str) -> None:
    with pytest.raises(ValueError, match=r"base\.lock"):
        parse_lock(text, "base.lock")


# ---------------------------------------------------------------- positive cases
def test_a_new_version_on_top_of_the_base_lock_passes() -> None:
    v1, v2 = a_drill(deprecated_by=f"{ID}@2"), a_drill(version=2)
    base = lock_entries([a_drill()])  # deprecating v1 is a lifecycle change, not an edit
    lock = {**base, **lock_entries([v2])}
    assert lint(v1, v2, lock=lock, base=base) == []


def test_lock_update_adds_a_new_version_on_top_of_the_base_lock() -> None:
    drill, new = a_drill(), a_drill("pb.test.new")
    base = lock_entries([drill])
    grown = lock_update({"d.json": drill, "n.json": new}, METRICS, base, base)
    assert grown == {**base, **lock_entries([new])}


def test_no_base_lock_is_the_lock_alone() -> None:
    drill = a_drill()
    lock = lock_entries([drill])
    assert lint(drill, lock=lock, base={}) == []
    assert base_lock_problems(lock, {}) == []


def test_render_then_parse_is_the_same_lock_sorted_by_version() -> None:
    lock = lock_entries([a_drill(version=2), a_drill()])
    text = render_lock(lock)
    assert parse_lock(text, "library.lock") == lock
    assert text.index(f"{ID}@1") < text.index(f"{ID}@2")
    assert text.endswith("}\n")
    assert f'"schema": "{LOCK_SCHEMA}"' in text
