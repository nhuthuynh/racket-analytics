"""Values of the scorebook: rally times and the outcome input (match-aggregate §2.1, §3 I5-I6).

Pure (ddd-guidelines §4.5). Built at the API edge from untrusted JSON, so every constructor
validates and raises a field-level ``ValidationFailed`` subclass; no input value is ever kept in
an error (api-sprint-01 §4.2).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeGuard

from racket.platform.errors import FieldError, ValidationFailed
from racket.sports.pickleball.rules import FaultKind, RallyOutcome, Side

MAX_MS = 2**48  # far beyond any video (150 min cap); keeps BIGINT and JSON integers exact
SLOTS = {"doubles": ("A1", "A2", "B1", "B2"), "singles": ("A1", "B1")}
OUTCOME_KEYS = frozenset({"ending", "winning_side", "responsible_player", "fault_kind"})


class InvalidRally(ValidationFailed):
    code = "invalid_rally"


class InvalidOutcome(ValidationFailed):
    code = "invalid_outcome"


class Ending(StrEnum):
    """Glossary "Rally ending" (FR-050). Forced and unforced errors stay apart in storage."""

    WINNER = "winner"
    UNFORCED_ERROR = "unforced_error"
    FORCED_ERROR = "forced_error"
    FAULT = "fault"
    REPLAY = "replay"


def _ms(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < MAX_MS:
        return value
    return None


@dataclass(frozen=True, slots=True)
class RallyTimes:
    """Integer milliseconds from the start of the video (QD-TR-02); ``end_ms`` is exclusive."""

    start_ms: int
    end_ms: int

    @classmethod
    def parse(cls, start_ms: object, end_ms: object) -> RallyTimes:
        start, end = _ms(start_ms), _ms(end_ms)
        if start is None or end is None:
            pairs = (("start_ms", start), ("end_ms", end))
            problems = [FieldError(name, "time_invalid") for name, v in pairs if v is None]
            raise InvalidRally("rally times are not integer ms", problems)
        if end <= start:
            raise InvalidRally("end before start", [FieldError("end_ms", "end_before_start")])
        return cls(start, end)

    def overlaps(self, other: RallyTimes) -> bool:
        return self.start_ms < other.end_ms and other.start_ms < self.end_ms

    def check_after(self, others: Iterable[RallyTimes]) -> None:
        """I5: no overlap with any kept rally."""
        if any(self.overlaps(o) for o in others):
            raise InvalidRally("overlaps a rally", [FieldError("start_ms", "overlaps_rally")])

    def check_within(self, video_ms: int | None) -> None:
        """QA-S2-API-02: the rally lies inside the video (``end_ms`` exclusive, so it may end
        exactly at the duration). ``None``: the duration is not known, no upper bound."""
        if video_ms is not None and self.end_ms > video_ms:
            raise InvalidRally("after the video", [FieldError("end_ms", "time_after_video")])


def _one_of(value: object, allowed: frozenset[str]) -> TypeGuard[str]:
    """Membership for untrusted JSON: a list or object is never hashed (IT-02-10)."""
    return isinstance(value, str) and value in allowed


ENDINGS = frozenset(e.value for e in Ending)
FAULT_KINDS = frozenset(k.value for k in FaultKind)


def _side(value: object) -> Side | None:
    return Side(value) if value in ("A", "B") else None


@dataclass(frozen=True, slots=True)
class OutcomeInput:
    """What the player said about one rally (match-aggregate §2.1). Nothing is inferred."""

    ending: Ending
    winning_side: Side | None
    responsible_player: str | None = None
    fault_kind: FaultKind | None = None

    @classmethod
    def parse(cls, body: Mapping[str, Any], *, format: str) -> OutcomeInput:
        if not isinstance(body, Mapping):
            raise InvalidOutcome("outcome is not an object", [FieldError(None, "invalid")])
        problems: list[FieldError] = []
        if any(key not in OUTCOME_KEYS for key in body):
            problems.append(FieldError(None, "unknown_field"))
        raw_ending = body.get("ending")
        ending = Ending(raw_ending) if _one_of(raw_ending, ENDINGS) else None
        if ending is None:
            problems.append(FieldError("ending", "ending_invalid"))
        raw_side = body.get("winning_side")
        side = _side(raw_side)
        if raw_side is not None and side is None:
            problems.append(FieldError("winning_side", "side_invalid"))
        elif ending is Ending.REPLAY and side is not None:
            problems.append(FieldError("winning_side", "replay_has_no_side"))
        elif ending not in (None, Ending.REPLAY) and side is None:
            problems.append(FieldError("winning_side", "side_required"))
        player = body.get("responsible_player")
        if player is not None:
            if not isinstance(player, str) or player not in SLOTS.get(format, ()):
                problems.append(FieldError("responsible_player", "player_invalid"))
            elif ending is Ending.REPLAY:
                problems.append(FieldError("responsible_player", "replay_has_no_player"))
            elif side is not None and ending is not None:
                on_winning = player[0] == side.value
                if ending is Ending.WINNER and not on_winning:
                    problems.append(FieldError("responsible_player", "must_be_on_winning_side"))
                elif ending is not Ending.WINNER and on_winning:
                    problems.append(FieldError("responsible_player", "must_be_on_losing_side"))
        raw_kind = body.get("fault_kind")
        kind = FaultKind(raw_kind) if _one_of(raw_kind, FAULT_KINDS) else None
        if raw_kind is not None:
            if kind is None:
                problems.append(FieldError("fault_kind", "fault_kind_invalid"))
            elif ending is not Ending.FAULT:
                problems.append(FieldError("fault_kind", "only_for_fault"))
        if problems or ending is None:
            raise InvalidOutcome("outcome is not valid", problems)
        return cls(ending, side, player, kind)

    def to_engine(self) -> RallyOutcome:
        """§2.1: the engine needs only who won; the ending detail is analytics data (P7)."""
        if self.winning_side is None:
            return RallyOutcome.replay()
        if self.ending is Ending.FAULT:
            return RallyOutcome.fault(
                by=self.winning_side.other, kind=self.fault_kind or FaultKind.OTHER
            )
        return RallyOutcome.won_by(self.winning_side)

    def as_json(self) -> dict[str, str | None]:
        return {
            "ending": self.ending.value,
            "winning_side": None if self.winning_side is None else self.winning_side.value,
            "responsible_player": self.responsible_player,
            "fault_kind": None if self.fault_kind is None else self.fault_kind.value,
        }
