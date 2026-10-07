"""``UploadExpiryPolicy`` for the purge (ST-038; FR-024; NFR-066 d; sprint-03 §5): an upload
idle 24 h (config) is abandoned; a completed upload never is. Negative cases first."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from racket.video_ingest.domain import ExpiryPolicy, UploadStatus

pytestmark = [pytest.mark.unit]

POLICY = ExpiryPolicy(idle=timedelta(hours=24), max_age=timedelta(hours=72))
NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(hours=10)


def test_idle_for_23h59_is_not_abandoned() -> None:
    idle = NOW - timedelta(hours=23, minutes=59)
    assert not POLICY.is_abandoned(UploadStatus.RECEIVING, idle, LATER, now=NOW)


def test_a_completed_upload_is_never_abandoned() -> None:
    long_ago = NOW - timedelta(days=30)
    assert not POLICY.is_abandoned(UploadStatus.COMPLETE, long_ago, long_ago, now=NOW)


def test_idle_for_24h_is_abandoned() -> None:
    assert POLICY.is_abandoned(UploadStatus.RECEIVING, NOW - timedelta(hours=24), LATER, now=NOW)


def test_past_its_expiry_time_is_abandoned_even_when_recently_active() -> None:
    assert POLICY.is_abandoned(UploadStatus.RECEIVING, NOW, NOW - timedelta(seconds=1), now=NOW)


def test_an_upload_already_marked_expired_is_abandoned() -> None:
    assert POLICY.is_abandoned(UploadStatus.EXPIRED, NOW, LATER, now=NOW)
