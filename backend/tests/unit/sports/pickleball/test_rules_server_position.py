"""Review round 1, PE-R1-03: who serves from where (ST-020; QD-RE-03; DOM R6, UNVERIFIED).

Every rule here waits for a rule number from the 2026 rulebook (OQ-01, DOM G1), so the whole
module is ``needs_verification``. The two invariants, stated for any side-out doubles config:

* each service turn starts from the right-hand court: at the game start (``0-0-2`` included)
  and after every side-out, the server is the serving side's right-court player;
* each side's slot-1 player (its starting player in a new game) stands in the right-hand court
  exactly when that side's score is even.

"The server stands in the right court iff the serving score is even" is NOT an invariant: the
second server of a turn serves from wherever they stand (see the last test).
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.sports.pickleball.rules import (
    GameState,
    RallyOutcome,
    apply,
    new_game,
)
from tests.unit.sports.pickleball.rules_helpers import A, B, config

pytestmark = [pytest.mark.unit, pytest.mark.scoring, pytest.mark.needs_verification]


@pytest.mark.parametrize("first", [A, B])
def test_at_0_0_2_the_first_server_is_the_right_court_player(first: object) -> None:
    state = new_game(config(first_service=True), first)  # type: ignore[arg-type]
    assert state.server_number == 2
    assert state.server_player == state.right_court_player[state.serving_side]
    assert state.server_player == f"{state.serving_side.value}1"


def test_at_0_0_2_the_first_server_keeps_serving_after_scoring_from_the_left_court() -> None:
    state = apply(
        new_game(config(first_service=True), A), RallyOutcome.won_by(A), config(first_service=True)
    )
    assert isinstance(state, GameState)
    assert (state.server_player, state.right_court_player[A]) == ("A1", "A2")


_rally = st.sampled_from(["A", "B", "replay"])


@given(first=st.sampled_from([A, B]), first_service=st.booleans(),
       rallies=st.lists(_rally, max_size=120))  # fmt: skip
def test_every_service_turn_starts_from_the_right_court_and_slot_one_follows_parity(
    first: object, first_service: bool, rallies: list[str]
) -> None:
    cfg = config(first_service=first_service)
    state: GameState = new_game(cfg, first)  # type: ignore[arg-type]
    assert state.server_player == state.right_court_player[state.serving_side]
    for rally in rallies:
        if state.is_over:
            break
        outcome = (
            RallyOutcome.replay()
            if rally == "replay"
            else RallyOutcome.won_by(A if rally == "A" else B)
        )
        after = apply(state, outcome, cfg)
        assert isinstance(after, GameState)
        if after.serving_side is not state.serving_side:  # side-out: a new service turn
            assert after.server_player == after.right_court_player[after.serving_side]
        for side in (A, B):
            slot_one_right = after.right_court_player[side] == f"{side.value}1"
            assert slot_one_right == (after.score_of(side) % 2 == 0)
        state = after


def test_the_second_server_serves_from_where_they_stand_even_at_an_odd_score() -> None:
    cfg = config(first_service=True)
    state = new_game(cfg, A)  # 0-0-2, A1 serves from the right
    # A scores (1-0-2, A1 to the left); B wins the rally: side-out, B1 serves 0-1-1 from the
    # right; B scores (1-1-1, B1 to the left, B2 to the right); A wins: B2 serves at server 2.
    for winner in (A, B, B, A):
        result = apply(state, RallyOutcome.won_by(winner), cfg)
        assert isinstance(result, GameState)
        state = result
    assert (state.serving_side, state.score_b, state.server_number) == (B, 1, 2)
    assert state.server_player == "B2"
    assert state.right_court_player[B] == "B2"  # right court at an odd score: legal
