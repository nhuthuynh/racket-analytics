"""Binds tests/features/pattern_measures_quick_tag.feature (ST-171a; FR-171.R1, R5, R6).

Pure domain: the sheet is built by the real projection (``tests.unit.analytics.sheets``), the
measures by ``racket.analytics.patterns``; no API and no database.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from racket.analytics.patterns.quick_tag import quick_tag_measures
from racket.analytics.snapshot import policy_from_dictionary
from racket.analytics.starter_stats import starter_stats
from racket.analytics.uncertainty import Interval
from racket.sports.pickleball.metrics import load_dictionary
from tests.unit.analytics.sheets import WORKED_EXAMPLE, a_serves_and_wins_25, one_game

scenarios("pattern_measures_quick_tag.feature")

_SHARES = {
    "AN-07:winner": "winner",
    "AN-07:unforced-error": "unforced_error",
    "AN-07:forced-error": "forced_error",
    "AN-07:fault": "fault",
}
_COUNTS = {"AN-03": ("value", "turns"), "AN-04": ("value", "games"), "AN-06": ("longest", "n")}


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {"dictionary": load_dictionary()}


@given("the worked-example game of the metric dictionary is projected")
def worked_example(ctx: dict[str, Any]) -> None:
    ctx["sheet"] = one_game(WORKED_EXAMPLE)


@given("side A serves and wins 25 rallies")
def wins_25(ctx: dict[str, Any]) -> None:
    ctx["sheet"] = a_serves_and_wins_25()


@when("the pattern measures of the match are taken from Quick Tag")
def measured(ctx: dict[str, Any]) -> None:
    ctx["measures"] = quick_tag_measures(ctx["sheet"], ctx["dictionary"])


@when(
    parsers.parse(
        'the pattern measures of the match are taken from Quick Tag with "{pattern}" from '
        '"{source}"'
    )
)
def measured_with(ctx: dict[str, Any], pattern: str, source: str) -> None:
    other = {pattern: (source, "0.1")}
    ctx["measures"] = quick_tag_measures(ctx["sheet"], ctx["dictionary"], other_patterns=other)


@then(
    parsers.parse(
        '"{pattern}" for side {side} is {value:f} with n {n:d} and the Wilson interval '
        "{low:f} to {high:f}"
    )
)
def proportion(
    ctx: dict[str, Any], pattern: str, side: str, value: float, n: int, low: float, high: float
) -> None:
    m = ctx["measures"][pattern][side]
    assert (m.value, m.n, m.interval, m.interval_method) == (
        value, n, Interval(low, high), "wilson",
    )  # fmt: skip


@then("every Quick Tag measure equals its starter stat")
def equals_starter_stats(ctx: dict[str, Any]) -> None:
    stats = starter_stats(ctx["sheet"], policy_from_dictionary(ctx["dictionary"]))
    for pattern, by_side in ctx["measures"].items():
        for side, m in by_side.items():
            if pattern in _COUNTS:
                value_key, n_key = _COUNTS[pattern]
                want = stats[pattern][side]
                assert (m.value, m.n) == (want[value_key], want[n_key]), (pattern, side)
                continue
            metric, share = (("AN-07", _SHARES[pattern]) if pattern in _SHARES
                             else (pattern, None))  # fmt: skip
            row = stats[metric][side]
            got = row["shares"][share] if share else row
            assert (m.value, m.n, m.low_sample) == (got["value"], row["n"], row["low_sample"])
            assert m.interval == Interval(got["ci_low"], got["ci_high"]), (pattern, side)


@then(
    parsers.parse(
        '"{pattern}" for side {side} is unavailable with the reason "{reason}" and no value'
    )
)
def unavailable(ctx: dict[str, Any], pattern: str, side: str, reason: str) -> None:
    m = ctx["measures"][pattern][side]
    assert (m.unavailable_reason, m.value, m.n, m.rankable) == (reason, None, 0, False)


@then(parsers.parse('"{pattern}" for side {side} is flagged as a low sample and is not rankable'))
def low_sample(ctx: dict[str, Any], pattern: str, side: str) -> None:
    m = ctx["measures"][pattern][side]
    assert (m.low_sample, m.rankable) == (True, False)


@then(parsers.parse('"{pattern}" for side {side} is rankable'))
def rankable(ctx: dict[str, Any], pattern: str, side: str) -> None:
    m = ctx["measures"][pattern][side]
    assert (m.low_sample, m.rankable) == (False, True)
