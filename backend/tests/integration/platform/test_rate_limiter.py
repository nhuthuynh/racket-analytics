"""Postgres rate limiter (NFR-023 partial; api-sprint-01 §2.4; T-ML-1/T-ML-8, T-UV-7).

Rolling window: a key may be hit ``limit`` times in any ``window``; the refusal carries the
time when the oldest counted hit leaves the window. Injected clock; real Postgres.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from racket.platform.ratelimit import RateLimiter

T0 = datetime(2026, 10, 5, 9, 0, tzinfo=UTC)
WINDOW = timedelta(minutes=10)


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        return self.now


def test_the_hit_over_the_limit_is_refused_with_a_retry_time(db_session: Any) -> None:
    clock = Clock()
    limiter = RateLimiter(db_session, clock=clock)
    results = []
    for _ in range(6):
        results.append(limiter.hit("link:email:abc", limit=5, window=WINDOW))
        clock.now += timedelta(seconds=30)
    assert results[:5] == [None] * 5
    assert results[5] == T0 + WINDOW  # the first hit leaves the window then


def test_hits_older_than_the_window_stop_counting(db_session: Any) -> None:
    clock = Clock()
    limiter = RateLimiter(db_session, clock=clock)
    for _ in range(5):
        assert limiter.hit("k", limit=5, window=WINDOW) is None
    assert limiter.hit("k", limit=5, window=WINDOW) is not None
    clock.now = T0 + WINDOW  # positive control: the same key works again once the window passed
    assert limiter.hit("k", limit=5, window=WINDOW) is None


def test_a_refused_hit_does_not_extend_the_wait(db_session: Any) -> None:
    clock = Clock()
    limiter = RateLimiter(db_session, clock=clock)
    assert limiter.hit("k", limit=1, window=WINDOW) is None
    clock.now += timedelta(minutes=5)
    assert limiter.hit("k", limit=1, window=WINDOW) == T0 + WINDOW
    assert limiter.hit("k", limit=1, window=WINDOW) == T0 + WINDOW


def test_keys_are_independent(db_session: Any) -> None:
    limiter = RateLimiter(db_session, clock=Clock())
    assert limiter.hit("a", limit=1, window=WINDOW) is None
    assert limiter.hit("a", limit=1, window=WINDOW) is not None
    assert limiter.hit("b", limit=1, window=WINDOW) is None
