"""Capture & Media's published query port for other contexts (context map R2).

Match & Scoring composes its status/media read model from ``media_summary`` and never reads
``video_ingest`` tables itself (context map rule 1).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.orm import Session

from racket.platform.settings import Settings
from racket.platform.storage import ObjectStore
from racket.video_ingest.domain import ExpiryPolicy, MediaFacts, MediaUrlPolicy, UploadStatus
from racket.video_ingest.domain.object_refs import (
    STAGING_CHUNK,
    MultipartRef,
    ObjectRef,
    OriginalKey,
    StagingPrefix,
    UnsafeObjectRef,
)
from racket.video_ingest.domain.uploads import ORIGINAL_CONTENT_TYPE
from racket.video_ingest.repository import (
    PROBE_FAILED,
    MediaRepository,
    UploadRepository,
    media_assets,
    media_facts,
    upload_sessions,
)

# Part of the port: other contexts name upload states through here, never through the domain
# package (context map rule 1, R2-02).
__all__ = [
    "AbandonedUpload",
    "MediaFacts",
    "MediaLink",
    "MediaSummary",
    "MultipartRef",
    "ObjectRef",
    "OriginalKey",
    "PendingUpload",
    "StagingPrefix",
    "UnsafeObjectRef",
    "UploadStatus",
    "abandoned_upload_ids",
    "claim_abandoned_upload",
    "close_for_deleted_match",
    "forget_upload",
    "lock_upload_of_match",
    "media_link",
    "media_summary",
    "object_refs",
    "purge_match",
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
    """Take the match's upload row lock, held to the caller's commit. The global lock order is
    upload row, then match row (deletion-and-purge.md §3.1): the completing PATCH
    (``write_chunk`` -> ``mark_uploaded``), the upload creation, the probe refusal
    (``ProbeStage._reject``) and ``DELETE /matches/{id}`` all take them so; any new transaction
    that touches both must too, or it can deadlock with them (PE-050a-01, PE-050a-05). Waits
    for a PATCH in flight; a PATCH arriving later gets its 409."""
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


def _shared(session: Session, key: str, match_id: uuid.UUID) -> bool:
    """True when a row of another match names the same object key (§4.6 (2))."""
    names = sa.union_all(
        sa.select(media_assets.c.match_id).where(media_assets.c.object_key == key),
        sa.select(upload_sessions.c.match_id).where(upload_sessions.c.object_key == key),
    ).subquery()
    others = session.execute(
        sa.select(sa.func.count(sa.distinct(names.c.match_id))).where(names.c.match_id != match_id)
    ).scalar_one()
    return bool(others)


def object_refs(session: Session, match_id: uuid.UUID) -> list[ObjectRef]:
    """Every stored object of this match, as typed refs built from this match's rows only
    (SEC-S3-TM-01, deletion-and-purge.md §4.6). Raises ``UnsafeObjectRef`` before the caller
    makes any store call when a key has another shape or another match names it too. Order:
    open multipart uploads, then staging folders, then originals."""
    assets = session.execute(
        sa.select(media_assets.c.object_key).where(media_assets.c.match_id == match_id)
    ).all()
    uploads = session.execute(
        sa.select(
            upload_sessions.c.id,
            upload_sessions.c.object_key,
            upload_sessions.c.s3_upload_id,
            upload_sessions.c.status,
            upload_sessions.c.staged,
        ).where(upload_sessions.c.match_id == match_id)
    ).all()
    multipart: list[ObjectRef] = []
    staging: list[ObjectRef] = []
    for upload in uploads:
        prefix = StagingPrefix.of(upload.id)
        for chunk in upload.staged:
            if STAGING_CHUNK.fullmatch(str(chunk.key)) is None or not chunk.key.startswith(
                prefix.prefix
            ):
                raise UnsafeObjectRef("a staged chunk outside its upload's folder")
        staging.append(prefix)
        if upload.status is not UploadStatus.COMPLETE:
            multipart.append(MultipartRef(upload.object_key, upload.s3_upload_id))
    originals = sorted({str(r.object_key) for r in assets} | {str(u.object_key) for u in uploads})
    refs: list[ObjectRef] = [*multipart, *staging]
    for key in originals:
        refs.append(OriginalKey(key))
        if _shared(session, key, match_id):
            raise UnsafeObjectRef("another match names the same object")
    return refs


def purge_match(session: Session, match_id: uuid.UUID) -> int:
    """Delete this context's rows of the match, in the caller's transaction. Rows deleted."""
    rows = 0
    for statement in (
        sa.delete(media_facts).where(media_facts.c.match_id == match_id),
        sa.delete(media_assets).where(media_assets.c.match_id == match_id),
        sa.delete(upload_sessions).where(upload_sessions.c.match_id == match_id),
    ):
        rows += int(session.execute(statement).rowcount)  # type: ignore[attr-defined]
    return rows


@dataclass(frozen=True)
class AbandonedUpload:
    upload_id: uuid.UUID
    match_id: uuid.UUID
    owner_id: uuid.UUID
    refs: tuple[ObjectRef, ...]  # the open multipart upload, then the staging folder


def _abandoned(now: datetime, idle: timedelta) -> sa.ColumnElement[bool]:
    """The SQL form of ``ExpiryPolicy.is_abandoned`` (PE-038-01): only rows the purge frees are
    listed or locked, so an active upload is never held and non-candidates never fill a page."""
    c = upload_sessions.c
    return sa.and_(
        c.status != UploadStatus.COMPLETE,
        sa.or_(c.status == UploadStatus.EXPIRED, c.updated_at <= now - idle, c.expires_at <= now),
    )


def abandoned_upload_ids(
    session: Session,
    now: datetime,
    idle: timedelta,
    *,
    after: uuid.UUID | None = None,
    limit: int = 100,
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """``(upload_id, match_id)`` of the uploads the purge frees (ST-038; deletion-and-purge.md
    §4.4), one keyset page by id after ``after``. Takes no lock: each upload is claimed on its
    own (``claim_abandoned_upload``)."""
    query = sa.select(upload_sessions.c.id, upload_sessions.c.match_id).where(_abandoned(now, idle))
    if after is not None:
        query = query.where(upload_sessions.c.id > after)
    rows = session.execute(query.order_by(upload_sessions.c.id).limit(limit)).all()
    return [(uuid.UUID(str(r.id)), uuid.UUID(str(r.match_id))) for r in rows]


def claim_abandoned_upload(
    session: Session, upload_id: uuid.UUID, now: datetime, idle: timedelta
) -> AbandonedUpload | None:
    """Lock one abandoned upload until the caller commits (``FOR UPDATE SKIP LOCKED``). None when
    a request or another pass holds it, or it is no longer abandoned (a chunk arrived). Refs are
    typed and built from the row's ids (``UnsafeObjectRef`` on a bad shape, §4.6)."""
    row = session.execute(
        sa.select(
            upload_sessions.c.id,
            upload_sessions.c.match_id,
            upload_sessions.c.owner_id,
            upload_sessions.c.object_key,
            upload_sessions.c.s3_upload_id,
            upload_sessions.c.status,
            upload_sessions.c.updated_at,
            upload_sessions.c.expires_at,
        )
        .where(upload_sessions.c.id == upload_id, _abandoned(now, idle))
        .with_for_update(skip_locked=True)
    ).one_or_none()
    policy = ExpiryPolicy(idle=idle, max_age=max(idle, timedelta(seconds=1)))
    if row is None or not policy.is_abandoned(
        row.status.value, row.updated_at, row.expires_at, now=now
    ):
        return None
    refs = (MultipartRef(row.object_key, row.s3_upload_id), StagingPrefix.of(row.id))
    return AbandonedUpload(row.id, row.match_id, row.owner_id, refs)


def forget_upload(session: Session, upload_id: uuid.UUID) -> None:
    """Delete the session row once its bytes are gone: no longer listed or resumable (HEAD and
    PATCH then answer 404, IT-03-09). In the caller's transaction."""
    session.execute(sa.delete(upload_sessions).where(upload_sessions.c.id == upload_id))
