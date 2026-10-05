"""Match & Scoring domain: the minimal ``Match`` aggregate for Sprint 0 (ST-006).

Pure Python: no framework imports (ddd-guidelines §4.5; tests/unit/test_architecture.py).
The aggregate root guards its invariants and carries ``owner_id`` (ddd-guidelines §4.9).
Persistence maps this class imperatively in ``racket.matches.repository``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Self

from racket.matches.match_state import GameRecord, MatchOver, MatchState  # ST-021 score
from racket.matches.participants import (  # ST-016 setup values (ADR 0024)
    InvalidParticipants,
    InvalidSetup,
    MatchParticipant,
    MatchSetup,
    Participants,
)
from racket.platform.errors import Conflict, ValidationFailed

__all__ = [
    "GameRecord",
    "InvalidParticipants",
    "InvalidSetup",
    "MatchOver",
    "MatchParticipant",
    "MatchSetup",
    "MatchState",
    "Participants",
]

TITLE_MAX = 120
DEFAULT_RULES_VERSION = "PROVISIONAL-UNVERIFIED"  # ADR 0009: the only shipped preset
REJECTION_CODES = ("not_a_video", "too_large", "too_long", "unsupported_video")  # §5.2


class InvalidId(ValueError):
    """A public ID that is not a UUID."""


class InvalidMatch(ValidationFailed):
    pass


class MatchAlreadyUploaded(Conflict):
    pass


@dataclass(frozen=True)
class _UuidId:
    value: uuid.UUID

    def __init__(self, raw: str | uuid.UUID) -> None:
        if isinstance(raw, uuid.UUID):
            value = raw
        else:
            try:
                value = uuid.UUID(str(raw).strip())
            except ValueError:
                raise InvalidId("not a UUID") from None
        object.__setattr__(self, "value", value)

    @classmethod
    def new(cls) -> Self:
        return cls(uuid.uuid4())

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, init=False)
class MatchId(_UuidId):
    pass


@dataclass(frozen=True, init=False)
class OwnerId(_UuidId):
    pass


class MatchFormat(StrEnum):
    SINGLES = "singles"
    DOUBLES = "doubles"


class MatchStatus(StrEnum):
    """States of the aggregate itself. The API status is a read model (api-sprint-00 §5.1)."""

    AWAITING_UPLOAD = "awaiting_upload"
    VIDEO_RECEIVED = "video_received"


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(eq=False)
class Match:
    id: MatchId
    owner_id: OwnerId
    title: str
    format: MatchFormat
    status: MatchStatus = MatchStatus.AWAITING_UPLOAD
    media_asset_id: uuid.UUID | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    scoring_system: str = "side_out"
    # Set by the server, never by the client (T-MS-1); the only preset is ADR 0009's.
    rules_version: str = DEFAULT_RULES_VERSION
    played_on: date | None = None
    # Child values of the aggregate (ADR 0024); loaded and saved by the repository.
    participants: Participants | None = None
    # The last refusal of a file for this match (ST-018; api-sprint-01 §5.2 ``rejection``).
    rejection_code: str | None = None
    rejected_at: datetime | None = None

    @classmethod
    def set_up(cls, *, owner_id: OwnerId, setup: MatchSetup) -> Match:
        """A match from the validated setup answers (ST-016; api-sprint-01 §5.1)."""
        match = cls.create(owner_id=owner_id, title=setup.title, format=setup.format)
        match.scoring_system = setup.scoring_system
        match.played_on = setup.played_on
        match.participants = setup.participants
        return match

    @classmethod
    def create(cls, *, owner_id: OwnerId, title: str, format: str) -> Match:
        if not isinstance(owner_id, OwnerId):
            raise InvalidMatch("a match needs an owner")
        clean_title = (title or "").strip()
        if not 1 <= len(clean_title) <= TITLE_MAX:
            raise InvalidMatch("title must have 1 to 120 characters")
        try:
            match_format = MatchFormat(format)
        except ValueError:
            raise InvalidMatch("unknown match format") from None
        now = _now()
        return cls(
            id=MatchId.new(),
            owner_id=owner_id,
            title=clean_title,
            format=match_format,
            created_at=now,
            updated_at=now,
        )

    def mark_uploaded(self, media_asset_id: uuid.UUID) -> None:
        if self.status is not MatchStatus.AWAITING_UPLOAD:
            raise MatchAlreadyUploaded("match already has its video")
        self.media_asset_id = media_asset_id
        self.status = MatchStatus.VIDEO_RECEIVED
        self.updated_at = _now()

    def reject_video(self, code: str, *, at: datetime) -> None:
        """A refused file: back to "No video yet", with the reason (api-sprint-01 §6.6)."""
        if code not in REJECTION_CODES:
            raise InvalidMatch("unknown rejection code")
        self.status = MatchStatus.AWAITING_UPLOAD
        self.media_asset_id = None
        self.rejection_code = code
        self.rejected_at = at
        self.updated_at = at

    def refuse_upload(self, code: str, *, at: datetime) -> None:
        """A file refused before it was received (§6.3 size cap, first-chunk content check).

        Only a match still waiting for its video can record such a refusal: a received video
        is never undone by a later creation request (PE-R1-01)."""
        if self.status is not MatchStatus.AWAITING_UPLOAD:
            raise MatchAlreadyUploaded("match already has its video")
        self.reject_video(code, at=at)

    def clear_rejection(self) -> None:
        """A new upload starts: the last refusal is no longer shown (§5.2)."""
        self.rejection_code = None
        self.rejected_at = None

    def can_be_read_by(self, owner_id: OwnerId) -> bool:
        return self.owner_id == owner_id
