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
from racket.sports.pickleball.rules.presets import PRESETS, PROVISIONAL_UNVERIFIED

__all__ = [
    "PRESETS",
    "PROVISIONAL_UNVERIFIED",
    "FaultKind",
    "InvalidRulesConfig",
    "MatchFormat",
    "RulesConfig",
    "ScoringSystem",
    "Side",
]
