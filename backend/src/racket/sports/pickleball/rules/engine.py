"""``apply`` and ``fold``: the pure scoring function (ST-020; scoring-engine.md §3; QD-RE-01).

``apply(state, outcome, config) -> GameState | DomainError`` never raises (QD-RE-05). Side-out
doubles is the only supported combination in Sprint 1. Every rule value comes from ``config``
(NFR-079).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from racket.sports.pickleball.rules.config import (
    MatchFormat,
    RulesConfig,
    ScoringSystem,
    Side,
)
from racket.sports.pickleball.rules.errors import (
    DomainError,
    GameOver,
    IllegalState,
    UnknownOutcome,
)
from racket.sports.pickleball.rules.outcome import RallyOutcome
from racket.sports.pickleball.rules.state import (
    FIRST_SERVER,
    SECOND_SERVER,
    GameState,
    meets_game_over,
    partner,
)


def _check_inputs(state: object, outcome: object, config: object) -> DomainError | None:
    if not isinstance(config, RulesConfig):
        return IllegalState("not a rules configuration")
    if not isinstance(state, GameState):
        return IllegalState("not a game state")
    if not isinstance(outcome, RallyOutcome):
        return UnknownOutcome()
    supported = (
        config.scoring_system is ScoringSystem.SIDE_OUT and config.format is MatchFormat.DOUBLES
    )
    if not supported or state.server_number is None:
        return IllegalState("state does not match a side-out doubles configuration")
    return None


def apply(state: GameState, outcome: RallyOutcome, config: RulesConfig) -> GameState | DomainError:
    """The state after one rally, or the reason the rally cannot be applied."""
    error = _check_inputs(state, outcome, config)
    if error is not None:
        return error
    if state.is_over:
        return GameOver()
    winner = outcome.rally_winner  # a fault: the other side won; the subtype is ignored (P7)
    if winner is None:
        return state  # replay is identity (P8)
    if winner is state.serving_side:
        return _point(state, winner, config)
    if state.server_number == FIRST_SERVER:
        return replace(
            state, server_number=SECOND_SERVER, server_player=partner(state.server_player)
        )
    return _side_out(state)


def _point(state: GameState, scorer: Side, config: RulesConfig) -> GameState:
    score_a = state.score_a + (1 if scorer is Side.A else 0)
    score_b = state.score_b + (1 if scorer is Side.B else 0)
    # The serving pair switches courts; the receivers keep their positions (SOD-05/06).
    switched = partner(state.right_court_player[scorer])
    winner = scorer if meets_game_over(score_a, score_b, config) else None
    if scorer is Side.A:
        return replace(
            state, score_a=score_a, score_b=score_b, winner=winner, right_court_a=switched
        )
    return replace(state, score_a=score_a, score_b=score_b, winner=winner, right_court_b=switched)


def _side_out(state: GameState) -> GameState:
    receiving = state.serving_side.other
    return replace(
        state,
        serving_side=receiving,
        server_number=FIRST_SERVER,
        server_player=state.right_court_player[receiving],
    )


def fold(
    outcomes: Iterable[RallyOutcome], config: RulesConfig, start: GameState
) -> GameState | DomainError:
    """Sequential ``apply`` from ``start``; the first ``DomainError`` stops it (P6)."""
    error = _check_inputs(start, RallyOutcome.replay(), config)
    if error is not None:
        return error
    state = start
    for outcome in outcomes:
        result = apply(state, outcome, config)
        if isinstance(result, DomainError):
            return result
        state = result
    return state
