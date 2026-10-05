"""MatchState: best of 1 or 3, match over, explicit first server and ends (ST-021).

sprint-01 §5 MatchState rows in order, negative first; scoring-engine.md §5. Configurations
are explicit test inputs, never rulebook claims (ADR 0009 part a).
"""

from __future__ import annotations

import dataclasses

import pytest

from racket.matches.domain import MatchOver, MatchState
from racket.sports.pickleball.rules import (
    DomainError,
    FaultKind,
    GameOver,
    IllegalState,
    RallyOutcome,
    RulesConfig,
    Side,
)

pytestmark = [pytest.mark.unit, pytest.mark.scoring]

A, B = Side.A, Side.B


def config(points_to_win: int = 3) -> RulesConfig:
    return RulesConfig(
        rules_version="TEST-MATCH",
        scoring_system="side_out",  # type: ignore[arg-type]
        format="doubles",  # type: ignore[arg-type]
        points_to_win=points_to_win,
        win_by=1,
        first_service_single_server=False,
    )


def ok(result: MatchState | DomainError) -> MatchState:
    assert isinstance(result, MatchState), result
    return result


def win_game(ms: MatchState, winner: Side, *, first_server: Side | None = None) -> MatchState:
    ms = ok(ms.start_game(first_server=first_server or winner, ends_switched=False))
    number = len(ms.games)
    while not ms.games[-1].state.is_over:
        ms = ok(ms.record_rally(number, RallyOutcome.won_by(winner)))
    return ms


def play(best_of: int, *winners: Side) -> MatchState:
    ms = MatchState.start(best_of=best_of, config=config())
    for winner in winners:
        ms = win_game(ms, winner)
    return ms


# ------------------------------------------------------------------ §5 row 1: MatchOver


@pytest.mark.parametrize(
    ("best_of", "winners", "game"), [(3, (A, A), 3), (1, (B,), 2), (3, (A, B, B), 3)]
)
def test_any_rally_after_the_match_is_decided_is_match_over(
    best_of: int, winners: tuple[Side, ...], game: int
) -> None:
    ms = play(best_of, *winners)
    for outcome in (
        RallyOutcome.won_by(A),
        RallyOutcome.replay(),
        RallyOutcome.fault(by=B, kind=FaultKind.NVZ),
    ):
        result = ms.record_rally(game, outcome)
        assert isinstance(result, MatchOver)
        assert result.message == "match is over"


def test_a_new_game_after_the_match_is_decided_is_match_over() -> None:
    assert isinstance(play(3, A, A).start_game(first_server=A, ends_switched=True), MatchOver)


def test_a_game_number_beyond_the_format_is_match_over() -> None:
    ms = ok(
        MatchState.start(best_of=1, config=config()).start_game(first_server=A, ends_switched=False)
    )
    assert isinstance(ms.record_rally(2, RallyOutcome.won_by(A)), MatchOver)


def test_match_over_is_a_rules_domain_error() -> None:
    assert issubclass(MatchOver, DomainError)


@pytest.mark.parametrize("best_of", [0, 2, 5, -1, True])
def test_only_best_of_one_or_three(best_of: int) -> None:
    with pytest.raises(ValueError, match="best_of"):
        MatchState.start(best_of=best_of, config=config())


def test_start_needs_a_rules_config() -> None:
    with pytest.raises(ValueError, match="config"):
        MatchState.start(best_of=1, config="PROVISIONAL-UNVERIFIED")  # type: ignore[arg-type]


def test_a_rally_for_a_game_not_started_is_illegal() -> None:
    ms = MatchState.start(best_of=3, config=config())
    assert isinstance(ms.record_rally(1, RallyOutcome.won_by(A)), IllegalState)
    ms = win_game(ms, A)
    assert isinstance(ms.record_rally(2, RallyOutcome.won_by(A)), IllegalState)


