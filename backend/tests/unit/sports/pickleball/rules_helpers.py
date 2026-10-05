"""Shared helpers for the BE rules-engine unit tests (ST-020). Explicit test configurations,
never rulebook claims (ADR 0009 part a)."""

from __future__ import annotations

from typing import Any

from racket.sports.pickleball.rules import GameState, RulesConfig, Side, declare_state

A, B = Side.A, Side.B


def config(points_to_win: int = 11, win_by: int = 2, *, first_service: bool = False) -> RulesConfig:
    return RulesConfig(
        rules_version="TEST-UNIT",
        scoring_system="side_out",  # type: ignore[arg-type]
        format="doubles",  # type: ignore[arg-type]
        points_to_win=points_to_win,
        win_by=win_by,
        first_service_single_server=first_service,
    )


def declared(serving: int, receiving: int, number: int, side: Side = A, **cfg: Any) -> GameState:
    state = declare_state(
        config(**cfg),
        serving_side=side,
        serving_score=serving,
        receiving_score=receiving,
        server_number=number,
    )
    assert isinstance(state, GameState), state
    return state


def call(state: GameState) -> tuple[int, int, int | None]:
    serving = state.score_of(state.serving_side)
    return serving, state.score_of(state.serving_side.other), state.server_number
