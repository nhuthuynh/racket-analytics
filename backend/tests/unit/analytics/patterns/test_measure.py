"""``PatternMeasure`` value object (ST-171a; FR-171.R1, R5, R6; ADR 0061 Rule 1, Rule 3.1).

Negative cases first: an unavailable pattern never carries a value (never 0, FR-171.R5), an
unknown reason or interval method is refused, a measure below its min_n is never rankable
(FR-171.R6), and a measure with no interval is never rankable (ADR 0061 Rule 3.1).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from racket.analytics.patterns.measure import (
    INTERVAL_METHODS,
    UNAVAILABLE_REASONS,
    InvalidMeasure,
    PatternMeasure,
)
from racket.analytics.uncertainty import Interval

pytestmark = [pytest.mark.unit]


def _measure(**changes: Any) -> PatternMeasure:
    fields: dict[str, Any] = {
        "pattern_id": "AN-01",
        "value": 0.6,
        "n": 25,
        "interval": Interval(0.4, 0.78),
        "interval_method": "wilson",
        "low_sample": False,
        "definition_version": "0.1",
    }
    fields.update(changes)
    return PatternMeasure(**fields)


# ---------------------------------------------------------------- negative first: FR-171.R5
def test_an_unavailable_pattern_is_never_reported_as_zero() -> None:
    with pytest.raises(InvalidMeasure, match="unavailable"):
        _measure(value=0.0, interval=None, interval_method=None, n=0,
                 unavailable_reason="no_shot_facets")  # fmt: skip


@pytest.mark.parametrize(
    "changes",
    [
        {"n": 3},
        {"interval": Interval(0.0, 1.0)},
        {"low_sample": True},
        {"n_excluded": 1},
        {"interval_method": "wilson"},
    ],
    ids=["n", "interval", "low_sample", "n_excluded", "interval_method"],
)
def test_an_unavailable_pattern_carries_no_sample(changes: dict[str, Any]) -> None:
    base: dict[str, Any] = {
        "value": None, "n": 0, "interval": None, "interval_method": None,
        "unavailable_reason": "no_shot_facets",
    }  # fmt: skip
    with pytest.raises(InvalidMeasure, match="unavailable"):
        _measure(**{**base, **changes})


def test_the_unavailable_factory_has_no_value_no_n_and_is_not_rankable() -> None:
    m = PatternMeasure.unavailable("AN-09", "no_shot_facets", "0.1")
    assert (m.pattern_id, m.value, m.n, m.interval, m.interval_method) == (
        "AN-09", None, 0, None, None,
    )  # fmt: skip
    assert (m.unavailable_reason, m.available, m.rankable, m.low_sample) == (
        "no_shot_facets", False, False, False,
    )  # fmt: skip
    assert (m.n_excluded, m.definition_version) == (0, "0.1")


def test_an_unknown_unavailable_reason_is_refused() -> None:
    with pytest.raises(InvalidMeasure, match="reason"):
        PatternMeasure.unavailable("AN-09", "no_data", "0.1")


def test_the_unavailable_reasons_are_the_catalogue_s() -> None:
    # docs/domain/pattern-catalogue.md §0.2
    assert set(UNAVAILABLE_REASONS) == {"no_shot_facets", "no_bounce_positions", "needs_cv"}


# ---------------------------------------------------------------- negative first: FR-171.R6
def test_a_low_sample_measure_is_not_rankable() -> None:
    m = _measure(n=7, low_sample=True)
    assert m.available
    assert not m.rankable


def test_a_measure_without_an_interval_is_not_rankable() -> None:
    # ADR 0061 Rule 3.1: AN-04 (a count per game) has no interval method, so no honest gap
    m = _measure(pattern_id="AN-04", value=1.5, n=2, interval=None, interval_method=None)
    assert m.available
    assert not m.rankable


def test_a_measure_with_no_value_is_not_rankable() -> None:
    # n = 0: the source exists but nothing was counted (not unavailable, FR-171.R5)
    m = _measure(value=None, n=0, interval=None, low_sample=True)
    assert (m.available, m.rankable, m.unavailable_reason) == (True, False, None)


def test_a_measure_at_or_above_min_n_with_an_interval_is_rankable() -> None:
    m = _measure()
    assert m.available
    assert m.rankable


# ---------------------------------------------------------------- shape and invariants
def test_an_interval_needs_its_method() -> None:
    with pytest.raises(InvalidMeasure, match="interval_method"):
        _measure(interval_method=None)


def test_a_method_without_an_interval_is_allowed_when_n_is_too_small() -> None:
    # AN-13 below n = 6: the order-statistic interval does not exist (FR-171.R4)
    m = _measure(pattern_id="AN-13", value=5.0, n=3, interval=None,
                 interval_method="order_statistic_median", low_sample=True)  # fmt: skip
    assert (m.interval, m.interval_method, m.rankable) == (None, "order_statistic_median", False)


def test_an_unknown_interval_method_is_refused() -> None:
    with pytest.raises(InvalidMeasure, match="interval_method"):
        _measure(interval_method="normal")


def test_the_interval_methods_are_wilson_and_the_order_statistic_median() -> None:
    assert set(INTERVAL_METHODS) == {"wilson", "order_statistic_median"}


@pytest.mark.parametrize("n", [-1, 1.5, True, "3"])
def test_n_is_a_count(n: Any) -> None:
    with pytest.raises(InvalidMeasure, match="n must"):
        _measure(n=n)


@pytest.mark.parametrize("n_excluded", [-1, 0.5, False])
def test_n_excluded_is_a_count(n_excluded: Any) -> None:
    with pytest.raises(InvalidMeasure, match="n_excluded"):
        _measure(n_excluded=n_excluded)


@pytest.mark.parametrize("version", ["", "1", "v0.1", "0.1.2", None])
def test_the_definition_version_is_major_dot_minor(version: Any) -> None:
    with pytest.raises(InvalidMeasure, match="definition_version"):
        _measure(definition_version=version)


@pytest.mark.parametrize("pattern_id", ["", "AN-1", "an-01", None])
def test_the_pattern_id_is_an_id(pattern_id: Any) -> None:
    with pytest.raises(InvalidMeasure, match="pattern_id"):
        _measure(pattern_id=pattern_id)


@pytest.mark.parametrize("pattern_id", ["AN-07:forced-error", "AN-09", "STACK", "SPACING"])
def test_pattern_ids_follow_the_catalogue_and_plan_target_forms(pattern_id: str) -> None:
    assert _measure(pattern_id=pattern_id).pattern_id == pattern_id


@pytest.mark.parametrize("value", [True, "0.5", float("nan")])
def test_the_value_is_a_number(value: Any) -> None:
    with pytest.raises(InvalidMeasure, match="value"):
        _measure(value=value)


def test_a_measure_is_immutable() -> None:
    m = _measure()
    with pytest.raises(FrozenInstanceError):
        m.value = 0.0  # type: ignore[misc]


def test_n_excluded_defaults_to_zero_and_is_kept() -> None:
    assert _measure().n_excluded == 0
    assert _measure(n_excluded=2).n_excluded == 2
