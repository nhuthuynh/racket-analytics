"""Persistence of the Full Tag consent record and label session (ST-052b; api-sprint-03 §5).
Only Dataset & Labelling reads these tables (context map rule 1)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from racket.dataset.full_tag import ConsentRecord
from racket.platform.db import metadata

label_consents = sa.Table(
    "label_consents",
    metadata,
    sa.Column("match_id", sa.Uuid(), primary_key=True),
    sa.Column("reference", sa.String(64), nullable=False),
    sa.Column("recorded_by", sa.String(64), nullable=False),
    sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
)

label_sessions = sa.Table(
    "label_sessions",
    metadata,
    sa.Column("match_id", sa.Uuid(), primary_key=True),
    sa.Column("owner_id", sa.Uuid(), nullable=False),
    sa.Column("version", sa.Integer(), nullable=False),
    sa.Column("rallies", JSONB(), nullable=False),
    sa.Column("events", JSONB(), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
)


class LabelRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def consent(self, match_id: uuid.UUID) -> ConsentRecord | None:
        row = self.session.execute(
            sa.select(label_consents).where(label_consents.c.match_id == match_id)
        ).one_or_none()
        if row is None:
            return None
        return ConsentRecord(str(row.match_id), row.reference, row.recorded_by, row.recorded_at)

    def save_consent(self, record: ConsentRecord) -> None:
        insert = pg_insert(label_consents).values(
            match_id=uuid.UUID(record.match_id),
            reference=record.reference,
            recorded_by=record.recorded_by,
            recorded_at=record.recorded_at,
        )
        self.session.execute(
            insert.on_conflict_do_update(
                index_elements=["match_id"],
                set_={"reference": insert.excluded.reference,
                      "recorded_by": insert.excluded.recorded_by,
                      "recorded_at": insert.excluded.recorded_at},
            )
        )  # fmt: skip

    def load(self, match_id: uuid.UUID, *, lock: bool = False) -> Any:
        query = sa.select(label_sessions).where(label_sessions.c.match_id == match_id)
        return self.session.execute(query.with_for_update() if lock else query).one_or_none()

    def lock_or_create(self, match_id: uuid.UUID, owner_id: uuid.UUID, at: datetime) -> Any:
        """The session row under its lock; created empty first (commands on one match are
        serialised by this lock, api-sprint-03 §5.2)."""
        self.session.execute(
            pg_insert(label_sessions)
            .values(match_id=match_id, owner_id=owner_id, version=0, rallies=[], events=[],
                    updated_at=at)
            .on_conflict_do_nothing(index_elements=["match_id"])
        )  # fmt: skip
        return self.load(match_id, lock=True)

    def save(
        self, match_id: uuid.UUID, version: int, rallies: list[Any], events: list[Any], at: datetime
    ) -> None:
        self.session.execute(
            sa.update(label_sessions)
            .where(label_sessions.c.match_id == match_id)
            .values(version=version, rallies=rallies, events=events, updated_at=at)
        )

    def delete_for_match(self, match_id: uuid.UUID) -> int:
        rows = 0
        for table in (label_sessions, label_consents):
            result = self.session.execute(sa.delete(table).where(table.c.match_id == match_id))
            rows += int(result.rowcount)  # type: ignore[attr-defined]
        return rows
