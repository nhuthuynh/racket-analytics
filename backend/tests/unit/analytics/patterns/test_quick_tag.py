"""Quick Tag adapter over AN-01..AN-07 (ST-171a; FR-171.R1, R5, R6; ADR 0061 Rule 1).

The adapter reuses ``starter_stats`` and ``uncertainty`` unchanged: every measure equals the
starter stat it comes from (value, n, interval, low_sample). Negative cases first: a Full Tag
or vision pattern on a Quick Tag-only match is unavailable with a reason, never 0 (FR-171.R5);
a measure below its min_n is flagged and not rankable (FR-171.R6); AN-03, AN-04 and AN-06 have
no interval method, so they are never rankable (ADR 0061 Rule 3.1).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from racket.analytics.patterns.quick_tag import (
    QUICK_TAG_PATTERNS,
    UnknownDataSource,
    quick_tag_measures,
)
from racket.analytics.snapshot import policy_from_dictionary
from racket.analytics.starter_stats import starter_stats
from racket.analytics.uncertainty import Interval
from racket.sports.pickleball.metrics import MetricDictionary, load_dictionary
from tests.unit.analytics.sheets import WORKED_EXAMPLE, a_serves_and_wins_25, one_game, sheet

pytestmark = [pytest.mark.unit]

DICTIONARY = load_dictionary()


def _stats(s: dict[str, Any], dictionary: MetricDictionary = DICTIONARY) -> Any:
    return starter_stats(s, policy_from_dictionary(dictionary))


# ---------------------------------------------------------------- negative first: FR-171.R5
def test_a_full_tag_pattern_on_a_quick_tag_only_match_is_unavailable_never_zero() -> None:
    measures = quick_tag_measures(one_game(WORKED_EXAMPLE), DICTIONARY,
                                  other_patterns={"AN-09": ("FT", "0.1")})  # fmt: skip
    for side in ("A", "B"):
        m = measures["AN-09"][side]
        assert m.value is None, "AN-09 on a Quick Tag-only match was given a value"
        assert m.value != 0
        assert (m.unavailable_reason, m.n, m.rankable) == ("no_shot_facets", 0, False)
        assert m.definition_version == "0.1"


def test_a_vision_pattern_on_a_quick_tag_only_match_needs_cv() -> None:
    measures = quick_tag_measures(one_game(WORKED_EXAMPLE), DICTIONARY,
                                  other_patterns={"AN-11": ("CV", "0.1")})  # fmt: skip
    assert measures["AN-11"]["A"].unavailable_reason == "needs_cv"


def test_an_unknown_data_source_is_refused() -> None:
    with pytest.raises(UnknownDataSource, match="AN-09"):
        quick_tag_measures(one_game(WORKED_EXAMPLE), DICTIONARY,
                           other_patterns={"AN-09": ("XX", "0.1")})  # fmt: skip


def test_a_quick_tag_pattern_cannot_be_declared_unavailable() -> None:
    with pytest.raises(UnknownDataSource, match="AN-01"):
        quick_tag_measures(one_game(WORKED_EXAMPLE), DICTIONARY,
                           other_patterns={"AN-01": ("FT", "0.1")})  # fmt: skip


# ---------------------------------------------------------------- negative first: FR-171.R6
def test_below_min_n_the_measure_is_low_sample_and_not_rankable() -> None:
    m = quick_tag_measures(one_game(WORKED_EXAMPLE), DICTIONARY)["AN-01"]["A"]
    assert (m.n, m.low_sample, m.rankable) == (7, True, False)


def test_at_min_n_with_a_narrow_interval_the_measure_is_rankable() -> None:
    m = quick_tag_measures(a_serves_and_wins_25(), DICTIONARY)["AN-01"]["A"]
    assert (m.n, m.value, m.low_sample, m.rankable) == (25, 1.0, False, True)


def test_min_n_comes_from_the_dictionary() -> None:
    # AN-01 needs 26 rallies in this dictionary: n = 25 is now a low sample (ADR 0041)
    entries = tuple(
        replace(e, min_sample={"unit": "rallies", "n": 26}) if e.id == "AN-01" else e
        for e in DICTIONARY.entries
    )
    stricter = replace(DICTIONARY, entries=entries)
    m = quick_tag_measures(a_serves_and_wins_25(), stricter)["AN-01"]["A"]
    assert (m.low_sample, m.rankable) == (True, False)


@pytest.mark.parametrize("pattern", ["AN-03", "AN-04", "AN-06"])
def test_measures_without_an_interval_method_are_never_rankable(pattern: str) -> None:
    for side in ("A", "B"):
        m = quick_tag_measures(a_serves_and_wins_25(), DICTIONARY)[pattern][side]
        assert (m.interval, m.interval_method, m.rankable) == (None, None, False)
        assert m.available


# ---------------------------------------------------------------- FR-171.R1: equal to starter stats
def test_the_quick_tag_patterns_are_an_01_to_an_07_with_the_an_07_shares() -> None:
    assert QUICK_TAG_PATTERNS == (
        "AN-01", "AN-02", "AN-03", "AN-04", "AN-05", "AN-06",
        "AN-07:winner", "AN-07:unforced-error", "AN-07:forced-error", "AN-07:fault",
    )  # fmt: skip


def test_the_worked_example_an_01_equals_the_coach_s_hand_count() -> None:
    m = quick_tag_measures(one_game(WORKED_EXAMPLE), DICTIONARY)["AN-01"]["A"]
    assert (m.pattern_id, m.value, m.n) == ("AN-01", 0.5714, 7)
    assert m.interval == Interval(0.2505, 0.8418)
    assert (m.interval_method, m.definition_version, m.n_excluded) == ("wilson", "0.1", 0)


@pytest.mark.parametrize("metric", ["AN-01", "AN-02", "AN-05"])
@pytest.mark.parametrize("side", ["A", "B"])
def test_proportions_equal_the_starter_stats(metric: str, side: str) -> None:
    s = one_game(WORKED_EXAMPLE)
    want = _stats(s)[metric][side]
    m = quick_tag_measures(s, DICTIONARY)[metric][side]
    assert (m.value, m.n, m.low_sample, m.interval_method) == (
        want["value"], want["n"], want["low_sample"], "wilson",
    )  # fmt: skip
    assert m.interval == Interval(want["ci_low"], want["ci_high"])


@pytest.mark.parametrize(
    ("pattern", "category"),
    [
        ("AN-07:winner", "winner"),
        ("AN-07:unforced-error", "unforced_error"),
        ("AN-07:forced-error", "forced_error"),
        ("AN-07:fault", "fault"),
    ],
)
@pytest.mark.parametrize("side", ["A", "B"])
def test_an_07_shares_equal_the_starter_stats(pattern: str, category: str, side: str) -> None:
    s = one_game(WORKED_EXAMPLE)
    want = _stats(s)["AN-07"][side]
    share = want["shares"][category]
    m = quick_tag_measures(s, DICTIONARY)[pattern][side]
    assert (m.pattern_id, m.value, m.n, m.low_sample) == (
        pattern, share["value"], want["n"], want["low_sample"],
    )  # fmt: skip
    assert m.interval == Interval(share["ci_low"], share["ci_high"])
    assert m.interval_method == "wilson"


@pytest.mark.parametrize("side", ["A", "B"])
def test_an_03_is_points_per_service_turn_over_turns(side: str) -> None:
    s = one_game(WORKED_EXAMPLE)
    want = _stats(s)["AN-03"][side]
    m = quick_tag_measures(s, DICTIONARY)["AN-03"][side]
    assert (m.value, m.n, m.low_sample) == (want["value"], want["turns"], want["low_sample"])


@pytest.mark.parametrize("side", ["A", "B"])
def test_an_04_is_unforced_errors_per_game_over_games(side: str) -> None:
    s = one_game(WORKED_EXAMPLE)
    want = _stats(s)["AN-04"][side]
    m = quick_tag_measures(s, DICTIONARY)["AN-04"][side]
    assert (m.value, m.n, m.low_sample) == (want["value"], want["games"], want["low_sample"])


@pytest.mark.parametrize("side", ["A", "B"])
def test_an_06_is_the_longest_run_over_points_in_runs(side: str) -> None:
    s = one_game(WORKED_EXAMPLE)
    want = _stats(s)["AN-06"][side]
    m = quick_tag_measures(s, DICTIONARY)["AN-06"][side]
    assert (m.value, m.n, m.low_sample) == (want["longest"], want["n"], False)


def test_an_empty_match_has_no_values_but_is_not_unavailable() -> None:
    measures = quick_tag_measures(sheet([]), DICTIONARY)
    for pattern in QUICK_TAG_PATTERNS:
        for side in ("A", "B"):
            m = measures[pattern][side]
            assert m.unavailable_reason is None, pattern
            assert not m.rankable, pattern
    an01 = measures["AN-01"]["A"]
    assert (an01.value, an01.n, an01.interval, an01.low_sample) == (None, 0, None, True)


def test_each_measure_carries_its_entry_s_definition_version() -> None:
    entries = tuple(replace(e, version="0.2") if e.id == "AN-07" else e for e in DICTIONARY.entries)
    bumped = replace(DICTIONARY, entries=entries)
    measures = quick_tag_measures(one_game(WORKED_EXAMPLE), bumped)
    assert measures["AN-07:fault"]["A"].definition_version == "0.2"
    assert measures["AN-01"]["A"].definition_version == "0.1"


def test_every_side_of_every_quick_tag_pattern_is_measured() -> None:
    measures = quick_tag_measures(one_game(WORKED_EXAMPLE), DICTIONARY)
    assert tuple(measures) == QUICK_TAG_PATTERNS
    assert all(set(by_side) == {"A", "B"} for by_side in measures.values())
