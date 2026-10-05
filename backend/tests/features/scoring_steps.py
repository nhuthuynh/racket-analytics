"""Shared steps for the scoring feature files (ST-020, ST-021, ST-023).

Imported by the four ``test_*`` modules that bind tests/features/side_out_doubles_provisional,
faults_provisional, match_structure and scoring_engine_mechanics. The engine is reached only
through the seams in ``tests.support.contract`` (ADR 0012).
"""

from __future__ import annotations

import random
import re
from typing import Any

import pytest
from pytest_bdd import given, parsers, then, when

from tests.support import contract
from tests.support import scoring as sc


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


# ------------------------------------------------------------------ configuration


@given(
    parsers.parse(
        'the rules preset "{name}" with target {target:d}, margin {margin:d} '
        "and the first-service exception"
    )
)
def preset_with_values(ctx: dict[str, Any], name: str, target: int, margin: int) -> None:
    assert name == contract.PROVISIONAL_PRESET
    config = sc.provisional_preset()
    assert config.points_to_win == target
    assert config.win_by == margin
    assert config.first_service_single_server is True
    assert config.scoring_system == "side_out"
    assert config.format == "doubles"
    ctx["config"] = config


@given(parsers.parse('the rules preset "{name}"'))
def preset(ctx: dict[str, Any], name: str) -> None:
    assert name == contract.PROVISIONAL_PRESET
    ctx["config"] = sc.provisional_preset()


@given(
    parsers.parse(
        "a game configured with target {target:d} and margin {margin:d} "
        "where only the serving side scores"
    )
)
def configured_game(ctx: dict[str, Any], target: int, margin: int) -> None:
    ctx["config"] = sc.mechanics_config(target, margin)


# ------------------------------------------------------------------ game states


@given(parsers.parse('a doubles game called "{before}" with side {letter} serving'))
def game_called(ctx: dict[str, Any], before: str, letter: str) -> None:
    config = ctx["config"]
    call = sc.parse_call(before)
    if call == sc.Call(0, 0, 2) and config.first_service_single_server:
        # SOD-01/02: the game start itself, so the first-service exception is exercised.
        state = contract.NEW_GAME.load()(config, sc.side(letter))
        assert sc.call_of(state) == call, f"new game is {sc.call_of(state)}, expected {call}"
    else:
        state = sc.state_from_call(config, call, letter)
    assert state.serving_side == sc.side(letter)
    ctx["before"] = state
    ctx["state"] = state


@given(parsers.parse("side {letter} is serving with the score {a:d} to {b:d}"))
def serving_with_score(ctx: dict[str, Any], letter: str, a: int, b: int) -> None:
    state = sc.state_from_call(ctx["config"], sc.Call(a, b, 1), letter)
    ctx["before"] = ctx["state"] = state


@given(parsers.parse("a game at {a:d}-{b:d} with side {letter} serving at server {n:d}"))
def game_at(ctx: dict[str, Any], a: int, b: int, letter: str, n: int) -> None:
    ctx["config"] = sc.mechanics_config(11, 2)
    state = sc.state_from_call(ctx["config"], sc.Call(a, b, n), letter)
    ctx["before"] = ctx["state"] = state


@given(parsers.parse("a doubles game that side {letter} has won {a:d}-{b:d}"))
def game_won(ctx: dict[str, Any], letter: str, a: int, b: int) -> None:
    config = ctx["config"]
    state = sc.state_from_call(config, sc.Call(a - 1, b, 1), letter)
    state = sc.apply(state, sc.outcome_for("serving", state), config)
    assert not sc.is_domain_error(state), state
    assert state.is_over, state
    assert state.winner == sc.side(letter), state
    assert (sc.score_of(state, sc.side(letter)), sc.score_of(state, sc.side(letter).other)) == (
        a,
        b,
    )
    ctx["state"] = state


@given("a game has ended")
def a_game_has_ended(ctx: dict[str, Any]) -> None:
    config = ctx["config"] = sc.mechanics_config(11, 2)
    start = contract.NEW_GAME.load()(config, sc.side("A"))
    ctx["state"] = sc.play_until_over(start, sc.side("A"), config)


# ------------------------------------------------------------------ rallies


@when(parsers.parse("the {winner} side wins the rally"))
def side_wins(ctx: dict[str, Any], winner: str) -> None:
    state = ctx["state"]
    ctx["result"] = sc.apply(state, sc.outcome_for(winner, state), ctx["config"])


@when(parsers.parse("side {letter} wins the rally"))
def lettered_side_wins(ctx: dict[str, Any], letter: str) -> None:
    outcome = contract.RALLY_OUTCOME.load().won_by(sc.side(letter))
    ctx["result"] = sc.apply(ctx["state"], outcome, ctx["config"])


@when(parsers.parse("the {who} side commits a {fault} fault"))
def side_faults(ctx: dict[str, Any], who: str, fault: str) -> None:
    state = ctx["state"]
    ctx["result"] = sc.apply(state, sc.fault_outcome(who, fault, state), ctx["config"])


@when("a rally is recorded as a replay")
def replay_recorded(ctx: dict[str, Any]) -> None:
    outcome = contract.RALLY_OUTCOME.load().replay()
    ctx["result"] = sc.apply(ctx["state"], outcome, ctx["config"])


@when("any rally is applied")
@when("another rally is applied to that game")
def any_rally(ctx: dict[str, Any]) -> None:
    ctx["results"] = [
        sc.apply(ctx["state"], outcome, ctx["config"]) for outcome in sc.all_outcomes()
    ]


