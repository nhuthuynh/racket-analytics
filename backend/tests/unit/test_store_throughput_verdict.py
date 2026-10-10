"""CI-OBJSTORE-SLOW: the throughput verdict that gates the CI object store (pure, no I/O)."""

from __future__ import annotations

import pytest

from tests.support.store_throughput import Throughput, verdict

KIB = 1024
MB = 1_000_000


def test_the_ci_stall_rate_fails_and_names_both_floors() -> None:
    reason = verdict(Throughput((64 * KIB,) * 4))
    assert reason is not None
    assert "median 0.07 MB/s < 5 MB/s" in reason
    assert "slowest 0.066 MB/s < 1 MB/s" in reason
    assert "4 writes" in reason


def test_one_stalled_write_fails_even_when_the_median_is_fast() -> None:
    reason = verdict(Throughput((40 * MB, 40 * MB, 40 * MB, 64 * KIB)))
    assert reason is not None
    assert "slowest" in reason
    assert "median" not in reason


def test_a_slow_median_fails_even_when_no_write_stalled() -> None:
    reason = verdict(Throughput((2 * MB, 3 * MB, 4 * MB)))
    assert reason is not None
    assert "median 3.00 MB/s < 5 MB/s" in reason


def test_no_measured_write_is_not_a_pass() -> None:
    assert verdict(Throughput(())) == "no write was measured"


@pytest.mark.parametrize("rates", [(5 * MB,), (1 * MB, 5 * MB, 60 * MB)])
def test_a_store_at_or_above_both_floors_passes(rates: tuple[float, ...]) -> None:
    assert verdict(Throughput(rates)) is None
