"""tus 1.0.0 core: the upload application service (ST-008; ADR 0011 "PATCH algorithm").

The HTTP layer validates headers and reads the body; this service does steps 3-6:
lock the session row (``NOWAIT``), write the bytes as a multipart part or a staging object,
and on the final byte complete the object, mark the match uploaded and queue the probe job
in **one** transaction (NFR-060; AQS/SEC-07 2.3.1, 2.3.3). Every failure leaves the stored
offset unchanged (fail closed, AQS/SEC-12).
"""

from __future__ import annotations

import base64
import binascii
import logging
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from botocore.exceptions import ClientError
from psycopg.errors import LockNotAvailable, UniqueViolation
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from racket.analysis_jobs.domain import JobKey
from racket.analysis_jobs.queue import JobQueue
from racket.matches import public as matches
from racket.platform.errors import (
    AppError,
    BadRequest,
    Conflict,
    LengthRequired,
    NotFound,
    PayloadTooLarge,
    Unauthenticated,
)
from racket.platform.logs import SECURITY_LOGGER
from racket.platform.ratelimit import RateLimited, RateLimiter
from racket.platform.settings import Settings
from racket.platform.slis import SLIRecorder, UploadEvent
from racket.platform.storage import ObjectStore, is_missing_upload
from racket.players import public as players
from racket.video_ingest.domain import (
    ExpiryPolicy,
    ObjectKeyPolicy,
    OffsetMismatch,
    Rejection,
    UploadChecksum,
    UploadExpired,
    UploadFile,
    UploadPolicy,
    UploadSession,
    UploadStatus,
)
from racket.video_ingest.domain.uploads import ORIGINAL_CONTENT_TYPE
from racket.video_ingest.repository import MediaRepository, UploadRepository

PROBE_STAGE = "probe"
METADATA_MAX = 1024
_METADATA_KEY = re.compile(r"[^\s,]+")

log = logging.getLogger(__name__)
security_log = logging.getLogger(SECURITY_LOGGER)


class UploadNotFound(NotFound):
    pass


class UploadExists(Conflict):
    pass


class VideoTooLarge(AppError):
    """413 ``video_too_large``: ``Upload-Length`` above the cap, before any byte is stored."""

    status, code = 413, "video_too_large"


class NotAVideoUpload(AppError):
    """415 ``not_a_video``: the first bytes are not MP4/QuickTime (T-UV-1)."""

    status, code = 415, "not_a_video"


class UploadQuotaExceeded(AppError):
    """429 ``upload_quota_exceeded`` with ``retry_at: null``: waiting does not help (T-UV-7)."""

    status, code = 429, "upload_quota_exceeded"
    retry_at = None


def _utcnow() -> datetime:
    return datetime.now(UTC)


SLI = SLIRecorder()  # NFR-042 upload-completion SLI (api-sprint-01 §10); no user data


@dataclass(frozen=True)
class PatchTarget:
    """What the HTTP layer needs to check a PATCH's headers, read before the body arrives.

    A plain snapshot, so the read transaction can end before the (possibly slow) body is
    streamed: no pooled connection sits idle in transaction during the upload (R1-05)."""

    id: uuid.UUID
    offset: int
    length: int
    complete: bool
    expires_at: datetime | None = None


# tus integer headers are plain ASCII decimals. ``str.isdigit`` is not enough: it accepts
# '²' and other Unicode digits that ``int`` rejects, and ``int`` refuses more than 4300 digits,
# so both escaped as a 500 (SEC-R2-01, SEC-R2-02). 20 digits hold any 64-bit value.
HEADER_MAX_DIGITS = 20
_ASCII_DECIMAL = re.compile(r"[0-9]+")


def _significant_digits(raw: str | None) -> str | None:
    """The digits of ``raw`` without leading zeros (``"0"`` for zero), or ``None`` unless
    ``raw`` is one or more ASCII digits and nothing else. Stripping first keeps ``int`` away
    from its 4300-digit limit on zero-padded values."""
    if raw is None or not _ASCII_DECIMAL.fullmatch(raw):
        return None
    return raw.lstrip("0") or "0"


def parse_upload_length(raw: str | None, maximum: int) -> int:
    digits = _significant_digits(raw)
    if digits is None:
        raise BadRequest("Upload-Length must be a decimal integer")
    if len(digits) > HEADER_MAX_DIGITS:
        raise PayloadTooLarge("Upload-Length above the limit")  # an integer, just too large
    length = int(digits)
    if length < 1:
        raise BadRequest("Upload-Length must be at least 1")
    if length > maximum:
        raise PayloadTooLarge("Upload-Length above the limit")
    return length


