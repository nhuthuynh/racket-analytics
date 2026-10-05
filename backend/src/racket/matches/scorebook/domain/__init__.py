"""Scorebook domain (pure): values, the aggregate's scored part and its projection."""

from racket.matches.scorebook.domain.book import (
    Change,
    CommandContext,
    GameStart,
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
    "MatchIsOver",
    "MatchNotReady",
    "NothingToUndo",
    "OutcomeInput",
    "Rally",
    "RallyNotFound",
    "RallyTimes",
    "Scorebook",
    "StaleMatch",
    "canonical_bytes",
    "project",
    "rules_for",
]
