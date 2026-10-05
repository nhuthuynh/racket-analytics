"""``score_call`` (FR-048, provisional call format; sprint-02 §5 ``ScoreCall`` formatter rows).

1. a doubles call has three numbers, serving side first; 2. a singles call has two numbers.
Both rest on DOM G1 R6, UNVERIFIED (ADR 0009): ``needs_verification``.
"""

from __future__ import annotations

import pytest

from racket.sports.pickleball.rules import GameState, Side, score_call

pytestmark = [pytest.mark.unit, pytest.mark.scoring, pytest.mark.needs_verification]


def state(score_a: int, score_b: int, serving: Side, number: int | None) -> GameState:
    server = "A1" if serving is Side.A else "B1"
    return GameState(score_a=score_a, score_b=score_b, serving_side=serving,
                     server_number=number, winner=None, server_player=server,
                     right_court_a="A1", right_court_b="B1")  # fmt: skip


def test_a_doubles_call_has_three_numbers_serving_side_first() -> None:
    assert score_call(state(4, 6, Side.B, 1)) == "6-4-1"
    assert score_call(state(0, 0, Side.A, 2)) == "0-0-2"


def test_a_singles_call_has_two_numbers_server_first() -> None:
    assert score_call(state(3, 7, Side.A, None)) == "3-7"
