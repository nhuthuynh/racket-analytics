"""Binds tests/features/attribution_conservation_domain.feature (ST-045; FR-109; ADR 0003).

Pure domain: the sheet is built by the real projection (``tests.unit.analytics.sheets``), the
attribution and stats by ``racket.analytics``; no API and no database. A broken attribution is
injected by wrapping the product's ``attribute_lost_rallies`` as ``starter_stats`` sees it.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

import racket.analytics.starter_stats as stats_module
from racket.analytics.attribution import (
    PHASES,
    UNATTRIBUTED,
    AttributionBroken,
    attribute_lost_rallies,
    lost_rallies,
)
from racket.analytics.sheet import SIDES, counted_rallies
from racket.analytics.starter_stats import starter_stats
from tests.unit.analytics.sheets import WORKED_EXAMPLE, one_game, sheet, side_a_wins_game, tag

scenarios("attribution_conservation_domain.feature")


def _numbers(text: str) -> list[int]:
    return [int(n) for n in text.split(",") if n.strip()]


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given("the worked-example game of the metric dictionary is projected")
def worked_example(ctx: dict[str, Any]) -> None:
    ctx["sheet"] = one_game(WORKED_EXAMPLE)


@given("a match of two games where side A wins game 1 and game 2 starts with side B serving")
def two_games(ctx: dict[str, Any]) -> None:
    ctx["sheet"] = sheet(
        [
            {"first_serving_side": "A", "tags": side_a_wins_game()},
            {"first_serving_side": "B", "tags": [tag("A", "winner"), tag("B", "fault", "foot")]},
        ]
    )


def _break_attribution(monkeypatch: pytest.MonkeyPatch, breaker: Any) -> None:
    def broken(counted: Any) -> Any:
        attributed = attribute_lost_rallies(counted)
        breaker(attributed)
        return attributed

    monkeypatch.setattr(stats_module, "attribute_lost_rallies", broken)


@given(parsers.parse("the attribution counts rally {number:d} twice"))
def counted_twice(monkeypatch: pytest.MonkeyPatch, number: int) -> None:
    def twice(attributed: Any) -> None:
        for side in SIDES:
            for phases in attributed[side].values():
                for groups in phases.values():
                    for numbers in groups.values():
                        if number in numbers:
                            numbers.append(number)
                            return

    _break_attribution(monkeypatch, twice)


@given(parsers.parse("the attribution leaves out what side {side} lost on {phase}"))
def left_out(monkeypatch: pytest.MonkeyPatch, side: str, phase: str) -> None:
    def drop(attributed: Any) -> None:
        for phases in attributed[side].values():
            phases[phase] = {}

    _break_attribution(monkeypatch, drop)


@given(
    parsers.parse(
        "the attribution puts rally {other:d} in place of rally {number:d} "
        "that side {side} lost on {phase}"
    )
)
def swapped(
    monkeypatch: pytest.MonkeyPatch, other: int, number: int, side: str, phase: str
) -> None:
    """Keeps the count, changes the identity (QA-ST045-R1-01)."""

    def swap(attributed: Any) -> None:
        for phases in attributed[side].values():
            for numbers in phases[phase].values():
                if number in numbers:
                    numbers[numbers.index(number)] = other
                    return
        raise AssertionError(f"rally {number} is not attributed to side {side} on {phase}")

    _break_attribution(monkeypatch, swap)


@when("the starter stats are computed")
def computed(ctx: dict[str, Any]) -> None:
    try:
        ctx["stats"] = starter_stats(ctx["sheet"])
    except AttributionBroken as refused:
        ctx["refused"] = refused
    ctx["counted"] = counted_rallies(ctx["sheet"])


@when("the lost rallies are attributed")
def attributed(ctx: dict[str, Any]) -> None:
    ctx["counted"] = counted_rallies(ctx["sheet"])
    ctx["attributed"] = attribute_lost_rallies(ctx["counted"])


@then(parsers.parse('the computation is refused with "{where}"'))
def refused(ctx: dict[str, Any], where: str) -> None:
    assert "stats" not in ctx, "numbers were published despite a broken attribution"
    assert where in str(ctx["refused"])


@then(
    parsers.re(
        r'side (?P<side>[AB]) lost rallies "(?P<serve>[0-9,]*)" on serve and '
        r'"(?P<receive>[0-9,]*)" on receive in game (?P<game>\d+)'
    )
)
def lost(ctx: dict[str, Any], side: str, serve: str, receive: str, game: str) -> None:
    assert "refused" not in ctx
    got = lost_rallies(ctx["counted"])[side][int(game)]
    assert got == {"serve": _numbers(serve), "receive": _numbers(receive)}


@then("for each side, game and phase the attributed and unattributed rallies equal the lost ones")
def conserved(ctx: dict[str, Any]) -> None:
    lost_by = lost_rallies(ctx["counted"])
    given_by = attribute_lost_rallies(ctx["counted"])
    for side in SIDES:
        assert set(given_by[side]) == set(lost_by[side])
        for game, phases in lost_by[side].items():
            for phase in PHASES:
                got = sorted(n for v in given_by[side][game][phase].values() for n in v)
                assert got == phases[phase], (side, game, phase)


@then(
    parsers.parse('side {side}\'s unattributed rallies on {phase} in game {game:d} are "{numbers}"')
)
def unattributed(ctx: dict[str, Any], side: str, phase: str, game: int, numbers: str) -> None:
    assert ctx["attributed"][side][game][phase][UNATTRIBUTED] == _numbers(numbers)