def parse_upload_offset(raw: str | None) -> int:
    """PATCH ``Upload-Offset``: a non-negative ASCII decimal of at most 20 significant digits
    (§6.4 check 5)."""
    digits = _significant_digits(raw)
    if digits is None or len(digits) > HEADER_MAX_DIGITS:
        raise BadRequest("Upload-Offset must be a non-negative integer")
    return int(digits)


def parse_content_length(raw: str | None, maximum: int) -> int:
    """PATCH ``Content-Length``: present and an ASCII decimal (411), at most ``maximum`` (413)."""
    digits = _significant_digits(raw)
    if digits is None:
        raise LengthRequired("Content-Length required")
    if len(digits) > HEADER_MAX_DIGITS or int(digits) > maximum:
        raise PayloadTooLarge("chunk above the limit")
    return int(digits)


def validate_metadata(raw: str | None) -> None:
    """``Upload-Metadata`` must be well formed; no value is stored or used (data minimisation)."""
    if raw is None or raw == "":
        return
    if len(raw) > METADATA_MAX:
        raise BadRequest("Upload-Metadata too long")
    for pair in raw.split(","):
        parts = pair.strip().split(" ")
        if not 1 <= len(parts) <= 2 or not _METADATA_KEY.fullmatch(parts[0]):
            raise BadRequest("malformed Upload-Metadata")
        if len(parts) == 2:
            try:
                base64.b64decode(parts[1], validate=True)
            except (binascii.Error, ValueError):
                raise BadRequest("malformed Upload-Metadata") from None


def policy_from(settings: Settings) -> UploadPolicy:
    """The caps from configuration (provisional until ST-025 / R-05, K12)."""
    return UploadPolicy(
        max_bytes=settings.upload_max_bytes,
        max_duration_ms=settings.upload_max_duration_ms,
        max_frame_pixels=settings.upload_max_frame_pixels,
    )


