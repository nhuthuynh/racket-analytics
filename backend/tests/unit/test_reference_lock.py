"""Unit tests of the reference-set lock (ST-170a; FR-170.R2): a published version never changes.

Negative cases first. ``check_lock(docs, lock, base)`` takes the parsed version files by path,
the lock ``{"<set>@<N>": sha256}`` and the base branch's lock.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.support.references import LOCK, digest, entry, reference_doc

pytestmark = pytest.mark.unit

V1 = "pb-reference/v1.json"
V2 = "pb-reference/v2.json"


def _docs() -> dict[str, Any]:
    return {V1: reference_doc([entry()]), V2: reference_doc([entry(band=[0.4, 0.65])], 2)}


def _locked(docs: dict[str, Any]) -> dict[str, str]:
    return {f"{d['set']}@{d['version']}": digest(d) for d in docs.values()}


def _check(docs: Any, lock: Any, base: Any = None) -> list[tuple[str, str, str]]:
    found = LOCK.load().check_lock(docs, lock, base or {})
    return [(p.entry, p.field, p.reason) for p in found]


def test_an_edited_published_version_is_refused() -> None:
    docs = _docs()
    lock = _locked(docs)
    docs[V1]["entries"][0]["band"] = [0.5, 0.75]

    assert ("pb-reference@1", "version", "published version changed") in _check(docs, lock)


def test_a_deleted_published_version_is_refused() -> None:
    docs = _docs()
    lock = _locked(docs)
    del docs[V1]

    assert any(
        e == "pb-reference@1" and "published version deleted" in r for e, _, r in _check(docs, lock)
    )


def test_a_version_missing_from_the_lock_is_refused() -> None:
    docs = _docs()
    lock = _locked(docs)
    del lock["pb-reference@2"]

    assert any(e == "pb-reference@2" and "not in lock" in r for e, _, r in _check(docs, lock))


def test_a_base_lock_entry_removed_or_rewritten_is_refused() -> None:
    docs = _docs()
    base = _locked(docs)
    docs[V1]["entries"][0]["band"] = [0.5, 0.75]
    rewritten = _locked(docs)

    problems = _check(docs, rewritten, base)
    assert ("pb-reference@1", "version", "lock entry changed") in problems
    assert ("pb-reference@1", "version", "published version changed") in problems

    del docs[V1]
    gone = _locked(docs)
    assert ("pb-reference@1", "version", "lock entry removed") in _check(docs, gone, base)


def test_a_new_version_next_to_a_locked_one_passes() -> None:
    docs = _docs()

    assert _check(docs, _locked(docs), {"pb-reference@1": digest(docs[V1])}) == []


def test_lock_update_adds_only_new_versions() -> None:
    lock_module = LOCK.load()
    docs = _docs()
    old = {"pb-reference@1": "0" * 64}

    grown = lock_module.lock_update(docs, old)

    assert grown == {"pb-reference@1": "0" * 64, "pb-reference@2": digest(docs[V2])}


def test_the_digest_is_sha256_of_canonical_json() -> None:
    doc = reference_doc([entry()])

    assert LOCK.load().digest(doc) == digest(doc)


@pytest.mark.parametrize(
    "text",
    ["", "[]", '{"schema": "other", "sets": {}}', '{"schema": "reference-set-lock/v1"}',
     '{"schema": "reference-set-lock/v1", "sets": {"a@1": 3}}'],
)  # fmt: skip
def test_an_unreadable_lock_raises(text: str) -> None:
    lock_module = LOCK.load()

    with pytest.raises(lock_module.LockError):
        lock_module.parse_lock(text, "references.lock")
