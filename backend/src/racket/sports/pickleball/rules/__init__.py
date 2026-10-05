"""Pickleball rules engine: a pure, configurable function (ST-020; scoring-engine.md).

Published Language (context map R5). Pure stdlib: no I/O, clock or randomness (QD-TR-01).
"""

from racket.sports.pickleball.rules.config import (
    FaultKind,
    InvalidRulesConfig,
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
from racket.sports.pickleball.rules.presets import PRESETS, PROVISIONAL_UNVERIFIED
from racket.sports.pickleball.rules.state import GameState, declare_state, new_game

__all__ = [
    "PRESETS",
    "PROVISIONAL_UNVERIFIED",
    "DomainError",
    "FaultKind",
    "GameOver",
    "GameState",
    "IllegalState",
    "InvalidRulesConfig",
    "MatchFormat",
    "RallyOutcome",
    "RulesConfig",
    "ScoringSystem",
    "Side",
    "UnknownOutcome",
    "declare_state",
    "new_game",
]
