"""``CreationUsage``: the read model behind ``GET /me/quota`` ``match_creations``
(QA-VERIFY04R3-04; FR-160; api-sprint-04 §7; Q-01 "when the player can continue").
``next_slot_at`` is set only when the account is at its limit: when the oldest counted creation
leaves the window, which is the ``retry_at`` the limiter would answer. Negative cases first."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from racket.matches.domain import CreationUsage

pytestmark = [pytest.mark.unit]

HOUR = timedelta(hours=1)
T0 = datetime(2026, 10, 29, 9, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("used", "oldest"), [(-1, None), (1, None), (0, T0)], ids=["negative", "no-oldest", "stray"]
)
def test_impossible_counts_are_refused_loudly(used: int, oldest: datetime | None) -> None:
    with pytest.raises(ValueError, match="impossible creation count"):
        CreationUsage.in_window(limit=10, window=HOUR, used=used, oldest=oldest)


def test_a_limit_below_one_is_not_a_limit() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        CreationUsage.in_window(limit=0, window=HOUR, used=0, oldest=None)


def test_at_the_limit_the_next_slot_is_when_the_oldest_creation_leaves_the_window() -> None:
    usage = CreationUsage.in_window(limit=10, window=HOUR, used=10, oldest=T0)
    assert usage == CreationUsage(limit=10, window_s=3600, used=10, next_slot_at=T0 + HOUR)


@pytest.mark.parametrize(("used", "oldest"), [(0, None), (3, T0), (9, T0)])
def test_under_the_limit_there_is_no_wait(used: int, oldest: datetime | None) -> None:
    usage = CreationUsage.in_window(limit=10, window=HOUR, used=used, oldest=oldest)
    assert usage == CreationUsage(limit=10, window_s=3600, used=used, next_slot_at=None)
