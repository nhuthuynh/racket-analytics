"""Open-loop pacing for Locust readers (C4-LOCUST; NFR-010). Standard library only, so the
unit tests run without Locust (infra/tests/test_perf_pacing.py).

Locust's ``constant_throughput`` re-anchors a user on its finish time once a request runs past
the period, so one slow second (a cold start) lines every reader up into one burst per second,
and the burst then holds itself. Measured 2026-10-17 on the local stack: 48 of 50 requests
sent within the same 100 ms of each second, GET stats p95 780 ms server-side, against p95
26.5 ms for the same routes and rate open loop (``scripts/measure/stats_latency.py``).
``phased_pacing`` keeps each user on its own fixed phase: a late request skips the slots it
missed, so the arrivals stay spread and the measured latency is the server's.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from typing import Any

GOLDEN = (math.sqrt(5) - 1) / 2  # low-discrepancy sequence: evenly spread for any user count


def reader_phase(index: int) -> float:
    """The fixed phase in [0, 1) of the period for reader ``index`` (0, 1, 2, ...)."""
    return (index * GOLDEN) % 1.0


def phased_pacing(
    period_s: float, clock: Callable[[], float] = time.monotonic
) -> Callable[[Any], float]:
    """A Locust ``wait_time``: one request per ``period_s`` at ``user.due`` (set by the user's
    ``on_start`` to its first slot), skipping missed slots instead of re-anchoring."""

    def wait_time_func(user: Any) -> float:
        now = clock()
        user.due += period_s
        if user.due < now:
            user.due += period_s * math.ceil((now - user.due) / period_s)
        return user.due - now

    return wait_time_func
