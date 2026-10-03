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

from botocore.exceptions import ClientError
from psycopg.errors import LockNotAvailable
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from racket.analysis_jobs.domain import JobKey
from racket.analysis_jobs.queue import JobQueue
from racket.matches import public as matches
from racket.platform.errors import BadRequest, Conflict, NotFound, PayloadTooLarge
from racket.platform.logs import SECURITY_LOGGER
from racket.platform.settings import Settings
from racket.platform.storage import ObjectStore, is_missing_upload
from racket.video_ingest.domain import (
    ObjectKeyPolicy,
    OffsetMismatch,
    UploadSession,
)
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


def parse_upload_length(raw: str | None, maximum: int) -> int:
    if raw is None or not raw.isdigit():
        raise BadRequest("Upload-Length must be a decimal integer")
    length = int(raw)
    if length < 1:
        raise BadRequest("Upload-Length must be at least 1")
    if length > maximum:
        raise PayloadTooLarge("Upload-Length above the limit")
    return length


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


def parse_upload_id(raw: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


class UploadService:
    def __init__(self, session: Session, store: ObjectStore, settings: Settings) -> None:
        self.session = session
        self.store = store
        self.settings = settings
        self.uploads = UploadRepository(session)
        self.media = MediaRepository(session)

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
        length = parse_upload_length(upload_length, self.settings.upload_max_bytes)
        validate_metadata(upload_metadata)
        if self.uploads.exists_for_match(match_id):
            raise UploadExists("the match already has an upload")
        object_key = ObjectKeyPolicy().original_key()
        s3_upload_id = self.store.create_multipart(object_key)
        upload = UploadSession.start(
            owner_id=owner_id,
            match_id=match_id,
            length=length,
            max_length=self.settings.upload_max_bytes,
            object_key=object_key,
            s3_upload_id=s3_upload_id,
        )
        self.uploads.add(upload)
        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            self.store.abort_multipart(object_key, s3_upload_id)
            raise
        log.info("upload created", extra={"event": "upload.created", "upload_id": str(upload.id)})
        return upload

    # ------------------------------------------------------------ HEAD / PATCH
    def load_owned(
        self, *, owner_id: uuid.UUID, raw_upload_id: str, route: str, method: str
    ) -> UploadSession:
        upload_id = parse_upload_id(raw_upload_id)
        upload = None if upload_id is None else self.uploads.get_owned(upload_id, owner_id)
        if upload is None:
            self._deny(owner_id, route, method)
            raise UploadNotFound("no such upload for this owner")
        return upload

    def write_chunk(self, upload_id: uuid.UUID, offset: int, data: bytes) -> int:
        """Steps 3-6 of ADR 0011. Returns the new offset."""
        try:
            upload = self._lock(upload_id)
            plan = upload.plan_chunk(offset, len(data), self.settings.upload_part_min_bytes)
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
        return upload.offset

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
        JobQueue(self.session).enqueue(
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
