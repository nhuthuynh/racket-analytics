"""Refusals of scorebook commands (match-aggregate §3). Each is an ``AppError`` with a fixed
status and code (api-sprint-00 §3 envelope; codes listed in ``racket.platform.errors``)."""

from __future__ import annotations

from racket.platform.errors import Conflict


class MatchNotReady(Conflict):
    """I1: tagging needs a received video (NFR-060)."""

    code = "match_not_ready"


class StaleMatch(Conflict):
    """The client's ``If-Match`` version is not the current one (IT-02-04)."""

    code = "stale_match"


class GameNotStarted(Conflict):
    code = "game_not_started"


class GameNotOver(Conflict):
    """I3: game n+1 starts only after game n is over in the projection."""

    code = "game_not_over"


class GameIsOver(Conflict):
    """I7: the projection says the current game is over; start the next one."""

    code = "game_over"


class MatchIsOver(Conflict):
    """I3/I7: the match is decided."""

    code = "match_over"


class DecisionNeeded(Conflict):
    """FR-053: rallies marked "needs your decision" must be resolved before a new tag."""

    code = "decision_needed"


class RallyNotFound(Conflict):
    """A rally id that is not a kept rally of this match (the match itself is owned)."""

    status, code = 404, "not_found"


class NothingToUndo(Conflict):
    code = "nothing_to_undo"
