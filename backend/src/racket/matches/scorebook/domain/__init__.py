"""Scorebook domain (pure): values, the aggregate's scored part and its projection."""

from racket.matches.scorebook.domain.book import (
    Change,
    CommandContext,
    GameStart,
    Limits,
    Rally,
    Scorebook,
)
from racket.matches.scorebook.domain.errors import (
    DecisionNeeded,
    GameIsOver,
    GameNotOver,
    GameNotStarted,
    MatchIsOver,
    MatchNotReady,
    NothingToUndo,
    RallyNotFound,
    RulesUnavailable,
    ScorebookFull,
    StaleMatch,
)
from racket.matches.scorebook.domain.projection import (
    NEEDS_DECISION,
    UNOFFICIAL_LABEL,
    canonical_bytes,
    project,
    rules_for,
)
from racket.matches.scorebook.domain.values import (
    Ending,
    InvalidOutcome,
    InvalidRally,
    OutcomeInput,
    RallyTimes,
)

__all__ = [
    "NEEDS_DECISION",
    "UNOFFICIAL_LABEL",
    "Change",
    "CommandContext",
    "DecisionNeeded",
    "Ending",
    "GameIsOver",
    "GameNotOver",
    "GameNotStarted",
    "GameStart",
    "InvalidOutcome",
    "InvalidRally",
    "Limits",
    "MatchIsOver",
    "MatchNotReady",
    "NothingToUndo",
    "OutcomeInput",
    "Rally",
    "RallyNotFound",
    "RallyTimes",
    "RulesUnavailable",
    "Scorebook",
    "ScorebookFull",
    "StaleMatch",
    "canonical_bytes",
    "project",
    "rules_for",
]
