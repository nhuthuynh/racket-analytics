"""``MetricSnapshot`` (ST-046; analytics-snapshots.md §2-§5; ADR 0040, ADR 0041).

Negative cases first: a dictionary whose thresholds do not fit refuses to build a policy; a
draft entry never reaches the published view; the same sheet version twice is not "behind".
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest

from racket.analytics.snapshot import MetricSnapshot, SnapshotKey, policy_from_dictionary
from racket.analytics.starter_stats import starter_stats
from racket.analytics.uncertainty import InvalidPolicy, LowSamplePolicy
from racket.sports.pickleball.metrics import MetricDictionary, load_dictionary
from tests.unit.analytics.sheets import WORKED_EXAMPLE, one_game

pytestmark = [pytest.mark.unit]

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
MATCH = uuid.UUID("11111111-1111-4111-8111-111111111111")
OWNER = uuid.UUID("22222222-2222-4222-8222-222222222222")


def _dictionary(**changes: Any) -> MetricDictionary:
    shipped = load_dictionary()
    entries = []
    for entry in shipped.entries:
        change = changes.get(entry.id)
        entries.append(entry if change is None else replace(entry, **change))
    return replace(shipped, entries=tuple(entries))


def _snapshot(dictionary: MetricDictionary | None = None, version: int = 15) -> MetricSnapshot:
    return MetricSnapshot.compute(
        match_id=MATCH,
        owner_id=OWNER,
        sheet=one_game(WORKED_EXAMPLE),
        sheet_version=version,
        dictionary=dictionary or _dictionary(),
        now=NOW,
    )


def test_a_proportion_threshold_that_differs_between_entries_is_refused() -> None:
    # One policy serves every proportion metric; two different n would make a card show a
    # min_sample that did not set its flag (ADR 0041, invariant S6), so it fails closed.
    odd = _dictionary(**{"AN-05": {"min_sample": {"unit": "rallies", "n": 30}}})
    with pytest.raises(InvalidPolicy, match="AN-05"):
        policy_from_dictionary(odd)


def test_a_min_sample_unit_that_does_not_fit_the_metric_is_refused() -> None:
    odd = _dictionary(**{"AN-03": {"min_sample": {"unit": "games", "n": 10}}})
    with pytest.raises(InvalidPolicy, match="AN-03"):
        policy_from_dictionary(odd)


def test_the_shipped_dictionary_gives_the_adr_0005_policy() -> None:
    assert policy_from_dictionary(load_dictionary()) == LowSamplePolicy()


def test_the_dictionary_thresholds_set_the_flags() -> None:
    strict = _dictionary(
        **{
            e: {"min_sample": {"unit": "rallies", "n": 2}}
            for e in ("AN-01", "AN-02", "AN-05", "AN-07")
        }
    )
    assert policy_from_dictionary(strict).min_proportion_n == 2


def test_the_key_names_match_dictionary_and_rules_versions() -> None:
    snap = _snapshot()
    assert snap.key == SnapshotKey(MATCH, load_dictionary().version, "PROVISIONAL-UNVERIFIED")
    assert (snap.owner_id, snap.sheet_version, snap.computed_at) == (OWNER, 15, NOW)


def test_the_stats_equal_starter_stats_of_the_sheet() -> None:
    assert _snapshot().stats == starter_stats(one_game(WORKED_EXAMPLE))


def test_the_same_inputs_give_an_equal_snapshot() -> None:
    assert _snapshot() == _snapshot()


def test_a_snapshot_is_behind_only_an_newer_sheet_version() -> None:
    snap = _snapshot(version=15)
    assert snap.is_behind(16)
    assert not snap.is_behind(15)
    assert not snap.is_behind(14)


def test_a_draft_entry_never_reaches_the_published_view() -> None:
    dictionary = _dictionary(**{"AN-05": {"status": "draft"}})
    view = _snapshot(dictionary).published_view(dictionary)
    assert "AN-05" not in view
    assert sorted(view) == ["AN-01", "AN-02", "AN-03", "AN-04", "AN-06", "AN-07"]


def test_the_published_view_has_the_entry_and_the_sides_without_rallies() -> None:
    dictionary = _dictionary()
    view = _snapshot(dictionary).published_view(dictionary)
    an01 = view["AN-01"]
    assert an01["entry"] == dictionary.entry("AN-01").public()
    assert (an01["A"]["k"], an01["A"]["n"]) == (4, 7)
    assert all("rallies" not in view[m][s] for m in view for s in ("A", "B"))


def test_the_rallies_behind_a_metric_and_side_come_from_the_stats() -> None:
    snap = _snapshot()
    assert snap.rallies("AN-01", "A") == snap.stats["AN-01"]["A"]["rallies"]
    with pytest.raises(KeyError):
        snap.rallies("AN-99", "A")
