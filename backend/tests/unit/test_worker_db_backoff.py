"""R1-06: the worker's back-off after database errors grows and is capped."""

from __future__ import annotations

from racket.worker.__main__ import DB_BACKOFF_MAX_S, db_backoff


def test_backoff_never_exceeds_the_cap() -> None:
    assert db_backoff(50, 1.0) == DB_BACKOFF_MAX_S


def test_backoff_starts_at_the_poll_interval_and_doubles() -> None:
    assert [db_backoff(n, 0.5) for n in (1, 2, 3)] == [0.5, 1.0, 2.0]
