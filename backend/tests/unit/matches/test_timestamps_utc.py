"""C-08 (PE-R3R-03): API timestamps are UTC ``Z`` strings whatever the database session's
``TimeZone`` is. Postgres returns ``timestamptz`` in the session's zone; a non-UTC session
used to give ``+02:00`` strings. No I/O: aware datetimes in another zone stand in."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from racket.matches.service import _rfc3339
from racket.platform.ratelimit import RateLimited

pytestmark = pytest.mark.unit

BERLIN_SUMMER = timezone(timedelta(hours=2))
AT = datetime(2026, 10, 5, 14, 30, 0, 123000, tzinfo=BERLIN_SUMMER)


def test_a_match_timestamp_from_a_non_utc_session_is_written_in_utc() -> None:
    assert _rfc3339(AT) == "2026-10-05T12:30:00.123Z"


def test_a_utc_timestamp_is_unchanged() -> None:
    assert _rfc3339(AT.astimezone(UTC)) == "2026-10-05T12:30:00.123Z"


def test_retry_at_from_a_non_utc_session_is_written_in_utc() -> None:
    assert RateLimited(AT, AT).retry_at == "2026-10-05T12:30:00Z"
