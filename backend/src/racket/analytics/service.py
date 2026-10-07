"""Analytics application service (ST-046, ST-047; analytics-snapshots.md §4; ADR 0040).

* ``on_sheet_changed``: the after-commit consumer of ``ScoreSheetChanged``. Its own session and
  transaction; the snapshot is written under the match row ``FOR SHARE`` lock that the
  tombstone-aware port ``lock_live_sheet`` takes (invariant S8).
* ``StatsReader.current``: read repair. Every read compares the stored ``sheet_version`` with
  the live one and recomputes on the spot when behind, so a read is never stale (S4) and a
  lost or failed event is retried by the next read.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from racket.analytics.repository import SnapshotRepository
from racket.analytics.snapshot import MetricSnapshot, SnapshotKey
from racket.matches import public as matches
from racket.matches.events import ScoreSheetChanged
from racket.sports.pickleball import metrics

log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class CurrentStats:
    snapshot: MetricSnapshot
    sheet: dict[str, Any]
    sheet_version: int


def current(
    session: Session, match_id: uuid.UUID, *, trigger: str, clock: Callable[[], datetime] = _now
) -> CurrentStats | None:
    """The snapshot of the live sheet, recomputed and stored when missing or behind. ``None``
    when the match is gone. Commits the caller's session (the lock ends with it)."""
    live = matches.lock_live_sheet(session, match_id)
    if live is None:
        session.rollback()
        log.debug(
            "snapshot skipped",
            extra={"event": "analytics.snapshot_skipped", "match_id": str(match_id),
                   "reason": "deleted"},
        )  # fmt: skip
        return None
    dictionary = metrics.load_dictionary()
    repo = SnapshotRepository(session)
    key = SnapshotKey(match_id, dictionary.version, str(live.sheet["rules_version"]))
    snapshot = repo.get(key)
    if snapshot is None or snapshot.is_behind(live.version):
        started = time.perf_counter()
        snapshot = MetricSnapshot.compute(
            match_id=match_id,
            owner_id=live.owner_id,
            sheet=live.sheet,
            sheet_version=live.version,
            dictionary=dictionary,
            now=clock(),
        )
        repo.upsert(snapshot)
        log.debug(
            "snapshot computed",
            extra={
                "event": "analytics.snapshot_computed",
                "match_id": str(match_id),
                "sheet_version": live.version,
                "metric_def_version": dictionary.version,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                "trigger": trigger,
            },
        )
    session.commit()
    return CurrentStats(snapshot, live.sheet, live.version)


def on_sheet_changed(event: ScoreSheetChanged, bind: Any) -> None:
    """The consumer (§4.2). Any failure is logged here and swallowed by the dispatcher."""
    with Session(bind=bind) as session:
        try:
            current(session, event.match_id, trigger="event")
        except Exception as exc:
            session.rollback()
            log.error(
                "snapshot failed",
                extra={
                    "event": "analytics.snapshot_failed",
                    "match_id": str(event.match_id),
                    "sheet_version": event.sheet_version,
                    "error": type(exc).__name__,
                },
            )
            raise


def replay_latest_event(conn: Any, match_id: uuid.UUID | str) -> None:
    """Test seam (§4.3): deliver the match's latest ``ScoreSheetChanged`` again, inside the
    caller's connection and transaction."""
    match_uuid = match_id if isinstance(match_id, uuid.UUID) else uuid.UUID(str(match_id))
    with Session(bind=conn) as session:
        current(session, match_uuid, trigger="event")
