"""Match & Scoring's published command port for Capture & Media (context map R2).

Sprint 0 exception (ADR 0011, hotspot H3), extended in Sprint 1 with ``reject_video`` and
``clear_rejection`` (ST-018): ``mark_uploaded`` runs inside the upload-completion
transaction, so "upload complete", ``Match.mark_uploaded`` and the probe job commit together.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from racket.matches.domain import MatchId, OwnerId
from racket.matches.repository import MatchRepository, matches
from racket.matches.scorebook.domain import project
from racket.matches.scorebook.repository import ScorebookRepository
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


@dataclass(frozen=True)
class LiveSheet:
    """The projected score sheet of a live match at ``version`` (published to Analytics, R6)."""

    version: int
    owner_id: uuid.UUID
    sheet: dict[str, Any]


def lock_live_sheet(session: Session, match_id: uuid.UUID) -> LiveSheet | None:
    """The sheet of a live match, read under the match row ``FOR SHARE`` lock, which the caller
    holds to its commit (analytics-snapshots.md §4.2 step 2, invariant S8). ``None`` when the
    match does not exist or is deleted, so a snapshot is never written for it."""
    owner = session.execute(
        sa.select(matches.c.owner_id)
        .where(*MatchRepository.live(match_id))
        .with_for_update(read=True)
    ).scalar_one_or_none()
    if owner is None:
        return None
    book = ScorebookRepository(session).load(match_id)
    return LiveSheet(book.version, uuid.UUID(str(owner)), project(book))
