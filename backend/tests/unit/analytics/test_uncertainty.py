"""Uncertainty of the starter stats: Wilson interval and the low-sample rule (ST-044; FR-101;
ADR 0005, metric-dictionary rule 0.3).

sprint-03 §5 TDD order. ``wilson``: 1. k > n or negative -> error; 2. n = 0 -> no interval;
3. k = 0 lower bound exactly 0, k = n upper bound exactly 1; 4. 22/40 -> 0.398-0.693.
``LowSamplePolicy``: 1. n < min -> flagged; 2. width > 0.30 at n >= 20 -> flagged (10/20);
3. 22/40 -> not flagged; 4. a count metric with 1 game -> flagged; thresholds from config.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.analytics.uncertainty import (
    ImpossibleCounts,
    InvalidPolicy,
    LowSamplePolicy,
    wilson,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------- wilson, negative cases first
@pytest.mark.parametrize(("k", "n"), [(5, 4), (-1, 4), (0, -1), (1, 0)])
def test_impossible_counts_are_refused(k: int, n: int) -> None:
    with pytest.raises(ImpossibleCounts):
        wilson(k, n)


@pytest.mark.parametrize(("k", "n"), [(True, 4), (1.0, 4), (1, 4.0)])
def test_counts_must_be_integers(k: object, n: object) -> None:
    with pytest.raises(ImpossibleCounts):
        wilson(k, n)  # type: ignore[arg-type]


def test_no_trials_gives_no_interval() -> None:
    assert wilson(0, 0) is None


def test_the_edges_are_exact() -> None:
    zero, full = wilson(0, 7), wilson(7, 7)
    assert zero is not None
    assert full is not None
    assert zero.low == 0.0
    assert full.high == 1.0


def test_22_of_40_is_0398_to_0693() -> None:
    ci = wilson(22, 40)
    assert ci is not None
    assert (round(ci.low, 3), round(ci.high, 3)) == (0.398, 0.693)
    assert ci.width == pytest.approx(ci.high - ci.low)


@given(
    st.integers(min_value=1, max_value=500).flatmap(
        lambda n: st.tuples(st.integers(min_value=0, max_value=n), st.just(n))
    )
)
def test_the_interval_holds_the_proportion_and_stays_in_0_1(kn: tuple[int, int]) -> None:
    k, n = kn
    ci = wilson(k, n)
    assert ci is not None
    assert 0.0 <= ci.low <= k / n <= ci.high <= 1.0


# ---------------------------------------------------------------- LowSamplePolicy
def test_a_proportion_below_the_minimum_n_is_flagged() -> None:
    assert LowSamplePolicy().proportion_flagged(19, 19) is True
    assert LowSamplePolicy().proportion_flagged(0, 0) is True


def test_a_wide_interval_at_n_20_is_flagged() -> None:
    assert LowSamplePolicy().proportion_flagged(10, 20) is True


def test_22_of_40_is_not_flagged() -> None:
    assert LowSamplePolicy().proportion_flagged(22, 40) is False


def test_a_count_metric_over_one_game_is_flagged() -> None:
    policy = LowSamplePolicy()
    assert policy.count_flagged(games=1) is True
    assert policy.count_flagged(games=2) is False


def test_fewer_than_10_service_turns_is_flagged() -> None:
    policy = LowSamplePolicy()
    assert policy.turns_flagged(9) is True
    assert policy.turns_flagged(10) is False


def test_thresholds_come_from_config() -> None:
    policy = LowSamplePolicy(
        min_proportion_n=10, max_interval_width=0.5, min_games=1, min_service_turns=2
    )
    assert policy.proportion_flagged(10, 20) is False
    assert policy.count_flagged(games=1) is False
    assert policy.turns_flagged(2) is False


def test_a_metric_with_its_own_threshold_is_flagged_by_it() -> None:
    # ADR 0041 (S6): per-metric minimum n; a metric without one uses min_proportion_n.
    policy = LowSamplePolicy(proportion_n={"AN-05": 30})
    assert policy.proportion_flagged(0, 25, "AN-05") is True
    assert policy.proportion_flagged(25, 25, "AN-01") is False
    assert policy.proportion_flagged(25, 25) is False
    assert (policy.proportion_threshold("AN-05"), policy.proportion_threshold("AN-01")) == (30, 20)


def test_the_defaults_are_adr_0005() -> None:
    p = LowSamplePolicy()
    assert (p.min_proportion_n, p.max_interval_width, p.min_games, p.min_service_turns) == (
        20,
        0.30,
        2,
        10,
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min_proportion_n": 0},
        {"min_games": 0},
        {"min_service_turns": -1},
        {"max_interval_width": 0.0},
        {"max_interval_width": 1.5},
        {"min_proportion_n": True},
        {"proportion_n": {"AN-05": 0}},
        {"proportion_n": {"AN-05": "30"}},
    ],
)
def test_a_nonsense_threshold_is_refused(kwargs: dict[str, object]) -> None:
    with pytest.raises(InvalidPolicy):
        LowSamplePolicy(**kwargs)  # type: ignore[arg-type]
