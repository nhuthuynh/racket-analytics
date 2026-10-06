"""The metric dictionary in code: versioned entries AN-01..AN-07 with a status; only
``coach-reviewed`` and ``verified`` entries are published (ST-043; FR-102; NFR-075).

sprint-03 §5 TDD order: 1. unknown status -> error; 2. duplicate id -> error; 3. draft entries
filtered out of the published set; 4. version bump on a definition change (fixture diff against
``metrics.lock.json``). The shipped file mirrors ``docs/domain/metric-dictionary.md`` v0.1.
"""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from racket.sports.pickleball.metrics import (
    LOCK_PATH,
    METRICS_PATH,
    STATUSES,
    InvalidDictionary,
    MetricDictionary,
    definition_digest,
    load_dictionary,
)

pytestmark = pytest.mark.unit


def raw() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    return copy.deepcopy(data)


# ---------------------------------------------------------------- 1, 2: refused
def test_an_unknown_status_is_refused() -> None:
    data = raw()
    data["entries"][0]["status"] = "approved"
    with pytest.raises(InvalidDictionary, match="AN-01: unknown status"):
        MetricDictionary.parse(data)


def test_a_duplicate_id_is_refused() -> None:
    data = raw()
    data["entries"][1]["id"] = "AN-01"
    with pytest.raises(InvalidDictionary, match="duplicate id AN-01"):
        MetricDictionary.parse(data)


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("id", "AN-1", "id"),
        ("version", "", "version"),
        ("version", "one", "version"),
        ("name", "", "name"),
        ("definition", None, "definition"),
        ("min_sample", {"unit": "rallies", "n": 0}, "min_sample"),
        ("data_level", "FT", "data_level"),
    ],
)
def test_a_malformed_entry_is_refused(field: str, value: object, reason: str) -> None:
    data = raw()
    data["entries"][2][field] = value
    with pytest.raises(InvalidDictionary, match=reason):
        MetricDictionary.parse(data)


def test_a_missing_field_is_refused() -> None:
    data = raw()
    del data["entries"][3]["formula"]
    with pytest.raises(InvalidDictionary, match="AN-04: formula"):
        MetricDictionary.parse(data)


def test_an_unknown_field_is_refused() -> None:
    data = raw()
    data["entries"][0]["colour"] = "red"
    with pytest.raises(InvalidDictionary, match="AN-01: unknown field"):
        MetricDictionary.parse(data)


# ---------------------------------------------------------------- 3: draft never published
def test_draft_entries_are_not_published() -> None:
    data = raw()
    for entry in data["entries"]:
        entry["status"] = "draft"
    data["entries"][0]["status"] = "coach-reviewed"
    data["entries"][4]["status"] = "verified"
    dictionary = MetricDictionary.parse(data)
    assert [e.id for e in dictionary.published()] == ["AN-01", "AN-05"]
    assert dictionary.is_published("AN-01") is True
    assert dictionary.is_published("AN-02") is False
    assert dictionary.is_published("AN-99") is False


def test_the_statuses_are_the_dictionary_lifecycle() -> None:
    assert STATUSES == ("draft", "coach-reviewed", "verified", "deprecated")


def test_a_deprecated_entry_is_not_published() -> None:
    data = raw()
    data["entries"][0]["status"] = "deprecated"
    assert "AN-01" not in [e.id for e in MetricDictionary.parse(data).published()]


# ---------------------------------------------------------------- the shipped file
def test_the_shipped_dictionary_has_an_01_to_an_07_v0_1() -> None:
    dictionary = load_dictionary()
    assert [e.id for e in dictionary.entries] == [f"AN-0{i}" for i in range(1, 8)]
    assert dictionary.version == "0.1"
    assert all(e.version == "0.1" for e in dictionary.entries)
    assert dictionary.sport == "pickleball"


def test_the_shipped_statuses_match_the_review_record() -> None:
    """Only the coach moves an entry (metric-dictionary §3); on 2026-10-06 every entry is draft."""
    dictionary = load_dictionary()
    assert {e.id: e.status for e in dictionary.entries} == dict.fromkeys(
        [f"AN-0{i}" for i in range(1, 8)], "draft"
    )


def test_the_how_is_this_measured_text_is_the_coach_definition() -> None:
    an01 = load_dictionary().entry("AN-01")
    assert an01.definition == "Of the rallies your side served, the share your side won."
    assert an01.name == "Rallies won on serve"
    assert an01.min_sample == {"unit": "rallies", "n": 20}


def test_the_public_view_carries_what_the_card_needs() -> None:
    view = load_dictionary().entry("AN-03").public()
    assert set(view) == {"id", "version", "name", "definition", "unit", "min_sample", "status"}


# ---------------------------------------------------------------- 4: version bump guard
def test_every_definition_change_bumps_its_version() -> None:
    """A definition changed without a version bump fails here (NFR-075: old snapshots keep
    their version). After a bump, update ``metrics.lock.json`` in the same commit."""
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    dictionary = load_dictionary()
    assert lock["version"] == dictionary.version, "dictionary version changed: update the lock"
    for entry in dictionary.entries:
        locked = lock["entries"][entry.id]
        if definition_digest(entry) != locked["digest"]:
            assert entry.version != locked["version"], f"{entry.id} changed without a bump"
        assert entry.version == locked["version"], f"{entry.id}: update metrics.lock.json"
        assert definition_digest(entry) == locked["digest"], f"{entry.id}: update the lock"


def test_the_guard_catches_a_silent_definition_change() -> None:
    data = raw()
    data["entries"][0]["formula"] = "something else"
    changed = MetricDictionary.parse(data).entry("AN-01")
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    assert definition_digest(changed) != lock["entries"]["AN-01"]["digest"]
    assert changed.version == lock["entries"]["AN-01"]["version"]  # the guard above would fail


def test_status_is_not_part_of_the_definition() -> None:
    data = raw()
    before = MetricDictionary.parse(data).entry("AN-02")
    data["entries"][1]["status"] = "coach-reviewed"
    after = MetricDictionary.parse(data).entry("AN-02")
    assert definition_digest(before) == definition_digest(after)


def test_a_descriptive_metric_has_no_minimum_sample() -> None:
    assert load_dictionary().entry("AN-06").min_sample is None
