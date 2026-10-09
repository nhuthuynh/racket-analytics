"""CI-OBJSTORE-SLOW: the object store of this stack takes the 1.72 MB clip fast enough for the
suites (median >= 5 MB/s, no write < 1 MB/s), measured the way ``write_chunk`` stores it, from as
many parallel writers as CI has xdist workers. CI runs this file on its own before the backend
suites and again before the red_until rows (ci.yml), where runs 37764445816 and 37961668800 saw
about 64 KiB/s. The negative control proves the check catches that rate on the same stack.
"""

from __future__ import annotations

import dataclasses
import os

import pytest

from racket.platform.storage import ObjectStore, S3Config
from tests.support.paths import SYNTHETIC_CLIP
from tests.support.slow_store import CI_WRITE_RATE, slow_object_store
from tests.support.store_throughput import measure, verdict

WRITERS = 4  # ubuntu-24.04 runners: 4 vCPU, `-n auto` = 4 xdist workers
ROUNDS = 3


def _store(endpoint: str | None = None) -> ObjectStore:
    config = S3Config.from_env()
    if endpoint is not None:
        config = dataclasses.replace(config, endpoint_url=endpoint)
    return ObjectStore(config)


def test_the_store_takes_the_clip_at_the_floor_from_parallel_writers() -> None:
    clip = SYNTHETIC_CLIP.read_bytes()
    assert len(clip) == 1_724_207  # the clip of the CI incidents
    result = measure(_store, clip, writers=WRITERS, rounds=ROUNDS)
    assert len(result.rates) == WRITERS * ROUNDS
    assert verdict(result) is None, verdict(result)


@pytest.mark.slow
def test_the_floor_fails_on_a_store_at_the_ci_stall_rate() -> None:
    """Negative control: the same check through a proxy at the measured CI rate (64 KiB/s)."""
    data = SYNTHETIC_CLIP.read_bytes()[: 128 * 1024]  # 192 KiB per write: ~3 s at the CI rate
    with slow_object_store(os.environ["S3_ENDPOINT_URL"], CI_WRITE_RATE) as endpoint:
        result = measure(lambda: _store(endpoint), data, writers=1, rounds=1)
    reason = verdict(result)
    assert reason is not None
    assert "median" in reason
    assert "slowest" in reason
