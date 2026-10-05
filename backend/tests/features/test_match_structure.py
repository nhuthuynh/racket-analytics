"""Binds tests/features/match_structure.feature, sprint-01 §7.10 (ST-021; M rows of ST-023).

Written before the code (tests first). RED until ST-021 provides MatchState and MatchOver
(seams in tests/support/contract.py, ADR 0012).
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.features.scoring_steps import *  # noqa: F403  (shared step fixtures)
from tests.features.scoring_steps import match_config, play_match
from tests.support import contract
from tests.support import scoring as sc

pytestmark = [pytest.mark.red_until(story="ST-021"), pytest.mark.scoring]

scenarios("match_structure.feature")


def _winners(games: str) -> list[str]:
    return [g.strip() for g in games.split(",") if g.strip()]


@given(parsers.parse("a best-of-{n:d} match in which the games were won by {games}"))
def match_with_games(ctx: dict[str, Any], n: int, games: str) -> None:
    ctx["config"] = match_config()
    ctx["match"] = play_match(n, _winners(games), ctx["config"])


@then(parsers.parse("the match is {result}"))
def match_is(ctx: dict[str, Any], result: str) -> None:
    ms = ctx["match"]
    if result.startswith("not over"):
        assert not ms.is_over
        assert ms.winner is None
        opened = ms.start_game(first_server=sc.side("A"), ends_switched=False)
        assert not sc.is_domain_error(opened), f"next game is not open: {opened!r}"
        assert [g.number for g in opened.games][-1] == len(ms.games) + 1 == 3
        return
    letter, a, b = parse_match_result(result)
    winner = sc.side(letter)
    assert ms.is_over
    assert ms.winner == winner
    assert (ms.games_won(winner), ms.games_won(winner.other)) == (a, b)
    assert isinstance(
        ms.start_game(first_server=winner, ends_switched=False), contract.MATCH_OVER.load()
    ), "a decided match opened another game"


def parse_match_result(result: str) -> tuple[str, int, int]:
    parsed = re.fullmatch(r"won by side ([AB]), (\d+)-(\d+)", result)
    assert parsed, f"unknown match result wording {result!r}"
    return parsed[1], int(parsed[2]), int(parsed[3])


@when(parsers.parse("a rally is recorded for game {game:d}"))
def rally_for_game(ctx: dict[str, Any], game: int) -> None:
    ms = ctx["match"]
    ctx["results"] = [ms.record_rally(game, outcome) for outcome in sc.all_outcomes()]


@given("game 1 of Ivy's match has ended")
def game_one_ended(ctx: dict[str, Any]) -> None:
    ctx["match"] = play_match(3, ["A"])


@when(
    parsers.parse(
        "she starts game 2 and states that side {letter} serves first and ends were switched"
    )
)
def start_game_two(ctx: dict[str, Any], letter: str) -> None:
    result = ctx["match"].start_game(first_server=sc.side(letter), ends_switched=True)
    assert not sc.is_domain_error(result), result
    ctx["match"] = result


@then(parsers.parse("game 2 starts with side {letter} serving"))
def game_two_serving(ctx: dict[str, Any], letter: str) -> None:
    game = ctx["match"].games[1]
    assert game.number == 2
    assert game.first_server == sc.side(letter)
    assert game.state.serving_side == sc.side(letter)
    assert (game.state.score_a, game.state.score_b) == (0, 0)


@then("game 2 is recorded as played from switched ends")
def game_two_switched(ctx: dict[str, Any]) -> None:
    assert ctx["match"].games[1].ends_switched is True
    assert ctx["match"].games[0].ends_switched is False
