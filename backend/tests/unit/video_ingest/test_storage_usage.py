"""``StorageQuota.usage``: the read model behind ``GET /me/quota`` ``storage`` (QA-VERIFY04R3-04;
FR-160; api-sprint-04 §7). Used is counted as check 4a counts it: stored + declared bytes of open
uploads, so the page and a refusal never disagree. Negative cases first."""

from __future__ import annotations

import pytest

from racket.video_ingest.domain import StorageQuota, StorageUsage

pytestmark = [pytest.mark.unit]

QUOTA = StorageQuota(limit_bytes=1000)


@pytest.mark.parametrize(("stored", "reserved"), [(-1, 0), (0, -1)])
def test_impossible_byte_counts_are_refused_loudly(stored: int, reserved: int) -> None:
    with pytest.raises(ValueError, match="impossible byte counts"):
        QUOTA.usage(stored_bytes=stored, reserved_bytes=reserved)


@pytest.mark.parametrize(
    ("stored", "reserved", "used"), [(0, 0, 0), (600, 300, 900), (1500, 0, 1500)]
)
def test_used_is_stored_plus_open_uploads_even_over_a_lowered_limit(
    stored: int, reserved: int, used: int
) -> None:
    usage = QUOTA.usage(stored_bytes=stored, reserved_bytes=reserved)
    assert usage == StorageUsage(used_bytes=used, limit_bytes=1000)


def test_usage_agrees_with_the_refusal_check() -> None:
    refusal = QUOTA.refusal(stored_bytes=600, reserved_bytes=300, requested_bytes=101)
    usage = QUOTA.usage(stored_bytes=600, reserved_bytes=300)
    assert refusal is not None
    assert (usage.used_bytes, usage.limit_bytes) == (refusal.used_bytes, refusal.limit_bytes)