def parse_upload_id(raw: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


class UploadService:
    def __init__(
        self,
        session: Session,
        store: ObjectStore,
        settings: Settings,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.session = session
        self.store = store
        self.settings = settings
        self.clock = clock
        self.uploads = UploadRepository(session)
        self.media = MediaRepository(session)
        # Bytes of replaced sessions, deleted only once the creation commits (C-16).
        self._after_commit: list[UploadSession] = []

    @property
    def policy(self) -> UploadPolicy:
        return policy_from(self.settings)

    @property
    def expiry(self) -> ExpiryPolicy:
        return ExpiryPolicy(
            idle=timedelta(seconds=self.settings.upload_expiry_seconds),
            max_age=timedelta(
                seconds=max(self.settings.upload_expiry_max_seconds,
                            self.settings.upload_expiry_seconds)
            ),
        )  # fmt: skip

    # ------------------------------------------------------------ creation
    def create(
        self,
        *,
        owner_id: uuid.UUID,
        raw_match_id: str,
        upload_length: str | None,
        upload_metadata: str | None,
        route: str,
        method: str,
    ) -> UploadSession:
        match_id = parse_upload_id(raw_match_id)
        if match_id is None or not matches.owns_match(self.session, match_id, owner_id):
            self._deny(owner_id, route, method)
            raise UploadNotFound("no such match for this owner")
        # Values beyond 20 digits stay 413 payload_too_large (not a plausible size, SEC-R2-02).
        length = parse_upload_length(upload_length, 10**HEADER_MAX_DIGITS)
        now = self.clock()
        # The existing-session check runs before the size cap: a 413 records a refusal on the
        # match, which must never touch a match with its video or a live upload (PE-R1-01).
        self._replace_expired_or_refuse(match_id, now)
        if self.policy.check_declared_length(length) is not None:
            self._reject(match_id, owner_id, Rejection.TOO_LARGE, now)  # T-UV-2, NFR-053
            self.session.commit()
            self._delete_replaced_bytes()
            raise VideoTooLarge("declared length above the cap")
        # §6.3 check 4: syntax and values (``last_modified`` range, ``head_sha256`` hex) are a
        # 400 before quota and rate (PE-R3-01).
        validate_metadata(upload_metadata)
        file = UploadFile.from_metadata(upload_metadata)
        # The quota is read under the owner's lock, held to the commit, so parallel creations
        # see each other's sessions (C-02, PE-R3R-01; READ COMMITTED reads after the lock).
        self.uploads.lock_owner(owner_id)
        self._check_quota(owner_id, length, now)
        # SEC-S3-TM-05: the account row FOR SHARE, held to the commit, before anything is written
        if not players.lock_live_account(self.session, owner_id):
            self.session.rollback()
            raise Unauthenticated("the account was deleted")
        retry_at = RateLimiter(self.session, clock=self.clock).hit(
            f"upload:create:{owner_id}",
            limit=self.settings.upload_create_limit_per_hour,
            window=timedelta(hours=1),
        )
        if retry_at is not None:
            self.session.rollback()
            raise RateLimited(retry_at, now)
        object_key = ObjectKeyPolicy().original_key()
        s3_upload_id = self.store.create_multipart(object_key, content_type=ORIGINAL_CONTENT_TYPE)
        upload = UploadSession.start(
            owner_id=owner_id,
            match_id=match_id,
            length=length,
            max_length=self.settings.upload_max_bytes,
            object_key=object_key,
            s3_upload_id=s3_upload_id,
            now=now,
            expiry=self.expiry,
            file=file,
        )
        matches.clear_rejection(self.session, match_id, owner_id)  # before add: no autoflush
        self.uploads.add(upload)
        try:
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            self.store.abort_multipart(object_key, s3_upload_id)
            # Two creations raced past exists_for_match; the unique constraint on
            # upload_sessions.match_id picked the winner. The loser is a 409 (R1-03).
            if isinstance(exc, IntegrityError) and isinstance(exc.orig, UniqueViolation):
                raise UploadExists("the match already has an upload") from None
            raise
        self._delete_replaced_bytes()
        log.info("upload created", extra={"event": "upload.created", "upload_id": str(upload.id)})
        SLI.upload_event(UploadEvent.CREATED)
        return upload

    def _replace_expired_or_refuse(self, match_id: uuid.UUID, now: datetime) -> None:
        """§6.3 check 2: an unexpired session is a 409; an expired one is replaced."""
        if not self.uploads.exists_for_match(match_id):
            return  # a racing creation is still caught by the unique constraint (R1-03)
        existing = self.uploads.for_match(match_id, for_update=True)
        if existing is None:
            return
        if not existing.is_expired(now):
            raise UploadExists("the match already has an upload")
        self.uploads.delete(existing)  # its bytes go after the commit (C-16, PE-R2-S1-05)
        self._after_commit.append(existing)
        log.info("upload replaced", extra={"event": "upload.replaced",
                                           "upload_id": str(existing.id)})  # fmt: skip

    def _reject(
        self, match_id: uuid.UUID, owner_id: uuid.UUID, rejection: Rejection, now: datetime
    ) -> None:
        matches.refuse_upload(self.session, match_id, owner_id, rejection.value, now)
        SLI.upload_event(UploadEvent.REJECTED, reason=rejection.value)
        log.info("upload refused", extra={"event": "upload.rejected", "reason": rejection.value})

    def _delete_replaced_bytes(self) -> None:
        for upload in self._after_commit:
            self._delete_bytes(upload)
        self._after_commit.clear()

    def _discard(self, upload: UploadSession) -> None:
        """Delete a session and its stored bytes (best effort for the bytes; ST-038 sweeps)."""
        self.uploads.delete(upload)
        self._delete_bytes(upload)

    def _delete_bytes(self, upload: UploadSession) -> None:
        try:
            self.store.abort_multipart(upload.object_key, upload.s3_upload_id)
            for staged in upload.staged:
                self.store.delete(staged.key)
        except ClientError:
            log.warning("upload bytes left", extra={"event": "upload.bytes_left"})

    def _refuse_content(self, upload: UploadSession) -> None:
        """T-UV-1: not MP4/MOV content. The session goes, nothing is kept, no job (NFR-060)."""
        self._discard(upload)
        self._reject(upload.match_id, upload.owner_id, Rejection.NOT_A_VIDEO, self.clock())
        self.session.commit()
        raise NotAVideoUpload("first bytes are not an MP4/QuickTime atom")

    def _check_quota(self, owner_id: uuid.UUID, length: int, now: datetime) -> None:
        count, declared = self.uploads.open_for_owner(owner_id, now)
        if (
            count >= self.settings.upload_max_open_sessions
            or declared + length > self.settings.upload_max_open_bytes
        ):
            raise UploadQuotaExceeded("too many unfinished uploads")

    # ------------------------------------------------------------ HEAD / PATCH
    def load_owned(
        self, *, owner_id: uuid.UUID, raw_upload_id: str, route: str, method: str
    ) -> UploadSession:
        """Ownership first (404 for others, T-UV-8), then expiry (410 for the owner, §6.4)."""
        upload_id = parse_upload_id(raw_upload_id)
        upload = None if upload_id is None else self.uploads.get_owned(upload_id, owner_id)
        if upload is not None and not matches.owns_match(self.session, upload.match_id, owner_id):
            upload = None  # the match was deleted: its uploads are gone too (ST-050)
        if upload is None:
            self._deny(owner_id, route, method)
            raise UploadNotFound("no such upload for this owner")
        now = self.clock()
        if upload.is_expired(now):
            newly = upload.status is UploadStatus.RECEIVING
            try:
                upload.ensure_open(now=now)
            except UploadExpired:
                if newly:  # persist "expired" and the dropped file name, then refuse
                    self.session.commit()
                    SLI.upload_event(UploadEvent.EXPIRED)
                raise
        return upload

    def patch_target(
        self, *, owner_id: uuid.UUID, raw_upload_id: str, route: str, method: str
    ) -> PatchTarget:
        """``load_owned`` for PATCH, then end the read transaction (R1-05)."""
        upload = self.load_owned(
            owner_id=owner_id, raw_upload_id=raw_upload_id, route=route, method=method
        )
        target = PatchTarget(
            id=upload.id,
            offset=upload.offset,
            length=upload.length,
            complete=upload.status == UploadStatus.COMPLETE or upload.is_complete,
            expires_at=upload.expires_at,
        )
        self.session.rollback()  # returns the connection to the pool before the body streams
        return target

    def write_chunk(
        self, upload_id: uuid.UUID, offset: int, data: bytes, checksum: UploadChecksum | None = None
    ) -> UploadSession:
        """Steps 3-6 of ADR 0011, with the checksum (460) and same-file checks of §6.5 before
        anything is stored. Returns the session after the chunk (offset and expiry)."""
        try:
            if checksum is not None:
                checksum.verify(data)  # T-UV-5: a damaged chunk is not kept
            upload = self._lock(upload_id)
            upload.ensure_open(now=self.clock())
            if offset == 0 and data:
                # Same-file check first: resuming with another file must not destroy the
                # session (T-UV-6, IT-01-06); then content (T-UV-1).
                upload.verify_head(data)
                if UploadPolicy.sniff(data, length=upload.length) is not None:
                    self._refuse_content(upload)  # commits the refusal, raises 415
            plan = upload.plan_chunk(offset, len(data), self.settings.upload_part_min_bytes)
            if plan.is_noop:  # empty PATCH: nothing to write, the offset stays (R1-01)
                self.session.rollback()
                return upload
            already_complete = False
            if plan.as_part:
                part_number = plan.part_number or len(upload.parts) + 1
                body = b"".join(self.store.get_bytes(s.key) for s in plan.staged) + data
                try:
                    etag = self.store.upload_part(
                        upload.object_key, upload.s3_upload_id, part_number, body
                    )
                except ClientError as exc:
                    # A retry after CompleteMultipartUpload succeeded but the commit did not.
                    if not (
                        plan.completes and is_missing_upload(exc) and self._object_complete(upload)
                    ):
                        raise
                    already_complete, etag = True, "completed"
                upload.commit_part(plan, etag=etag)
            else:
                key = ObjectKeyPolicy.staging_key(upload.id, offset)
                self.store.put_bytes(key, data)
                upload.commit_staged(plan, staging_key=key)
            upload.touch(now=self.clock(), expiry=self.expiry)
            if plan.completes:
                self._complete(upload, already_complete)
            self.session.commit()
        except BaseException:
            self.session.rollback()
            raise
        for staged in plan.staged:  # best effort; the Sprint 1 sweeper removes leftovers
            try:
                self.store.delete(staged.key)
            except ClientError:
                log.warning("staging delete failed", extra={"event": "upload.staging_left"})
        if plan.completes:
            SLI.upload_event(UploadEvent.COMPLETED)
        return upload

    # ------------------------------------------------------------ helpers
    def _lock(self, upload_id: uuid.UUID) -> UploadSession:
        try:
            upload = self.uploads.lock_nowait(upload_id)
        except OperationalError as exc:
            if isinstance(exc.orig, LockNotAvailable):
                raise OffsetMismatch("another PATCH holds this upload") from None
            raise
        if upload is None:
            raise UploadNotFound("upload vanished")
        return upload

    def _object_complete(self, upload: UploadSession) -> bool:
        return self.store.size_of(upload.object_key) == upload.length

    def _complete(self, upload: UploadSession, already_complete: bool) -> None:
        if not already_complete:
            self.store.complete_multipart(
                upload.object_key, upload.s3_upload_id, [(p.number, p.etag) for p in upload.parts]
            )
        asset_id = self.media.add_asset(
            owner_id=upload.owner_id,
            match_id=upload.match_id,
            object_key=upload.object_key,
            size_bytes=upload.length,
        )
        upload.mark_complete(asset_id)
        matches.mark_uploaded(self.session, upload.match_id, upload.owner_id, asset_id)
        # enqueue_again: a new upload after a refused one must be probed again (ST-018).
        JobQueue(self.session).enqueue_again(
            JobKey(match_id=upload.match_id, pipeline_version=self.settings.pipeline_version,
                   stage=PROBE_STAGE)
        )  # fmt: skip
        log.info("upload complete", extra={"event": "upload.complete", "upload_id": str(upload.id)})

    def _deny(self, owner_id: uuid.UUID, route: str, method: str) -> None:
        security_log.info(
            "access denied",
            extra={"event": "authz.denied", "account_id": str(owner_id), "route": route,
                   "method": method},
        )  # fmt: skip
