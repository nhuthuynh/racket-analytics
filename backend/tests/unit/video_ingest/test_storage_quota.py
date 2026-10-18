"""``StorageQuota`` arithmetic (ST-072a; FR-160; api-sprint-04 §7 check 4a): used = stored bytes
+ declared bytes of open uploads; an upload is refused when used + requested > limit.
Negative cases first."""

from __future__ import annotations

import pytest

from racket.video_ingest.domain import QuotaUsage, StorageQuota

pytestmark = [pytest.mark.unit]

QUOTA = StorageQuota(limit_bytes=1000)


def test_one_byte_over_the_limit_is_refused_with_the_usage() -> None:
    refusal = QUOTA.refusal(stored_bytes=600, reserved_bytes=300, requested_bytes=101)
    assert refusal == QuotaUsage(used_bytes=900, limit_bytes=1000, requested_bytes=101)


@pytest.mark.parametrize(("stored", "reserved"), [(0, 1000), (1500, 0)])
def test_open_uploads_count_and_an_account_over_a_lowered_limit_cannot_add_a_byte(
    stored: int, reserved: int
) -> None:
    refusal = QUOTA.refusal(stored_bytes=stored, reserved_bytes=reserved, requested_bytes=1)
    assert refusal == QuotaUsage(used_bytes=stored + reserved, limit_bytes=1000, requested_bytes=1)


@pytest.mark.parametrize("counts", [(-1, 0, 1), (0, -1, 1), (0, 0, 0), (0, 0, -5)])
def test_impossible_byte_counts_are_refused_loudly(counts: tuple[int, int, int]) -> None:
    stored, reserved, requested = counts
    with pytest.raises(ValueError, match="impossible byte counts"):
        QUOTA.refusal(stored_bytes=stored, reserved_bytes=reserved, requested_bytes=requested)


def test_a_negative_limit_is_not_a_quota() -> None:
    with pytest.raises(ValueError, match="never negative"):
        StorageQuota(limit_bytes=-1)


@pytest.mark.parametrize(("stored", "reserved", "requested"), [(600, 300, 100), (0, 0, 1000)])
def test_an_upload_that_reaches_the_limit_exactly_fits(
    stored: int, reserved: int, requested: int
) -> None:
    assert (
        QUOTA.refusal(stored_bytes=stored, reserved_bytes=reserved, requested_bytes=requested)
        is None
    )
