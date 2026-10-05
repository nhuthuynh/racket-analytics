"""Capture & Media persistence (ST-008, ST-009). Only this context reads these tables."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from racket.platform.db import DataclassListType, StrEnumType, mapper_registry, metadata
from racket.video_ingest.domain import MediaFacts, Part, StagedChunk, UploadSession, UploadStatus

upload_sessions = sa.Table(
    "upload_sessions",
    metadata,
    sa.Column("id", sa.Uuid(), primary_key=True),
    sa.Column("owner_id", sa.Uuid(), nullable=False),
    sa.Column("match_id", sa.Uuid(), nullable=False, unique=True),
    sa.Column("length", sa.BigInteger(), nullable=False),
    sa.Column("offset", sa.BigInteger(), nullable=False),
    sa.Column("object_key", sa.String(128), nullable=False),
    sa.Column("s3_upload_id", sa.String(1024), nullable=False),
    sa.Column("parts", DataclassListType(Part), nullable=False),
    sa.Column("staged", DataclassListType(StagedChunk), nullable=False),
    sa.Column("status", StrEnumType(UploadStatus), nullable=False),
    sa.Column("media_asset_id", sa.Uuid(), nullable=True),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("file_name", sa.String(255), nullable=True),
    sa.Column("file_last_modified_ms", sa.BigInteger(), nullable=True),
    sa.Column("head_sha256", sa.String(64), nullable=True),
)

media_assets = sa.Table(
    "media_assets",
    metadata,
    sa.Column("id", sa.Uuid(), primary_key=True),
    sa.Column("owner_id", sa.Uuid(), nullable=False),
    sa.Column("match_id", sa.Uuid(), nullable=False, unique=True),
    sa.Column("object_key", sa.String(128), nullable=False),
    sa.Column("size_bytes", sa.BigInteger(), nullable=False),
    sa.Column("probe_status", sa.String(32), nullable=False),  # pending | probed | failed
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
)

media_facts = sa.Table(
    "media_facts",
    metadata,
    sa.Column("media_asset_id", sa.Uuid(), sa.ForeignKey("media_assets.id"), primary_key=True),
    sa.Column("match_id", sa.Uuid(), nullable=False),
    sa.Column("container", sa.String(128)),
    sa.Column("video_codec", sa.String(64)),
    sa.Column("duration_ms", sa.BigInteger()),
    sa.Column("fps", sa.Numeric(10, 3)),
    sa.Column("vfr", sa.Boolean()),
    sa.Column("width", sa.Integer()),
    sa.Column("height", sa.Integer()),
    sa.Column("has_audio", sa.Boolean()),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
)

mapper_registry.map_imperatively(UploadSession, upload_sessions)

PROBE_PENDING, PROBE_DONE, PROBE_FAILED = "pending", "probed", "failed"


def _now() -> datetime:
    return datetime.now(UTC)


class UploadRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, upload: UploadSession) -> None:
        self.session.add(upload)

    def get_owned(self, upload_id: uuid.UUID, owner_id: uuid.UUID) -> UploadSession | None:
        query = sa.select(UploadSession).where(
            upload_sessions.c.id == upload_id, upload_sessions.c.owner_id == owner_id
        )
        return self.session.execute(query).scalar_one_or_none()

    def lock_nowait(self, upload_id: uuid.UUID) -> UploadSession | None:
        """Row lock for one PATCH at a time; raises if another PATCH holds it (ADR 0011 step 3)."""
        query = (
            sa.select(UploadSession)
            .where(upload_sessions.c.id == upload_id)
            .with_for_update(nowait=True)
            .execution_options(populate_existing=True)
        )
        return self.session.execute(query).scalar_one_or_none()

    def exists_for_match(self, match_id: uuid.UUID) -> bool:
        query = sa.select(sa.literal(1)).where(upload_sessions.c.match_id == match_id)
        return self.session.execute(query).first() is not None

    def for_match(self, match_id: uuid.UUID, *, for_update: bool = False) -> UploadSession | None:
        query = sa.select(UploadSession).where(upload_sessions.c.match_id == match_id)
        if for_update:
            query = query.with_for_update()
        return self.session.execute(query).scalar_one_or_none()

    def delete(self, upload: UploadSession) -> None:
        self.session.delete(upload)
        self.session.flush()

    def open_for_owner(self, owner_id: uuid.UUID, now: datetime) -> tuple[int, int]:
        """(count, declared bytes) of the owner's unexpired receiving sessions (T-UV-7)."""
        count, total = self.session.execute(
            sa.select(
                sa.func.count(), sa.func.coalesce(sa.func.sum(upload_sessions.c.length), 0)
            ).where(
                upload_sessions.c.owner_id == owner_id,
                upload_sessions.c.status == UploadStatus.RECEIVING,
                upload_sessions.c.expires_at > now,
            )
        ).one()
        return int(count), int(total)

    def state_for_match(self, match_id: uuid.UUID) -> UploadStatus | None:
        query = sa.select(upload_sessions.c.status).where(upload_sessions.c.match_id == match_id)
        status: UploadStatus | None = self.session.execute(query).scalar_one_or_none()
        return status


class MediaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_asset(
        self, *, owner_id: uuid.UUID, match_id: uuid.UUID, object_key: str, size_bytes: int
    ) -> uuid.UUID:
        asset_id = uuid.uuid4()
        now = _now()
        self.session.execute(
            sa.insert(media_assets).values(
                id=asset_id,
                owner_id=owner_id,
                match_id=match_id,
                object_key=object_key,
                size_bytes=size_bytes,
                probe_status=PROBE_PENDING,
                created_at=now,
                updated_at=now,
            )
        )
        return asset_id

    def asset_for_match(self, match_id: uuid.UUID) -> Any:
        return self.session.execute(
            sa.select(media_assets).where(media_assets.c.match_id == match_id)
        ).one_or_none()

    def set_probe_status(self, asset_id: uuid.UUID, status: str) -> None:
        self.session.execute(
            sa.update(media_assets)
            .where(media_assets.c.id == asset_id)
            .values(probe_status=status, updated_at=_now())
        )

    def write_partial_facts(self, asset_id: uuid.UUID, match_id: uuid.UUID, container: str) -> None:
        """Only the fault-injection path uses this (ADR 0012, APP_ENV=test)."""
        self.session.execute(
            sa.insert(media_facts).values(
                media_asset_id=asset_id, match_id=match_id, container=container, created_at=_now()
            )
        )
        self.session.flush()

    def save_facts(self, asset_id: uuid.UUID, match_id: uuid.UUID, facts: MediaFacts) -> None:
        """Idempotent: one set of facts per asset; a re-run replaces nothing it did not write."""
        stmt = (
            pg_insert(media_facts)
            .values(
                media_asset_id=asset_id,
                match_id=match_id,
                container=facts.container,
                video_codec=facts.video_codec,
                duration_ms=facts.duration_ms,
                fps=facts.fps,
                vfr=facts.vfr,
                width=facts.width,
                height=facts.height,
                has_audio=facts.has_audio,
                created_at=_now(),
            )
            .on_conflict_do_nothing(index_elements=["media_asset_id"])
        )
        self.session.execute(stmt)

    def facts_for_match(self, match_id: uuid.UUID) -> Any:
        return self.session.execute(
            sa.select(media_facts).where(media_facts.c.match_id == match_id)
        ).one_or_none()


def count_media_facts(session: Session, match_id: uuid.UUID | str) -> int:
    """Rows of MediaAsset facts for a match (ADR 0012 seam; "exactly one set of media facts")."""
    match_uuid = match_id if isinstance(match_id, uuid.UUID) else uuid.UUID(str(match_id))
    query = (
        sa.select(sa.func.count())
        .select_from(media_facts)
        .where(media_facts.c.match_id == match_uuid)
    )
    return int(session.execute(query).scalar_one())
