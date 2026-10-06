"""C-26 (PE-R1-07): ``apply`` refuses a state whose score already meets the game-over condition
but has no winner (an inconsistent input), instead of scoring past the end of the game.
Mechanics only (ADR 0009 (a)): the configuration is a test input, not a rule claim."""

from __future__ import annotations

import pytest

from racket.sports.pickleball.rules import (
    GameState,
    IllegalState,
    RallyOutcome,
    RulesConfig,
    Side,
    apply,
    fold,
)

pytestmark = [pytest.mark.unit, pytest.mark.scoring]

CONFIG = RulesConfig(rules_version="TEST-C26", scoring_system="side_out",  # type: ignore[arg-type]
                     format="doubles", points_to_win=11, win_by=2,  # type: ignore[arg-type]
                     first_service_single_server=True)  # fmt: skip


def state(score_a: int, score_b: int, winner: Side | None) -> GameState:
    return GameState(score_a=score_a, score_b=score_b, serving_side=Side.A, server_number=1,
                     winner=winner, server_player="A1", right_court_a="A1",
                     right_court_b="B1")  # fmt: skip


def test_a_game_over_score_without_a_winner_is_an_illegal_state() -> None:
    result = apply(state(11, 3, None), RallyOutcome.won_by(Side.A), CONFIG)
    assert isinstance(result, IllegalState)


def test_fold_refuses_the_same_start() -> None:
    assert isinstance(fold([RallyOutcome.replay()], CONFIG, state(12, 10, None)), IllegalState)


def test_a_score_short_of_the_end_still_plays() -> None:
    result = apply(state(10, 3, None), RallyOutcome.won_by(Side.A), CONFIG)
    assert isinstance(result, GameState)
    assert result.winner is Side.A
