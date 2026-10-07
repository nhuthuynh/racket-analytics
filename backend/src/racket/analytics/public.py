"""Analytics' published port for the purge job (deletion-and-purge.md §4.2, §5)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from racket.analytics.repository import SnapshotRepository


def purge_match(session: Session, match_id: uuid.UUID) -> int:
    """Delete every snapshot of the match (in the caller's transaction). Rows deleted."""
    return SnapshotRepository(session).delete_for_match(match_id)


def snapshot_match_ids(
    session: Session, after: uuid.UUID | None, limit: int
) -> Sequence[uuid.UUID]:
    """Match ids that have snapshot rows, ascending, one page (orphan sweep, SEC-S3-TM-02)."""
    return SnapshotRepository(session).match_ids(after, limit)
