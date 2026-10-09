"""Capture & Media's published query port for other contexts (context map R2).

Match & Scoring composes its status/media read model from ``media_summary`` and never reads
``video_ingest`` tables itself (context map rule 1).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from racket.platform.settings import Settings
from racket.platform.storage import ObjectStore
from racket.video_ingest.domain import MediaFacts, MediaUrlPolicy, UploadStatus
from racket.video_ingest.domain.uploads import ORIGINAL_CONTENT_TYPE
from racket.video_ingest.repository import PROBE_FAILED, MediaRepository, UploadRepository

# Part of the port: other contexts name upload states through here, never through the domain
# package (context map rule 1, R2-02).
__all__ = [
    "MediaFacts",
    "MediaLink",
    "MediaSummary",
    "PendingUpload",
    "UploadStatus",
    "close_for_deleted_match",
    "lock_upload_of_match",
    "media_link",
    "media_summary",
]


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


@dataclass(frozen=True)
class MediaLink:
    """A short-lived GET link to the match's original video (ST-037; NFR-055). ``repr`` hides
    the URL: it is a bearer secret and never reaches a log line (NFR-069)."""

    url: str = field(repr=False)
    expires_in_s: int


def media_link(
    session: Session,
    store: ObjectStore,
    settings: Settings,
    match_id: uuid.UUID,
    *,
    session_token: str | None,
) -> MediaLink | None:
    """The link to the received video of ``match_id``, or ``None`` while there is none. The
    caller has already checked that the match is the requester's (I9)."""
    asset = MediaRepository(session).asset_for_match(match_id)
    if asset is None:
        return None
    policy = MediaUrlPolicy(ttl_seconds=settings.media_url_ttl_seconds)
    url = store.presigned_get(
        asset.object_key,
        policy.ttl_seconds,
        public_endpoint=settings.s3_public_endpoint_url,
        content_type=ORIGINAL_CONTENT_TYPE,  # QA-RV1-05: also for originals stored before
    )
    return MediaLink(policy.check(url, session_token=session_token), policy.ttl_seconds)


def lock_upload_of_match(session: Session, match_id: uuid.UUID) -> None:
    """Take the match's upload row lock, held to the caller's commit. Lock order is upload row,
    then match row: the completing PATCH (``write_chunk`` -> ``mark_uploaded``) and the upload
    creation take them so, and a caller that then locks the match must too, or the two
    deadlock (PE-050a-01). Waits for a PATCH in flight; a PATCH arriving later gets its 409."""
    UploadRepository(session).for_match(match_id, for_update=True)


def close_for_deleted_match(session: Session, match_id: uuid.UUID, at: datetime) -> None:
    """The match was deleted (ST-050; deletion-and-purge.md §3.1 step 4): a receiving upload
    is expired and forgets its file name, under the upload row lock, so a racing PATCH (which
    takes the same lock) stores nothing more. Its bytes are left for the purge."""
    upload = UploadRepository(session).for_match(match_id, for_update=True)
    if upload is not None and upload.status is UploadStatus.RECEIVING:
        upload.status = UploadStatus.EXPIRED
        upload.file = None
        upload.updated_at = at
