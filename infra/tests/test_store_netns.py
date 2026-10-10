"""CI-OBJSTORE-STALL: the arithmetic of the store's receive buffer (``store_netns``).

Negative cases first: the runner kernel's 128 KiB default holds two loopback segments."""

from __future__ import annotations

import pytest
from store_netns import LOOPBACK_MSS, MIN_SEGMENTS, default_rmem, loopback_segments

pytestmark = pytest.mark.unit


def test_the_runner_default_holds_only_two_loopback_segments() -> None:
    assert loopback_segments(131_072) == 2
    assert loopback_segments(131_072) < MIN_SEGMENTS


def test_a_buffer_one_byte_short_of_the_budget_is_refused() -> None:
    assert loopback_segments(MIN_SEGMENTS * LOOPBACK_MSS - 1) == MIN_SEGMENTS - 1


@pytest.mark.parametrize("value", ["", "4096 131072", "4096 lots 33554432", "4096 1048576 4096"])
def test_a_malformed_or_inconsistent_tcp_rmem_is_refused(value: str) -> None:
    with pytest.raises(ValueError, match="tcp_rmem"):
        default_rmem(value)


def test_the_default_is_the_middle_of_min_default_max() -> None:
    assert default_rmem("4096\t1048576\t33554432\n") == 1_048_576
    assert default_rmem("4096 1048576 33554432") == 1_048_576


def test_one_mebibyte_holds_sixteen_loopback_segments() -> None:
    assert LOOPBACK_MSS == 65_483
    assert loopback_segments(1_048_576) == MIN_SEGMENTS == 16
