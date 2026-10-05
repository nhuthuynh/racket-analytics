"""GameState, declare_state, new_game, RallyOutcome and DomainError (ST-020; sprint-01 §5
GameState rows 1-3, in order; scoring-engine.md §2.4-§2.7). BE unit tests, negative first."""

from __future__ import annotations

from typing import Any

import pytest

from racket.sports.pickleball.rules import (
    GameState,
    IllegalState,
    declare_state,
    new_game,
)
from tests.unit.sports.pickleball.rules_helpers import A, B, call, config, declared

pytestmark = [pytest.mark.unit, pytest.mark.scoring]


# ------------------------------------------------------------------ GameState (§5 rows 1-3)


@pytest.mark.parametrize("number", [0, 3, -1, None, True])
def test_declared_server_number_outside_one_or_two_is_illegal_in_doubles(number: Any) -> None:
    result = declare_state(
        config(), serving_side=A, serving_score=0, receiving_score=0, server_number=number
    )
    assert isinstance(result, IllegalState)
    assert "server number" in result.message


@pytest.mark.parametrize(("s", "r"), [(11, 9), (9, 11), (12, 10), (15, 0)])
def test_a_state_meeting_the_game_over_condition_cannot_be_declared_in_play(s: int, r: int) -> None:
    result = declare_state(
        config(), serving_side=A, serving_score=s, receiving_score=r, server_number=1
    )
    assert isinstance(result, IllegalState)
    assert "game-over" in result.message


@pytest.mark.parametrize(("s", "r"), [(-1, 0), (0, -3), ("1", 0), (1.0, 0), (True, 0)])
def test_declared_scores_must_be_non_negative_ints(s: Any, r: Any) -> None:
    result = declare_state(
        config(), serving_side=A, serving_score=s, receiving_score=r, server_number=1
    )
    assert isinstance(result, IllegalState)


def test_declared_serving_side_must_be_a_side() -> None:
    result = declare_state(
        config(), serving_side="A", serving_score=0, receiving_score=0, server_number=1
    )
    assert isinstance(result, IllegalState)


def test_a_legal_declared_state_is_in_play_from_the_serving_side_view() -> None:
    state = declared(3, 5, 2, side=B)
    assert (state.score_a, state.score_b) == (5, 3)
    assert state.serving_side is B
    assert call(state) == (3, 5, 2)
    assert state.winner is None
    assert not state.is_over


def test_declared_zero_zero_one_is_legal() -> None:
    assert call(declared(0, 0, 1, first_service=True)) == (0, 0, 1)


def test_game_state_has_no_call_formatting() -> None:
    # Call formatting is a separate pure function (FR-048, Sprint 2).
    assert not hasattr(GameState, "call")
    assert not hasattr(GameState, "format_call")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"score_a": -1},
        {"server_number": 3},
        {"winner": "A"},
        {"winner": B},  # B has the lower score
        {"serving_side": "A"},
        {"server_player": "B1"},  # not on the serving side
    ],
)
def test_hand_built_inconsistent_state_is_a_programming_error(kwargs: dict[str, Any]) -> None:
    values: dict[str, Any] = {
        "score_a": 11,
        "score_b": 3,
        "serving_side": A,
        "server_number": 1,
        "winner": A,
        "server_player": "A1",
        "right_court_a": "A1",
        "right_court_b": "B1",
    }
    values.update(kwargs)
    with pytest.raises(ValueError, match="must"):
        GameState(**values)


@pytest.mark.parametrize(("flag", "number"), [(True, 2), (False, 1)])
def test_first_service_exception_comes_from_config(flag: bool, number: int) -> None:
    state = new_game(config(first_service=flag), B)
    assert call(state) == (0, 0, number)
    assert state.serving_side is B


# ------------------------------------------------------------------ positions (SOD-05/06)


def test_new_game_puts_slot_one_players_in_the_right_court() -> None:
    state = new_game(config(), A)
    assert state.right_court_player == {A: "A1", B: "B1"}
    assert state.server_player == "A1"


def test_new_game_needs_a_side_as_first_server() -> None:
    with pytest.raises(ValueError, match="first_server"):
        new_game(config(), "A")  # type: ignore[arg-type]


@pytest.mark.parametrize(("field", "value"), [("right_court_a", "B1"), ("right_court_b", "Z9")])
def test_right_court_players_belong_to_their_side(field: str, value: str) -> None:
    values: dict[str, Any] = {
        "score_a": 0,
        "score_b": 0,
        "serving_side": A,
        "server_number": 1,
        "winner": None,
        "server_player": "A1",
        "right_court_a": "A1",
        "right_court_b": "B1",
        field: value,
    }
    with pytest.raises(ValueError, match="right-court"):
        GameState(**values)
