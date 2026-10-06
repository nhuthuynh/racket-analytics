"""Binds tests/features/mid_game_start.feature, sprint-02 §7.5 (ST-041; rows SOD-13..SOD-15).

The rows bind to the engine's declared state (``declare_state``, QD-RE-06), which ST-020
already ships, so they run green now; ST-034 (stretch) puts the same check behind the score
sheet and its UI. Ivy is on side A. Shared steps live in scoring_steps.py.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.features.scoring_steps import *  # noqa: F403  (shared step fixtures)
from tests.support import contract
from tests.support import scoring as sc

pytestmark = pytest.mark.scoring

scenarios("mid_game_start.feature")

HER_SIDE = "A"
_OTHER = {"A": "B", "B": "A"}


@given(parsers.parse('Ivy declares the start as "{start}" with her side {role}'))
def declares_start(ctx: dict[str, Any], start: str, role: str) -> None:
    assert role in ("serving", "receiving"), role
    call = sc.parse_call(start)
    serving_letter = HER_SIDE if role == "serving" else _OTHER[HER_SIDE]
    ctx["declared"] = contract.DECLARE_STATE.load()(
        ctx["config"],
        serving_side=sc.side(serving_letter),
        serving_score=call.serving,
        receiving_score=call.receiving,
        server_number=call.server_number,
    )


@when("she tags the first rally as won by her side")
def tags_first_rally(ctx: dict[str, Any]) -> None:
    state = ctx["declared"]
    assert not sc.is_domain_error(state), state
    outcome = contract.RALLY_OUTCOME.load().won_by(sc.side(HER_SIDE))
    ctx["result"] = sc.apply(state, outcome, ctx["config"])


@then(parsers.parse('the score is called "{after}" with her side serving'))
def called_with_her_side_serving(ctx: dict[str, Any], after: str) -> None:
    result = ctx["result"]
    assert not sc.is_domain_error(result), result
    assert result.serving_side == sc.side(HER_SIDE), result
    assert sc.call_of(result) == sc.parse_call(after), result
    assert contract.SCORE_CALL.load()(result) == after


@then("the declared start is accepted")
def accepted(ctx: dict[str, Any]) -> None:
    state = ctx["declared"]
    assert not sc.is_domain_error(state), state
    assert not state.is_over


@then("she is told why the start is impossible")
def start_refused(ctx: dict[str, Any]) -> None:
    state = ctx["declared"]
    assert isinstance(state, contract.ILLEGAL_STATE.load()), f"accepted: {state!r}"
    assert state.message, "a refusal must say why"
