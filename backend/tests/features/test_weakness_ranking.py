"""Binds tests/features/weakness_ranking.feature (ST-055; FR-120; ADR 0003; OQ-08).

Pure domain: no API and no database. The FR-120 rallies are built as Coaching's own
``RallyFact`` values; the metric dictionary's worked example is projected by the real score
sheet projection (``tests.unit.analytics.sheets``), read through Analytics' published read
model (``facts_of_sheet``) and translated by Coaching's ACL, as IT-04-01 does over Postgres.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from racket.analytics.public import facts_of_sheet
from racket.coaching.weakness import acl
from racket.coaching.weakness.domain import RallyFact, Weakness, attribute, rank
from tests.unit.analytics.sheets import WORKED_EXAMPLE, one_game

scenarios("weakness_ranking.feature")

MATCH = uuid.UUID(int=55)
IVY = "A"  # Ivy's side in every scenario


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {"facts": [], "games": 0}


def _fact(number: int, serving: str, winning: str, ending: str, kind: str | None) -> RallyFact:
    scored = winning == serving  # side-out: only the serving side scores (UNVERIFIED, P7)
    return RallyFact(
        rally_id=f"r{number}",
        game=1,
        serving_side=serving,
        winning_side=winning,
        ending=ending,
        fault_kind=kind,
        responsible_player=None,
        point_to=winning if scored else None,
    )


@given(parsers.parse('player "{name}" has no tagged match'))
def no_match(ctx: dict[str, Any], name: str) -> None:
    ctx["facts"], ctx["games"] = [], 0


@given(parsers.parse('over 1 game Ivy lost {count:d} rallies on serve to "{ending}"'))
def lost_on_serve(ctx: dict[str, Any], count: int, ending: str) -> None:
    start = len(ctx["facts"])
    ctx["facts"] += [_fact(start + i + 1, IVY, "B", ending, None) for i in range(count)]
    ctx["games"] = 1


@given(parsers.parse('over the same game Ivy lost {count:d} rallies on receive to a "{kind}" fault'))
def lost_on_receive(ctx: dict[str, Any], count: int, kind: str) -> None:
    start = len(ctx["facts"])
    ctx["facts"] += [_fact(start + i + 1, "B", "B", "fault", kind) for i in range(count)]


@given("side A of the metric dictionary's worked example is Ivy's side")
def worked_example(ctx: dict[str, Any]) -> None:
    facts = facts_of_sheet(one_game(WORKED_EXAMPLE))
    ctx["facts"] = list(acl.translate(facts))
    ctx["games"] = len(facts.games)


@when("Ivy's weaknesses are ranked")
def ranked(ctx: dict[str, Any]) -> None:
    ctx["losses"] = attribute(MATCH, IVY, ctx["facts"])
    ctx["ranking"] = rank(ctx["losses"], ctx["games"], rallies=len(ctx["facts"]))


def _weakness(ctx: dict[str, Any], name: str) -> Weakness:
    found = [w for w in ctx["ranking"].weaknesses if w.name == name]
    assert found, f"{name} is not ranked: {[w.name for w in ctx['ranking'].weaknesses]}"
    return found[0]


@then(parsers.parse('the ranking is empty with the reason "{reason}"'))
def empty(ctx: dict[str, Any], reason: str) -> None:
    assert ctx["ranking"].weaknesses == ()
    assert ctx["ranking"].reason == reason


@then(parsers.parse("the ranking covers {games:d} games"))
def covers(ctx: dict[str, Any], games: int) -> None:
    assert ctx["ranking"].games == games


@then(parsers.parse('the weaknesses in order are "{names}"'))
def in_order(ctx: dict[str, Any], names: str) -> None:
    assert [w.name for w in ctx["ranking"].weaknesses] == names.split(", ")
    assert [w.rank for w in ctx["ranking"].weaknesses] == list(
        range(1, len(ctx["ranking"].weaknesses) + 1)
    )


@then(
    parsers.parse(
        '"{name}" shows {per_game:f} rallies lost per game, {serve:d} on serve and '
        "{receive:d} on receive"
    )
)
def shows(ctx: dict[str, Any], name: str, per_game: float, serve: int, receive: int) -> None:
    w = _weakness(ctx, name)
    assert (w.lost_on_serve, w.lost_on_receive) == (serve, receive)
    assert round(float(w.per_game), 1) == per_game
    assert w.on_serve_per_game + w.on_receive_per_game == w.per_game


@then(parsers.re(r'"(?P<name>[^"]+)" shows (?P<points>\d+) points? conceded'))
def conceded(ctx: dict[str, Any], name: str, points: str) -> None:
    assert _weakness(ctx, name).conceded == int(points)


@then("every rally Ivy lost is counted once, on serve or on receive")
def counted_once(ctx: dict[str, Any]) -> None:
    lost = [f for f in ctx["facts"] if f.winning_side != IVY]
    ranking = ctx["ranking"]
    assert ranking.lost_on_serve + ranking.lost_on_receive == len(lost)
    attributed = sum(w.lost for w in ranking.weaknesses) + ranking.unattributed
    assert attributed == len(lost)
    assert sorted(loss.rally_id for loss in ctx["losses"]) == sorted(f.rally_id for f in lost)


@then(parsers.parse('the ranking\'s unit is "{unit}"'))
def unit(ctx: dict[str, Any], unit: str) -> None:
    assert ctx["ranking"].unit == unit


@then("the ranking is marked provisional, side-out rule not verified")
def provisional(ctx: dict[str, Any]) -> None:
    assert ctx["ranking"].provisional is True
    assert ctx["ranking"].side_out_verified is False
