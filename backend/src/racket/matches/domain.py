"""Match & Scoring domain: the minimal ``Match`` aggregate for Sprint 0 (ST-006).

Pure Python: no framework imports (ddd-guidelines §4.5; tests/unit/test_architecture.py).
The aggregate root guards its invariants and carries ``owner_id`` (ddd-guidelines §4.9).
Persistence maps this class imperatively in ``racket.matches.repository``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Self

from racket.platform.errors import Conflict, ValidationFailed

TITLE_MAX = 120


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

    def can_be_read_by(self, owner_id: OwnerId) -> bool:
        return self.owner_id == owner_id
