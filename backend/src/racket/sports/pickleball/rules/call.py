"""The score call of a game state (FR-048; provisional format, ``@needs-verification``).

Doubles: three numbers, serving side's score first, then the server number ("4-6-1").
Singles (ST-035): two numbers, server's score first. The format is unverified [DOM G1 R6]
until the coach records a rule number (OQ-01, ADR 0009).
"""

from __future__ import annotations

from racket.sports.pickleball.rules.state import GameState


def score_call(state: GameState) -> str:
    serving = state.score_of(state.serving_side)
    receiving = state.score_of(state.serving_side.other)
    if state.server_number is None:
        return f"{serving}-{receiving}"
    return f"{serving}-{receiving}-{state.server_number}"
