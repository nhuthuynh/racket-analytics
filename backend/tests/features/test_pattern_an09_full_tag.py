"""Binds tests/features/pattern_an09_full_tag.feature (ST-171b; FR-171.R2, R3, R6).

Pure domain: team-made label documents (``tests.unit.analytics.full_tag_docs``) are read through
the Analytics ACL by ``racket.analytics.patterns.full_tag``; no API and no database.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from racket.analytics.patterns.full_tag import AGREEMENT_LABELS, full_tag_measures

from tests.unit.analytics.full_tag_docs import doc, rally, third_shots

scenarios("pattern_an09_full_tag.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {"rallies": []}


def _serve(ctx: dict[str, Any], trajectories: list[str | None]) -> None:
    ctx["rallies"] += third_shots("A", trajectories, start=len(ctx["rallies"]) + 1)


@given(parsers.parse("side A serves {n:d} rallies whose third shots are {d:d} drops and "
                     "{v:d} drives"))  # fmt: skip
def drops_and_drives(ctx: dict[str, Any], n: int, d: int, v: int) -> None:
    assert d + v == n
    _serve(ctx, ["drop"] * d + ["drive"] * v)


@given(parsers.parse("side A serves {n:d} rallies whose third shots are {d:d} drops, {v:d} "
                     "drives and {m:d} without a facet"))  # fmt: skip
def with_missing(ctx: dict[str, Any], n: int, d: int, v: int, m: int) -> None:
    assert d + v + m == n
    _serve(ctx, ["drop"] * d + ["drive"] * v + [None] * m)


@given("side A serves a rally that ends after the return")
def two_hits(ctx: dict[str, Any]) -> None:
    ctx["rallies"].append(rally(f"r{len(ctx['rallies']) + 1}", "A1", "B1", winner="B"))


@when("the pattern measures of the labels are taken from Full Tag")
def measured(ctx: dict[str, Any]) -> None:
    ctx["measures"] = full_tag_measures(doc(*ctx["rallies"]))


def _m(ctx: dict[str, Any], pattern: str, side: str) -> Any:
    return ctx["measures"][pattern][side]


@then(parsers.parse('"{pattern}" for side {side:w} is {value:g} with n {n:d} and n_excluded {x:d}'))
def value_n(ctx: dict[str, Any], pattern: str, side: str, value: float, n: int, x: int) -> None:
    m = _m(ctx, pattern, side)
    assert (m.value, m.n, m.n_excluded) == (pytest.approx(value), n, x)


@then(parsers.parse('side {side:w}\'s exclusions are "{reason}" {count:d}'))
def exclusions(ctx: dict[str, Any], side: str, reason: str, count: int) -> None:
    assert _m(ctx, "AN-09", side).exclusions == ((reason, count),)


@then(parsers.parse('"{pattern}" for side {side:w} is rankable'))
def rankable(ctx: dict[str, Any], pattern: str, side: str) -> None:
    m = _m(ctx, pattern, side)
    assert (m.low_sample, m.rankable) == (False, True)


@then(parsers.parse('"{pattern}" for side {side:w} is flagged as a low sample and is not rankable'))
def low_sample(ctx: dict[str, Any], pattern: str, side: str) -> None:
    m = _m(ctx, pattern, side)
    assert (m.low_sample, m.rankable) == (True, False)


@then(parsers.parse('"{pattern}" for side {side:w} is labelled "{label}"'))
def labelled(ctx: dict[str, Any], pattern: str, side: str, label: str) -> None:
    agreement = _m(ctx, pattern, side).agreement
    assert AGREEMENT_LABELS[agreement] == label
