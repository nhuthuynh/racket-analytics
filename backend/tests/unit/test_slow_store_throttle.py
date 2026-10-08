"""Unit tests of the pacing used by the slow object store (CI-IT0213-HANG; testing-strategy
rule 8: a test tool needs its own checks). Pure: the clock is passed in, nothing sleeps."""

from __future__ import annotations

import pytest

from tests.support.slow_store import CI_WRITE_RATE, Throttle


def test_a_rate_of_zero_or_less_is_refused() -> None:
    with pytest.raises(ValueError, match="rate must be positive"):
        Throttle(0, now=0.0)
    with pytest.raises(ValueError, match="rate must be positive"):
        Throttle(-1, now=0.0)


def test_bytes_sent_faster_than_the_rate_wait_for_the_rate() -> None:
    throttle = Throttle(1_000, now=10.0)
    assert throttle.delay_after(500, now=10.0) == pytest.approx(0.5)
    assert throttle.delay_after(500, now=10.5) == pytest.approx(0.5)


def test_bytes_sent_slower_than_the_rate_do_not_wait() -> None:
    throttle = Throttle(1_000, now=0.0)
    assert throttle.delay_after(1_000, now=3.0) == 0.0


def test_the_ci_rate_makes_a_clip_chunk_take_as_long_as_in_the_failed_run() -> None:
    """Run 37764445816: a half-clip staging write (862,104 bytes) took 13.3 s and the whole-clip
    part (1,724,207 bytes) 26.7 s, request overhead included."""
    assert CI_WRITE_RATE == 64 * 1024
    assert Throttle(CI_WRITE_RATE, now=0.0).delay_after(862_104, now=0.0) == pytest.approx(
        13.2, abs=0.1
    )
    assert Throttle(CI_WRITE_RATE, now=0.0).delay_after(1_724_207, now=0.0) == pytest.approx(
        26.3, abs=0.1
    )
