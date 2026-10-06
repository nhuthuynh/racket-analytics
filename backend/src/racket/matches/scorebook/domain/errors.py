"""Refusals of scorebook commands (match-aggregate §3). Each is an ``AppError`` with a fixed
status and code (api-sprint-00 §3 envelope; codes listed in ``racket.platform.errors``)."""

from __future__ import annotations

from racket.platform.errors import Conflict, ValidationFailed


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


class RulesUnavailable(Conflict):
    """PE-S2-R1-05 (BE-D1-05): the match's (``rules_version``, ``format``) pair has no rules
    preset (today: singles, until ST-035), so no game can start and no rally can be tagged."""

    code = "rules_unavailable"


class ScorebookFull(ValidationFailed):
    """SEC-S2-R1-01: the match holds its cap of stored rallies (``too_many_rallies``) or of
    audit rows (``too_many_changes``); nothing more is written (ASVS 5.0 2.4.1)."""

    code = "scorebook_full"
