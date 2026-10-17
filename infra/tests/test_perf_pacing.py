"""C4-LOCUST unit: the open-loop pacing of the dashboard readers (backend/tests/perf/pacing.py).

Measured 2026-10-17 on the local stack: with Locust's ``constant_throughput(1)`` the 50
readers sent 48-50 requests within the same 100 ms of every second (one slow cold-start second
re-anchors every user on its finish time), so the server queued them: GET stats p95 780 ms
server-side, against p95 26.5 ms open loop at the same rate (``stats_latency.py``). The
pacing keeps each reader on a fixed phase and skips slots it missed instead of re-anchoring.
"""

from __future__ import annotations

import importlib.util
from collections import Counter
from types import ModuleType, SimpleNamespace

import pytest
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

PACING = REPO_ROOT / "backend" / "tests" / "perf" / "pacing.py"


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("perf_pacing", PACING)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def wait(due: float, now: float, period: float = 1.0) -> tuple[float, float]:
    user = SimpleNamespace(due=due)
    w = _module().phased_pacing(period, clock=lambda: now)(user)
    return w, user.due


# ---------------------------------------------------------------- negative cases first
def test_a_late_request_keeps_the_phase_and_does_not_fire_at_once() -> None:
    # due at 10.0, the request ran until 11.5: constant_throughput would wait 0 (re-anchor at
    # 11.5, in step with every other late reader); the phase keeps the next slot at 12.0
    w, due = wait(due=9.0, now=11.5)
    assert due == pytest.approx(12.0)
    assert w == pytest.approx(0.5)


def test_fifty_readers_never_line_up_in_one_slot() -> None:
    phases = [_module().reader_phase(i) for i in range(50)]
    per_100ms = Counter(int(p * 10) for p in phases)
    assert max(per_100ms.values()) <= 6, per_100ms  # measured burst: 48 in one 100 ms slot
    assert all(0.0 <= p < 1.0 for p in phases)


# ---------------------------------------------------------------- positive
def test_an_on_time_request_waits_for_its_next_slot() -> None:
    w, due = wait(due=10.0, now=10.2)
    assert due == pytest.approx(11.0)
    assert w == pytest.approx(0.8)


def test_the_rate_is_one_request_per_period() -> None:
    user, now = SimpleNamespace(due=0.0), [0.0]
    pace = _module().phased_pacing(0.5, clock=lambda: now[0])
    for _ in range(10):
        now[0] += 0.05 + pace(user)  # 50 ms request, then the wait
    assert user.due == pytest.approx(5.0)
