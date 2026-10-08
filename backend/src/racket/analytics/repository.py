"""Persistence of ``MetricSnapshot`` (ST-046; analytics-snapshots.md §2, §6). Only Analytics
reads ``metric_snapshots`` (context map rule 1)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from racket.analytics.snapshot import MetricSnapshot, SnapshotKey
from racket.platform.db import metadata

metric_snapshots = sa.Table(
    "metric_snapshots",
    metadata,
    sa.Column("match_id", sa.Uuid(), primary_key=True),
    sa.Column("metric_def_version", sa.String(16), primary_key=True),
    sa.Column("rules_version", sa.String(64), primary_key=True),
    sa.Column("owner_id", sa.Uuid(), nullable=False),
    sa.Column("sheet_version", sa.Integer(), nullable=False),
    sa.Column("stats", JSONB(), nullable=False),
    sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
)


class SnapshotRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, key: SnapshotKey) -> MetricSnapshot | None:
        row = self.session.execute(
            sa.select(metric_snapshots).where(
                metric_snapshots.c.match_id == key.match_id,
                metric_snapshots.c.metric_def_version == key.metric_def_version,
                metric_snapshots.c.rules_version == key.rules_version,
            )
        ).one_or_none()
        if row is None:
            return None
        return MetricSnapshot(key, row.owner_id, row.sheet_version, row.stats, row.computed_at)

    def upsert(self, snapshot: MetricSnapshot) -> bool:
        """Write only when newer (invariant S2): the same event twice, a late event and two
        racing consumers all leave one row with the newest version. True when written."""
        key = snapshot.key
        insert = pg_insert(metric_snapshots).values(
            match_id=key.match_id,
            metric_def_version=key.metric_def_version,
            rules_version=key.rules_version,
            owner_id=snapshot.owner_id,
            sheet_version=snapshot.sheet_version,
            stats=dict(snapshot.stats),
            computed_at=snapshot.computed_at,
        )
        result = self.session.execute(
            insert.on_conflict_do_update(
                index_elements=["match_id", "metric_def_version", "rules_version"],
                set_={
                    "owner_id": insert.excluded.owner_id,
                    "sheet_version": insert.excluded.sheet_version,
                    "stats": insert.excluded.stats,
                    "computed_at": insert.excluded.computed_at,
                },
                where=metric_snapshots.c.sheet_version < insert.excluded.sheet_version,
            )
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

    def delete_for_match(self, match_id: uuid.UUID) -> int:
        result = self.session.execute(
            sa.delete(metric_snapshots).where(metric_snapshots.c.match_id == match_id)
        )
        return int(result.rowcount)  # type: ignore[attr-defined]

    def match_ids(self, after: uuid.UUID | None, limit: int) -> Sequence[uuid.UUID]:
        query = (
            sa.select(metric_snapshots.c.match_id).distinct().order_by(metric_snapshots.c.match_id)
        )
        if after is not None:
            query = query.where(metric_snapshots.c.match_id > after)
        return list(self.session.execute(query.limit(limit)).scalars())
