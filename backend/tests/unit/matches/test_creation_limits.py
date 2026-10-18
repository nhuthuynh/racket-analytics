"""``CreationLimits`` (ST-072a; FR-160; api-sprint-04 §7; SEC-4 T4-QT-1, T4-QT-2): one key per
account and one per client IP, account first (a fixed lock order). Negative cases first."""

from __future__ import annotations

import uuid

import pytest

from racket.matches.domain import CreationLimits, OwnerId

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(("per_account", "per_ip"), [(0, 60), (10, 0), (-1, -1)])
def test_a_limit_below_one_is_not_a_limit(per_account: int, per_ip: int) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        CreationLimits(per_account=per_account, per_ip=per_ip)


def test_the_account_key_comes_before_the_ip_key() -> None:
    owner = OwnerId(uuid.UUID(int=7))
    assert CreationLimits(per_account=10, per_ip=60).keys(owner, "203.0.113.7") == (
        (f"match:create:{owner.value}", 10),
        ("match:create:ip:203.0.113.7", 60),
    )
