"""Capture & Media's published query port for other contexts (context map R2).

Match & Scoring composes its status/media read model from ``media_summary`` and never reads
``video_ingest`` tables itself (context map rule 1).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from racket.video_ingest.domain import MediaFacts, UploadStatus
from racket.video_ingest.repository import PROBE_FAILED, MediaRepository, UploadRepository

# Part of the port: other contexts name upload states through here, never through the domain
# package (context map rule 1, R2-02).
__all__ = ["MediaFacts", "MediaSummary", "PendingUpload", "UploadStatus", "media_summary"]


@dataclass(frozen=True)
class PendingUpload:
    """An upload session that is not complete: the resume source of truth (flows D-3, U-04).
    Only ever shown in its owner's match read model (T-UV-8)."""

    upload_id: uuid.UUID
    state: str  # "receiving" | "expired"
    offset: int
    length: int
    expires_at: datetime | None
    file_name: str | None
    file_last_modified_ms: int | None
    head_sha256: str | None


@dataclass(frozen=True)
class MediaSummary:
    upload_state: UploadStatus | None  # None: no upload session yet
    facts: MediaFacts | None
    probe_failed: bool
    pending: PendingUpload | None = None


def media_summary(session: Session, match_id: uuid.UUID) -> MediaSummary:
    media = MediaRepository(session)
    asset = media.asset_for_match(match_id)
    row = media.facts_for_match(match_id) if asset is not None else None
    facts = None
    if row is not None and row.duration_ms is not None:
        facts = MediaFacts(
            container=row.container,
            video_codec=row.video_codec,
            duration_ms=int(row.duration_ms),
            fps=float(row.fps),
            vfr=bool(row.vfr),
            width=int(row.width),
            height=int(row.height),
            has_audio=bool(row.has_audio),
        )
    upload = UploadRepository(session).for_match(match_id)
    pending = None
    state = None if upload is None else upload.status
    if upload is not None and upload.status is not UploadStatus.COMPLETE:
        expired = upload.is_expired(datetime.now(UTC))
        state = UploadStatus.EXPIRED if expired else upload.status
        pending = PendingUpload(
            upload_id=upload.id,
            state=state.value,
            offset=upload.offset,
            length=upload.length,
            expires_at=upload.expires_at,
            file_name=None if expired else upload.file_name,
            file_last_modified_ms=None if expired else upload.file_last_modified_ms,
            head_sha256=None if expired else upload.head_sha256,
        )
    return MediaSummary(
        upload_state=state,
        facts=facts,
        probe_failed=asset is not None and asset.probe_status == PROBE_FAILED,
        pending=pending,
    )
