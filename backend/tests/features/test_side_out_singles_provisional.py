"""Binds tests/features/side_out_singles_provisional.feature, sprint-02 §7.5 (ST-041 for ST-035).

Written first (ST-041). RED until stretch ST-035 gives the engine a singles preset
(``preset_for``, seam in tests/support/contract.py) and two-number calls. Shared steps
("the game is ...", "any rally is applied", "the rally is refused ...") live in
scoring_steps.py.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.features.scoring_steps import *  # noqa: F403  (shared step fixtures)
from tests.support import contract
from tests.support import scoring as sc

pytestmark = [pytest.mark.red_until(story="ST-035"), pytest.mark.scoring]

scenarios("side_out_singles_provisional.feature")


def _singles_call(text: str) -> tuple[int, int]:
    parts = text.split("-")
    assert len(parts) == 2, f"not a singles call 'S-R': {text!r}"
    return int(parts[0]), int(parts[1])


def _declared(config: Any, serving: int, receiving: int, letter: str) -> Any:
    state = contract.DECLARE_STATE.load()(
        config,
        serving_side=sc.side(letter),
        serving_score=serving,
        receiving_score=receiving,
        server_number=None,
    )
    assert not sc.is_domain_error(state), f"engine refused {serving}-{receiving}: {state!r}"
    return state


@given(
    parsers.parse(
        'the rules preset "{name}" for singles with target {target:d} and margin {margin:d}'
    )
)
def singles_preset(ctx: dict[str, Any], name: str, target: int, margin: int) -> None:
    assert name == contract.PROVISIONAL_PRESET
    config = contract.PRESET_FOR.load()(name, "singles")
    assert config is not None, "no singles preset under the provisional rules"
    assert (config.points_to_win, config.win_by) == (target, margin)
    assert str(getattr(config.format, "value", config.format)) == "singles"
    ctx["config"] = config


@given(parsers.parse('a singles game called "{before}" with player {letter} serving'))
def singles_game(ctx: dict[str, Any], before: str, letter: str) -> None:
    serving, receiving = _singles_call(before)
    if (serving, receiving) == (0, 0):
        state = contract.NEW_GAME.load()(ctx["config"], sc.side(letter))
    else:
        state = _declared(ctx["config"], serving, receiving, letter)
    assert state.server_number is None, "a singles state has no server number"
    assert contract.SCORE_CALL.load()(state) == before
    ctx["before"] = ctx["state"] = state


@given(parsers.parse("a singles game that player {letter} has won {a:d}-{b:d}"))
def singles_won(ctx: dict[str, Any], letter: str, a: int, b: int) -> None:
    config = ctx["config"]
    state = _declared(config, a - 1, b, letter)
    state = sc.apply(state, sc.outcome_for("serving", state), config)
    assert not sc.is_domain_error(state), state
    assert state.is_over, state
    assert state.winner == sc.side(letter), state
    ctx["state"] = state


@given(parsers.parse("a singles game where the server's score is {score:d}"))
def server_score(ctx: dict[str, Any], score: int) -> None:
    # The receiver is one point behind (0 at 0-0), so no row is already game over.
    receiving = max(score - 1, 0)
    if score == 0:
        state = contract.NEW_GAME.load()(ctx["config"], sc.side("A"))
    else:
        state = _declared(ctx["config"], score, receiving, "A")
    ctx["state"] = state


@when(parsers.parse("the {winner} player wins the rally"))
def player_wins(ctx: dict[str, Any], winner: str) -> None:
    state = ctx["state"]
    ctx["result"] = sc.apply(state, sc.outcome_for(winner, state), ctx["config"])


@when("the server serves")
def server_serves(ctx: dict[str, Any]) -> None:
    ctx["result"] = ctx["state"]


@then(parsers.parse('the score is called "{after}" with player {letter} serving'))
def singles_called(ctx: dict[str, Any], after: str, letter: str) -> None:
    result = ctx["result"]
    assert not sc.is_domain_error(result), result
    assert result.serving_side == sc.side(letter), result
    assert contract.SCORE_CALL.load()(result) == after, result


@then(parsers.parse("the serve is expected from the {court} court"))
def serve_court(ctx: dict[str, Any], court: str) -> None:
    state = ctx["result"]
    serving = state.serving_side
    on_right = state.right_court_player[serving] == state.server_player
    assert ("right" if on_right else "left") == court, state
