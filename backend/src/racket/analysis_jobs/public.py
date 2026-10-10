"""Vision Analysis' published port for the purge job (deletion-and-purge.md §4.2, §5)."""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Session

from racket.analysis_jobs.queue import jobs


def purge_match(session: Session, match_id: uuid.UUID) -> int:
    """Delete every job row of the match (in the caller's transaction). Rows deleted."""
    result = session.execute(sa.delete(jobs).where(jobs.c.match_id == match_id))
    return int(result.rowcount)  # type: ignore[attr-defined]