@pytest.mark.parametrize("number", [0, -1, True, "1"])
def test_a_game_number_that_is_not_a_positive_int_is_illegal(number: object) -> None:
    ms = ok(
        MatchState.start(best_of=3, config=config()).start_game(first_server=A, ends_switched=False)
    )
    assert isinstance(ms.record_rally(number, RallyOutcome.won_by(A)), IllegalState)  # type: ignore[arg-type]


def test_starting_a_game_while_one_is_in_play_is_illegal() -> None:
    ms = ok(
        MatchState.start(best_of=3, config=config()).start_game(first_server=A, ends_switched=False)
    )
    result = ms.start_game(first_server=B, ends_switched=True)
    assert isinstance(result, IllegalState)
    assert "not finished" in result.message


def test_a_rally_on_a_finished_game_of_an_open_match_is_game_over() -> None:
    ms = play(3, A)
    assert isinstance(ms.record_rally(1, RallyOutcome.won_by(B)), GameOver)


def test_an_unknown_outcome_is_returned_not_raised() -> None:
    ms = ok(
        MatchState.start(best_of=1, config=config()).start_game(first_server=A, ends_switched=False)
    )
    assert isinstance(ms.record_rally(1, "A wins"), DomainError)  # type: ignore[arg-type]


@pytest.mark.parametrize(("first", "ends"), [("A", False), (A, "yes"), (None, True)])
def test_game_inputs_are_explicit_and_typed(first: object, ends: object) -> None:
    ms = MatchState.start(best_of=3, config=config())
    assert isinstance(ms.start_game(first_server=first, ends_switched=ends), IllegalState)  # type: ignore[arg-type]


# ------------------------------------------------------------------ §5 row 2: deciding


def test_best_of_three_is_decided_after_two_games_won_by_one_side() -> None:
    ms = play(3, B, B)
    assert ms.is_over
    assert ms.winner is B
    assert (ms.games_won(B), ms.games_won(A)) == (2, 0)


def test_best_of_three_is_open_at_one_game_each() -> None:
    ms = play(3, A, B)
    assert not ms.is_over
    assert ms.winner is None
    assert len(ok(ms.start_game(first_server=A, ends_switched=True)).games) == 3


def test_best_of_one_is_decided_by_its_game() -> None:
    ms = play(1, B)
    assert (ms.is_over, ms.winner, ms.games_won(B)) == (True, B, 1)


def test_a_new_match_is_open_with_no_games() -> None:
    ms = MatchState.start(best_of=3, config=config())
    assert (ms.is_over, ms.winner, ms.games, ms.games_won(A)) == (False, None, (), 0)


# ------------------------------------------------------------------ §5 row 3: explicit inputs


@pytest.mark.parametrize("second_first_server", [A, B])
def test_first_server_of_game_two_is_taken_from_input_never_inferred(
    second_first_server: Side,
) -> None:
    ms = play(3, A)
    ms = ok(ms.start_game(first_server=second_first_server, ends_switched=True))
    game = ms.games[1]
    assert game.number == 2
    assert game.first_server is second_first_server
    assert game.state.serving_side is second_first_server
    assert (game.state.score_a, game.state.score_b) == (0, 0)
    assert game.ends_switched is True
    assert ms.games[0].ends_switched is False


def test_rallies_go_to_the_named_game_only() -> None:
    ms = play(3, A)
    ms = ok(ms.start_game(first_server=B, ends_switched=True))
    ms = ok(ms.record_rally(2, RallyOutcome.won_by(B)))
    assert (ms.games[1].state.score_a, ms.games[1].state.score_b) == (0, 1)
    assert ms.games[0].state.winner is A


def test_match_keeps_its_rules_version_and_is_immutable() -> None:
    ms = play(1, A)
    assert ms.rules_version == "TEST-MATCH"
    assert ms.config == config()
    with pytest.raises(dataclasses.FrozenInstanceError):
        ms.best_of = 3  # type: ignore[misc]
    assert play(1, A) == ms