# ------------------------------------------------------------------ outcomes


@then(parsers.parse('the score is called "{after}" with side {letter} serving'))
def score_called(ctx: dict[str, Any], after: str, letter: str) -> None:
    result = ctx["result"]
    assert not sc.is_domain_error(result), result
    assert result.serving_side == sc.side(letter), result
    assert sc.call_of(result) == sc.parse_call(after), f"called {sc.call_of(result)}: {result!r}"
    assert not result.is_over


@then(parsers.parse("the score is still {a:d}-{b:d} with side {letter} serving at server {n:d}"))
def score_still(ctx: dict[str, Any], a: int, b: int, letter: str, n: int) -> None:
    result = ctx["result"]
    assert not sc.is_domain_error(result), result
    assert result == ctx["before"], "a replay changed the game state (P8)"
    assert result.serving_side == sc.side(letter)
    assert sc.call_of(result) == sc.Call(a, b, n)


_WON = re.compile(r"won by (?:side )?(?P<side>[AB])(?: (?P<a>\d+)-(?P<b>\d+))?")


@then(parsers.parse("the game is {state}"))
def game_is(ctx: dict[str, Any], state: str) -> None:
    result = ctx["result"]
    assert not sc.is_domain_error(result), result
    if state == "not over":
        assert not result.is_over, result
        assert result.winner is None, result
        return
    m = _WON.fullmatch(state)
    assert m, f"unknown game state wording {state!r}"
    winner = sc.side(m["side"])
    assert result.is_over, result
    assert result.winner == winner, result
    if m["a"]:
        got = (sc.score_of(result, winner), sc.score_of(result, winner.other))
        assert got == (int(m["a"]), int(m["b"])), result


@then("the same server serves again from the other court")
def same_server_other_court(ctx: dict[str, Any]) -> None:
    before, after = ctx["before"], ctx["result"]
    assert not sc.is_domain_error(after), after
    serving = before.serving_side
    assert after.server_player == before.server_player
    assert (
        before.right_court_player[serving] == before.server_player
    )  # server starts on the right here
    assert after.right_court_player[serving] != before.right_court_player[serving], (
        "server did not switch"
    )


@then("the receiving players keep their positions")
def receivers_keep_positions(ctx: dict[str, Any]) -> None:
    before, after = ctx["before"], ctx["result"]
    receiving = before.serving_side.other
    assert after.right_court_player[receiving] == before.right_court_player[receiving]


@then(parsers.parse('the rally is refused with a "{message}" message'))
def refused(ctx: dict[str, Any], message: str) -> None:
    results = ctx.get("results") or [ctx["result"]]
    expected = contract.MATCH_OVER if "match" in message else contract.GAME_OVER
    error_type = expected.load()
    for result in results:
        assert isinstance(result, error_type), f"expected {error_type.__name__}, got {result!r}"
        assert message in result.message.lower(), result.message


# ------------------------------------------------------------------ configuration validation

_FIELDS = {"target": "points_to_win", "margin": "win_by"}


@given(parsers.parse("a game configuration with {field} set to {value:d}"))
def configuration_with(ctx: dict[str, Any], field: str, value: int) -> None:
    values = {"points_to_win": 11, "win_by": 2}
    values[_FIELDS[field]] = value
    ctx["values"] = values


@when("the configuration is loaded")
def load_configuration(ctx: dict[str, Any]) -> None:
    error_type = contract.INVALID_RULES_CONFIG.load()
    values = ctx["values"]
    try:
        ctx["config"] = sc.mechanics_config(values["points_to_win"], values["win_by"])
    except error_type as exc:
        ctx["error"] = exc


@then(parsers.parse("it is refused with a message naming {field}"))
def refused_naming(ctx: dict[str, Any], field: str) -> None:
    assert "error" in ctx, f"configuration was accepted: {ctx.get('config')!r}"
    error = ctx["error"]
    assert error.field == _FIELDS[field]
    assert _FIELDS[field] in str(error)


# ------------------------------------------------------------------ replay determinism


@given(parsers.parse("a game with {count:d} recorded rally outcomes"))
def recorded_outcomes(ctx: dict[str, Any], count: int) -> None:
    config = ctx["config"] = sc.mechanics_config(50, 2)  # high target: 30 rallies cannot end it
    ctx["start"] = contract.NEW_GAME.load()(config, sc.side("A"))
    rng = random.Random(20261019)  # noqa: S311  (seeded test data, not security)
    ctx["outcomes"] = [sc.to_outcome(r) for r in sc.random_sequence(rng, count)]
    assert len(ctx["outcomes"]) == count


@when("the score sheet is rebuilt from those outcomes")
def rebuild(ctx: dict[str, Any]) -> None:
    fold = contract.RULES_FOLD.load()
    outcomes = ctx["outcomes"]
    ctx["rebuilt"] = [
        fold(outcomes[:k], ctx["config"], ctx["start"]) for k in range(len(outcomes) + 1)
    ]


@then("it is identical to the score sheet computed rally by rally")
def identical_sheet(ctx: dict[str, Any]) -> None:
    sheet = [ctx["start"]]
    for outcome in ctx["outcomes"]:
        nxt = sc.apply(sheet[-1], outcome, ctx["config"])
        assert not sc.is_domain_error(nxt), nxt
        sheet.append(nxt)
    assert ctx["rebuilt"] == sheet

