"""Unit: the QA-REF-GOLD integrity rule (golden.lock.json; ADR 0061 Rule 6; NFR-078).

A frozen file may change only through a new lock row that names a new ADR which exists under
``docs/decisions/`` and names QA-REF-GOLD. In memory only: the reader and the ADR lookup are
dictionaries. Written red first: before QA-REF-GOLD nothing checks a golden pattern file.
"""

from __future__ import annotations

import hashlib
import importlib
from types import ModuleType
from typing import Any

import pytest

ADR_1 = "docs/decisions/0061-reference-patterns.md"
ADR_2 = "docs/decisions/0070-golden-patterns-v2.md"
VEC = "backend/tests/regression/golden_patterns/vectors/measures.gs-pat-1-v1.json"
FIX = "docs/domain/hand-counts/GS-PAT-1-v1.json"
OLD, NEW = b'{"v": 1}', b'{"v": 2}'


def _integrity() -> ModuleType:
    try:
        return importlib.import_module("tests.regression.golden_patterns.integrity")
    except ImportError as exc:
        pytest.fail(f"RED until QA-REF-GOLD: no integrity check ({exc})", pytrace=False)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def row(adr: str, files: dict[str, bytes], date: str = "2026-11-13") -> dict[str, Any]:
    return {
        "date": date,
        "ticket": "QA-REF-GOLD",
        "by": "senior-qa-engineer",
        "adr": adr,
        "reason": "freeze",
        "files": {path: sha(data) for path, data in files.items()},
    }


def lock(*rows: dict[str, Any]) -> dict[str, Any]:
    return {"schema": "golden-patterns-lock/v1", "changes": list(rows)}


ADRS = {ADR_1: "... QA-REF-GOLD vectors ...", ADR_2: "Supersedes the QA-REF-GOLD v1 vectors"}


def problems(
    the_lock: dict[str, Any],
    files: dict[str, bytes],
    adrs: dict[str, str] | None = None,
    present: tuple[str, ...] = (),
) -> list[str]:
    adrs = ADRS if adrs is None else adrs
    result: list[str] = _integrity().check(the_lock, files.get, adrs.get, present)
    return result


def test_frozen_files_with_their_adr_pass() -> None:
    assert problems(lock(row(ADR_1, {VEC: OLD, FIX: OLD})), {VEC: OLD, FIX: OLD}) == []


def test_an_edited_vector_without_a_lock_row_is_refused() -> None:
    found = problems(lock(row(ADR_1, {VEC: OLD})), {VEC: NEW})
    assert len(found) == 1
    assert VEC in found[0]
    assert "edited without an ADR" in found[0]


def test_an_edited_input_fixture_is_refused() -> None:
    found = problems(lock(row(ADR_1, {VEC: OLD, FIX: OLD})), {VEC: OLD, FIX: NEW})
    assert [p for p in found if FIX in p and "edited without an ADR" in p]


def test_a_new_row_with_a_new_adr_accepts_the_edit() -> None:
    the_lock = lock(row(ADR_1, {VEC: OLD}), row(ADR_2, {VEC: NEW}, date="2026-12-01"))
    assert problems(the_lock, {VEC: NEW}) == []


def test_a_row_naming_an_adr_that_does_not_exist_is_refused() -> None:
    missing = "docs/decisions/0099-no-such-adr.md"
    found = problems(lock(row(ADR_1, {VEC: OLD}), row(missing, {VEC: NEW})), {VEC: NEW})
    assert any(missing in p and "does not exist" in p for p in found)


def test_a_row_reusing_an_earlier_adr_is_refused() -> None:
    found = problems(lock(row(ADR_1, {VEC: OLD}), row(ADR_1, {VEC: NEW})), {VEC: NEW})
    assert any("already authorised change 1" in p for p in found)


def test_an_adr_that_does_not_name_the_golden_set_is_refused() -> None:
    adrs = {**ADRS, ADR_2: "an unrelated decision"}
    found = problems(lock(row(ADR_1, {VEC: OLD}), row(ADR_2, {VEC: NEW})), {VEC: NEW}, adrs)
    assert any(ADR_2 in p and "does not name QA-REF-GOLD" in p for p in found)


@pytest.mark.parametrize("adr", ["docs/0061.md", "0061-x.md", "docs/decisions/61-x.md", ""])
def test_a_row_whose_adr_is_not_a_decision_record_path_is_refused(adr: str) -> None:
    found = problems(lock(row(adr, {VEC: OLD})), {VEC: OLD}, {adr: "QA-REF-GOLD"})
    assert any("not a docs/decisions/NNNN-*.md path" in p for p in found)


def test_a_missing_frozen_file_is_refused() -> None:
    found = problems(lock(row(ADR_1, {VEC: OLD})), {})
    assert any(VEC in p and "missing" in p for p in found)


def test_a_golden_file_outside_the_lock_is_refused() -> None:
    extra = "backend/tests/regression/golden_patterns/vectors/new.json"
    found = problems(lock(row(ADR_1, {VEC: OLD})), {VEC: OLD, extra: OLD}, present=(extra,))
    assert any(extra in p and "not in the lock" in p for p in found)


@pytest.mark.parametrize(
    "the_lock",
    [
        {"schema": "other/v1", "changes": []},
        {"schema": "golden-patterns-lock/v1", "changes": []},
        {"schema": "golden-patterns-lock/v1"},
    ],
)
def test_a_lock_with_a_wrong_schema_or_no_change_is_refused(the_lock: dict[str, Any]) -> None:
    assert problems(the_lock, {})


@pytest.mark.parametrize("field", ["date", "ticket", "by", "adr", "reason", "files"])
def test_a_row_missing_a_field_is_refused(field: str) -> None:
    bad = row(ADR_1, {VEC: OLD})
    del bad[field]
    found = problems(lock(bad), {VEC: OLD})
    assert any(f"missing {field}" in p for p in found)


def test_rows_out_of_date_order_are_refused() -> None:
    the_lock = lock(row(ADR_1, {VEC: OLD}), row(ADR_2, {VEC: NEW}, date="2026-11-01"))
    assert any("date before change 1" in p for p in problems(the_lock, {VEC: NEW}))
