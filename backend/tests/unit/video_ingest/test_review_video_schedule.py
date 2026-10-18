"""Review video deletion date rules (ST-069; FR-008; ADR 0006; api-sprint-04 §5; T4-RT-4).

Negative cases first: "until I delete" and "not analysed yet" have no date and are never due;
one microsecond before the date is not due. Then: date = analysed time + the owner's days, due
from that instant on; the date always follows the current setting (a longer one moves it)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from racket.video_ingest.domain.retention import ReviewVideoSchedule

pytestmark = [pytest.mark.unit]

ANALYSED = datetime(2026, 10, 1, 9, 30, tzinfo=UTC)
LATER = ANALYSED + timedelta(days=4000)


def test_until_i_delete_has_no_date_and_is_never_due() -> None:
    schedule = ReviewVideoSchedule(None)
    assert schedule.delete_at(ANALYSED) is None
    assert schedule.is_due(ANALYSED, LATER) is False


@pytest.mark.parametrize("days", [30, 90, 365, None])
def test_a_video_not_analysed_yet_has_no_date_and_is_never_due(days: int | None) -> None:
    assert ReviewVideoSchedule(days).delete_at(None) is None
    assert ReviewVideoSchedule(days).is_due(None, LATER) is False


def test_one_microsecond_before_the_date_is_not_due() -> None:
    date = ANALYSED + timedelta(days=30)
    assert ReviewVideoSchedule(30).is_due(ANALYSED, date - timedelta(microseconds=1)) is False


@pytest.mark.parametrize("days", [0, -1, True])
def test_days_are_whole_days_of_at_least_one(days: int) -> None:
    with pytest.raises(ValueError, match="whole days"):
        ReviewVideoSchedule(days)


def test_a_naive_time_is_refused() -> None:
    with pytest.raises(ValueError, match="time zone"):
        ReviewVideoSchedule(30).delete_at(datetime(2026, 10, 1, 9, 30))


@pytest.mark.parametrize("days", [30, 90, 365])
def test_the_date_is_the_analysed_time_plus_the_days_and_due_from_then(days: int) -> None:
    schedule = ReviewVideoSchedule(days)
    date = ANALYSED + timedelta(days=days)
    assert schedule.delete_at(ANALYSED) == date
    assert schedule.is_due(ANALYSED, date) is True
    assert schedule.is_due(ANALYSED, date + timedelta(days=1)) is True


def test_the_date_follows_the_current_setting() -> None:
    now = ANALYSED + timedelta(days=31)
    assert ReviewVideoSchedule(30).is_due(ANALYSED, now) is True
    assert ReviewVideoSchedule(365).is_due(ANALYSED, now) is False
    assert ReviewVideoSchedule(365).delete_at(ANALYSED) == ANALYSED + timedelta(days=365)
