"""Binds tests/features/starter_stats_domain.feature (ST-044; FR-100, FR-101, NFR-004).

Pure domain: the sheet is built by the real projection (``tests.unit.analytics.sheets``), the
stats by ``racket.analytics``; no API and no database. Numbers are the coach's hand count of
metric-dictionary §2 and the FR-101 examples.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from racket.analytics.starter_stats import starter_stats
from racket.analytics.uncertainty import LowSamplePolicy, wilson
from tests.unit.analytics.sheets import WORKED_EXAMPLE, one_game, sheet

scenarios("starter_stats_domain.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given("a projected sheet with no game")
def no_game(ctx: dict[str, Any]) -> None:
    ctx["sheet"] = sheet([])


@given("the worked-example game of the metric dictionary is projected")
def worked_example(ctx: dict[str, Any]) -> None:
    ctx["sheet"] = one_game(WORKED_EXAMPLE)


@when("the starter stats are computed")
def computed(ctx: dict[str, Any]) -> None:
    ctx["stats"] = starter_stats(ctx["sheet"])


@then(parsers.parse('"{metric}" for side {side} has no value with "n = {n:d}"'))
def no_value(ctx: dict[str, Any], metric: str, side: str, n: int) -> None:
    got = ctx["stats"][metric][side]
    assert (got["value"], got["ci_low"], got["ci_high"], got["n"]) == (None, None, None, n)


@then(parsers.parse('"{metric}" for side {side} is flagged as a low sample'))
def flagged(ctx: dict[str, Any], metric: str, side: str) -> None:
    assert ctx["stats"][metric][side]["low_sample"] is True


@then(
    parsers.parse(
        '"{metric}" for side {side} is {k:d} of {n:d} with the interval {low:f} to {high:f}'
    )
)
def proportion(
    ctx: dict[str, Any], metric: str, side: str, k: int, n: int, low: float, high: float
) -> None:
    got = ctx["stats"][metric][side]
    assert (got["k"], got["n"], got["ci_low"], got["ci_high"]) == (k, n, low, high)


@then(parsers.parse("no stat counts rally {number:d}, which was a replay"))
def replay_not_counted(ctx: dict[str, Any], number: int) -> None:
    for metric, sides in ctx["stats"].items():
        for side, fields in sides.items():
            assert number not in fields["rallies"], (metric, side)


@given(parsers.parse("a proportion of {k:d} out of {n:d}"))
def a_proportion(ctx: dict[str, Any], k: int, n: int) -> None:
    ctx["k"], ctx["n"] = k, n


@then(parsers.parse("its Wilson interval is {low:f} to {high:f}"))
def interval(ctx: dict[str, Any], low: float, high: float) -> None:
    ci = wilson(ctx["k"], ctx["n"])
    assert ci is not None
    assert (round(ci.low, 3), round(ci.high, 3)) == (low, high)


@then(parsers.parse("it is {flag}"))
def low_sample_flag(ctx: dict[str, Any], flag: str) -> None:
    expected = {"flagged": True, "not flagged": False}[flag]
    assert LowSamplePolicy().proportion_flagged(ctx["k"], ctx["n"]) is expected
