"""Rolling-window rate limits in Postgres (NFR-023 partial; api-sprint-01 §2.4, §6.3).

One row per counted hit, ``rate_limit_events(key, at)``. A key may be hit ``limit`` times in
any ``window``; over the limit, ``hit`` returns the time when the oldest counted hit leaves the
window (``retry_at``), and the refused hit is not counted. Hits on one key are serialised with
a transaction-scoped advisory lock, so concurrent requests cannot both take the last slot.
Keys never hold personal data in clear: callers pass an ``email_key``, an IP or an account ID.
The caller owns the transaction and commits it (even when the guarded action then fails).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.orm import Session

from racket.platform.db import metadata
from racket.platform.errors import AppError

rate_limit_events = sa.Table(
    "rate_limit_events",
    metadata,
    sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
    sa.Column("key", sa.String(128), nullable=False),
    sa.Column("at", sa.DateTime(timezone=True), nullable=False),
)


class RateLimited(AppError):
    """429 with ``retry_at`` and ``Retry-After`` (api-sprint-01 §1.1, §2.4)."""

    status, code = 429, "rate_limited"

    def __init__(self, retry_at: datetime, now: datetime) -> None:
        super().__init__("rate limited")
        utc = retry_at.astimezone(UTC)  # the DB session's zone may not be UTC (C-08)
        self.retry_at: str | None = utc.isoformat(timespec="seconds").replace("+00:00", "Z")
        wait = max(1, int((retry_at - now).total_seconds() + 0.999))
        self.response_headers = {"Retry-After": str(wait)}


def _utcnow() -> datetime:
    return datetime.now(UTC)


class RateLimiter:
    def __init__(self, session: Session, clock: Callable[[], datetime] = _utcnow) -> None:
        self.session = session
        self.clock = clock

    def hit(self, key: str, *, limit: int, window: timedelta) -> datetime | None:
        """Count one hit on ``key``. ``None`` when allowed, else the ``retry_at`` time."""
        now = self.clock()
        self.session.execute(
            sa.text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"), {"k": key}
        )
        self.session.execute(
            sa.delete(rate_limit_events).where(
                rate_limit_events.c.key == key, rate_limit_events.c.at <= now - window
            )
        )
        count, oldest = self.session.execute(
            sa.select(sa.func.count(), sa.func.min(rate_limit_events.c.at)).where(
                rate_limit_events.c.key == key
            )
        ).one()
        if count >= limit:
            retry_at: datetime = oldest + window
            return retry_at
        self.session.execute(sa.insert(rate_limit_events).values(key=key, at=now))
        return None
