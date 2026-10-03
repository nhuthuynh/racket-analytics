"""Match & Scoring's published command port for Capture & Media (context map R2).

Sprint 0 exception (ADR 0011, hotspot H3): ``mark_uploaded`` runs inside the upload-completion
transaction, so "upload complete", ``Match.mark_uploaded`` and the probe job commit together.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from racket.matches.domain import MatchId, OwnerId
from racket.matches.repository import MatchRepository
from racket.platform.errors import NotFound


def owns_match(session: Session, match_id: uuid.UUID, owner_id: uuid.UUID) -> bool:
    return MatchRepository(session).get_owned(MatchId(match_id), OwnerId(owner_id)) is not None


def mark_uploaded(
    session: Session, match_id: uuid.UUID, owner_id: uuid.UUID, media_asset_id: uuid.UUID
) -> None:
    match = MatchRepository(session).get_owned(
        MatchId(match_id), OwnerId(owner_id), for_update=True
    )
    if match is None:
        raise NotFound("match vanished during upload")
    match.mark_uploaded(media_asset_id)
