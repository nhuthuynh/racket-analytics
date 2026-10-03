"""Capture & Media's published query port for other contexts (context map R2).

Match & Scoring composes its status/media read model from ``media_summary`` and never reads
``video_ingest`` tables itself (context map rule 1).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from racket.video_ingest.domain import MediaFacts, UploadStatus
from racket.video_ingest.repository import PROBE_FAILED, MediaRepository, UploadRepository


@dataclass(frozen=True)
class MediaSummary:
    upload_state: UploadStatus | None  # None: no upload session yet
    facts: MediaFacts | None
    probe_failed: bool


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
    return MediaSummary(
        upload_state=UploadRepository(session).state_for_match(match_id),
        facts=facts,
        probe_failed=asset is not None and asset.probe_status == PROBE_FAILED,
    )
