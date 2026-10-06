"""Undo a correction that the Locust run stopped mid-flight (ST-039 slice 3, CI run 37505286086).

The correction user sends only correct/undo pairs and every command bumps the match version by
one, so after the run an odd distance from the seeded version means exactly one correction
the server applied but the client never saw answered. Kept free of Locust so it is unit-tested
(infra/tests/test_perf_restore.py).
"""

from __future__ import annotations

import time
from collections.abc import Callable


def restore_orphan_correction(
    read_version: Callable[[], int],
    undo: Callable[[int], object],
    seed_version: int,
    *,
    settle_reads: int = 5,
    interval_s: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Wait until the server version stops moving, then undo once if a correction is unpaired.

    Returns the number of undos sent (0 or 1). A version below the seed fails closed.
    """
    version = read_version()
    for _ in range(settle_reads):
        sleep(interval_s)
        latest = read_version()
        if latest == version:
            break
        version = latest
    extra = version - seed_version
    if extra < 0:
        raise ValueError(f"server version {version} is below the seeded version {seed_version}")
    if extra % 2 == 0:
        return 0
    undo(version)
    return 1
