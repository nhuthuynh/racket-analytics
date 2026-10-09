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
    DefinitionLock,
    InvalidDictionary,
    MetricDictionary,
    definition_digest,
    load_dictionary,
    low_sample_digest,
    version_bump_violations,
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
    """Only the coach moves an entry (metric-dictionary §3); since 2026-10-07 (COACH-1, ADR 0044)
    every entry is coach-reviewed (TCR row PD-R2S3-01 / PE-R2S3-05)."""
    dictionary = load_dictionary()
    assert {e.id: e.status for e in dictionary.entries} == dict.fromkeys(
        [f"AN-0{i}" for i in range(1, 8)], "coach-reviewed"
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
# ``version_bump_violations`` is the NFR-075 guard (pure). The lock is append-only, keyed by
# (id, version) -> digest; ``previous`` is the lock on main (the integration test reads it from
# the merge base with git), so a digest overwritten in place is caught (PE-ST043-01, SQA-3).
def lock() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    return copy.deepcopy(data)


def violations(
    data: dict[str, Any], current: dict[str, Any], previous: dict[str, Any] | None = None
) -> tuple[str, ...]:
    return version_bump_violations(
        MetricDictionary.parse(data),
        DefinitionLock.parse(current),
        previous=None if previous is None else DefinitionLock.parse(previous),
    )


def digest_of(data: dict[str, Any], entry_id: str) -> str:
    return definition_digest(MetricDictionary.parse(data).entry(entry_id))


def bump_an01(data: dict[str, Any], current: dict[str, Any], version: str = "0.2") -> None:
    data["entries"][0]["formula"] = "rallies won by S / all rallies"
    data["entries"][0]["version"] = version
    current["entries"]["AN-01"][version] = digest_of(data, "AN-01")


def test_a_definition_change_without_a_bump_is_a_violation() -> None:
    data = raw()
    data["entries"][0]["formula"] = "rallies won by S / all rallies"
    assert violations(data, lock()) == ("AN-01 0.1: definition changed without a version bump",)


def test_a_digest_rewritten_in_place_is_a_violation_against_the_previous_lock() -> None:
    """The reviewer's bypass: new formula, new digest pasted over 0.1, no bump."""
    data, current, previous = raw(), lock(), lock()
    data["entries"][0]["formula"] = "rallies won by S / all rallies"
    current["entries"]["AN-01"]["0.1"] = digest_of(data, "AN-01")
    assert violations(data, current) == ()  # the lock alone agrees with the file ...
    assert violations(data, current, previous) == (  # ... but history says otherwise
        "AN-01 0.1: locked digest rewritten; the lock is append-only, bump the version",
    )


def test_a_removed_lock_row_is_a_violation_against_the_previous_lock() -> None:
    previous, current = lock(), lock()
    previous["entries"]["AN-02"]["0.0"] = "0" * 64
    assert "AN-02 0.0: locked row removed; the lock is append-only" in violations(
        raw(), current, previous
    )


def test_an_unrecorded_version_is_a_violation() -> None:
    data = raw()
    data["entries"][0]["version"] = "0.2"
    data["version"] = "0.2"
    current = lock()
    current["version"] = "0.2"
    assert violations(data, current) == ("AN-01 0.2: not recorded in metrics.lock.json",)


def test_an_entry_bump_without_a_dictionary_bump_is_a_violation() -> None:
    data, current = raw(), lock()
    bump_an01(data, current)
    assert violations(data, current) == (
        "dictionary 0.1: older than entry AN-01 0.2; bump the dictionary version",
    )


def test_a_new_definition_without_a_dictionary_bump_since_main_is_a_violation() -> None:
    data, current, previous = raw(), lock(), lock()
    data["version"] = "0.2"
    current["version"] = "0.2"
    previous["version"] = "0.2"
    bump_an01(data, current)
    assert violations(data, current, previous) == (
        "dictionary 0.2: definitions changed since the previous lock 0.2; bump the dictionary",
    )


def test_a_lock_for_another_dictionary_version_is_a_violation() -> None:
    current = lock()
    current["version"] = "0.3"
    assert violations(raw(), current) == ("dictionary 0.1: metrics.lock.json is for 0.3",)


def test_a_bumped_definition_recorded_in_the_lock_passes() -> None:
    data, current, previous = raw(), lock(), lock()
    bump_an01(data, current)
    data["version"] = "0.2"
    current["version"] = "0.2"
    assert violations(data, current, previous) == ()


def test_a_malformed_lock_is_refused() -> None:
    current = lock()
    current["entries"]["AN-01"] = {"0.1": "not-a-digest"}
    with pytest.raises(InvalidDictionary, match=r"AN-01 0\.1: digest"):
        DefinitionLock.parse(current)


def test_the_shipped_dictionary_matches_its_lock() -> None:
    assert violations(raw(), lock()) == ()


def test_status_is_not_part_of_the_definition() -> None:
    data = raw()
    before = MetricDictionary.parse(data).entry("AN-02")
    data["entries"][1]["status"] = "coach-reviewed"
    after = MetricDictionary.parse(data).entry("AN-02")
    assert definition_digest(before) == definition_digest(after)


def test_a_descriptive_metric_has_no_minimum_sample() -> None:
    assert load_dictionary().entry("AN-06").min_sample is None


# ---------------------------------------------------------------- 5: the low-sample rule (ADR 0041)
# The interval-width rule is a top-level, digested dictionary field; changing it needs a new
# dictionary version recorded in the lock's ``low_sample`` rows (NFR-075; §5.2 item 2).
@pytest.mark.parametrize(
    "rule",
    [None, {}, {"max_interval_width": 0}, {"max_interval_width": 1.5},
     {"max_interval_width": "0.3"}, {"max_interval_width": True},
     {"max_interval_width": 0.3, "min_n": 20}],
)  # fmt: skip
def test_a_missing_or_nonsense_low_sample_rule_is_refused(rule: object) -> None:
    data = raw()
    if rule is None:
        del data["low_sample"]
    else:
        data["low_sample"] = rule
    with pytest.raises(InvalidDictionary, match="low_sample"):
        MetricDictionary.parse(data)


def test_a_low_sample_rule_changed_without_a_bump_is_a_violation() -> None:
    data = raw()
    data["low_sample"] = {"max_interval_width": 0.4}
    assert violations(data, lock()) == (
        "low_sample: the interval-width rule changed without a dictionary version bump",
    )


def test_a_low_sample_digest_rewritten_in_place_is_a_violation_against_the_previous_lock() -> None:
    data, current, previous = raw(), lock(), lock()
    data["low_sample"] = {"max_interval_width": 0.4}
    current["low_sample"]["0.1"] = low_sample_digest(MetricDictionary.parse(data))
    assert violations(data, current) == ()
    assert violations(data, current, previous) == (
        "low_sample 0.1: locked digest rewritten; the lock is append-only, bump the version",
    )


def test_a_low_sample_rule_change_recorded_under_a_new_dictionary_version_passes() -> None:
    data, current, previous = raw(), lock(), lock()
    data["low_sample"] = {"max_interval_width": 0.4}
    data["version"] = current["version"] = "0.2"
    current["low_sample"]["0.2"] = low_sample_digest(MetricDictionary.parse(data))
    assert violations(data, current, previous) == ()


def test_a_lock_without_a_low_sample_row_is_a_violation() -> None:
    current = lock()
    del current["low_sample"]
    assert violations(raw(), current) == ("low_sample: not recorded in metrics.lock.json",)


def test_the_shipped_low_sample_rule_is_rule_0_3() -> None:
    assert load_dictionary().low_sample == {"max_interval_width": 0.30}
