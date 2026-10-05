"""Match & Scoring's published command port for Capture & Media (context map R2).

Sprint 0 exception (ADR 0011, hotspot H3), extended in Sprint 1 with ``reject_video`` and
``clear_rejection`` (ST-018): ``mark_uploaded`` runs inside the upload-completion
transaction, so "upload complete", ``Match.mark_uploaded`` and the probe job commit together.
"""

from __future__ import annotations

import uuid
from datetime import datetime

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


def reject_video(
    session: Session, match_id: uuid.UUID, owner_id: uuid.UUID, code: str, at: datetime
) -> None:
    """Capture & Media refused a file for this match (ST-018; api-sprint-01 §6.6). Runs in the
    caller's transaction, so the refusal and the clean-up commit together."""
    match = MatchRepository(session).get_owned(
        MatchId(match_id), OwnerId(owner_id), for_update=True
    )
    if match is None:
        raise NotFound("match vanished during upload")
    match.reject_video(code, at=at)


def refuse_upload(
    session: Session, match_id: uuid.UUID, owner_id: uuid.UUID, code: str, at: datetime
) -> None:
    """Capture & Media refused a file before receiving it (§6.3, §6.5). 409 when the match
    already has its video (PE-R1-01). Runs in the caller's transaction."""
    match = MatchRepository(session).get_owned(
        MatchId(match_id), OwnerId(owner_id), for_update=True
    )
    if match is None:
        raise NotFound("match vanished during upload")
    match.refuse_upload(code, at=at)


def clear_rejection(session: Session, match_id: uuid.UUID, owner_id: uuid.UUID) -> None:
    """A new upload was created: the last refusal is no longer shown (§5.2)."""
    match = MatchRepository(session).get_owned(
        MatchId(match_id), OwnerId(owner_id), for_update=True
    )
    if match is not None and match.rejection_code is not None:
        match.clear_rejection()
