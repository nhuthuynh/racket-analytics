"""Locust run of the perf-baseline job from Sprint 4 (C4-LOCUST; ST-054 SRE half; NFR-010
"dashboard", NFR-013, NFR-041).

An extension of ``locustfile_sprint02.py``: the same seeding (one fresh account, a doubles
match, the fixture uploaded, the 6-rally journey tagged), the same correction user and the
same restore check (C-04). The readers add the two dashboard reads of the seeded tagged match
to their rotation: GET stats and GET evidence (AN-01, side A), the G03-05 routes. Routes come
only from the harness contracts (``tagcontract.py``, ``statscontract.py``).

* ``DashboardReadUser`` x (users - 1), one request per second each on a fixed phase
  (``pacing.phased_pacing``, open loop): GET score sheet, GET correction history, GET match,
  GET stats, GET evidence, in rotation;
* ``CorrectionUser`` x 1 (from Sprint 2): correction + undo with ``If-Match``.

At test start, after the Sprint 2 seeding, the stats and the evidence of the match must answer
200 with the metric present, or the run is marked not seeded (fails closed: the load must
measure real stats, not a 404 or an empty body). ``scripts/ci/perf_verdict.py
--dashboard-reads stats,evidence`` gates them at p95 <= 300 ms, p99 <= 800 ms and
availability >= 99.5% per route.

    MAILPIT_API_URL=http://127.0.0.1:8025 RA_ORIGIN=https://localhost:3000 RA_CACERT=root.crt \\
    RA_PERF_STATE=reports/perf/perf_state.json \\
    uvx --from locust==2.46.7 locust -f backend/tests/perf/locustfile_sprint04.py --headless \\
      --host http://127.0.0.1:8000 -u 51 -r 51 -t 90s --csv reports/perf/perf --only-summary

Not collected by pytest (the file name does not start with ``test_``).
"""

from __future__ import annotations

import sys
import time
from itertools import count, cycle
from pathlib import Path
from typing import Any

from locust import events, task

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Importing the Sprint 2 file registers its seeding (test_start) and restore (quitting)
# listeners; only CorrectionUser is taken into this namespace, so Locust runs no Sprint 2
# reader beside the dashboard readers.
from locustfile_sprint02 import STATE, CorrectionUser, _Base, _client, k
from pacing import phased_pacing, reader_phase

MEASURE = Path(__file__).resolve().parents[3] / "scripts" / "measure"
sys.path.insert(0, str(MEASURE))
import statscontract as sk  # noqa: E402

EVIDENCE = {"metric_id": "AN-01", "side": "A"}  # as G03-05 (stats_latency.py)
READY_TIMEOUT_S = 30.0
_readers = count()
_anchor: list[float] = []

__all__ = ["CorrectionUser", "DashboardReadUser"]


def _dashboard_paths(match_id: str) -> list[tuple[str, str]]:
    return [
        ("stats", sk.path("stats", match_id=match_id)[1]),
        ("evidence", sk.path("evidence", match_id=match_id, **EVIDENCE)[1]),
    ]


@events.test_start.add_listener
def dashboard_ready(environment: Any, **_: Any) -> None:
    """Registered after the Sprint 2 seeding, so it runs after it: the seeded match must
    serve its stats (with the metric) and its evidence before any load."""
    if not STATE.get("seeded"):
        return  # seeding already failed and stopped the run
    c = _client(environment.host)
    c.cookie = STATE["cookie"]
    try:
        stats_path, evidence_path = (p for _, p in _dashboard_paths(STATE["match_id"]))
        deadline = time.monotonic() + READY_TIMEOUT_S
        while True:
            stats = c.request("GET", stats_path)
            body = stats.json() if stats.status == 200 else {}
            if EVIDENCE["metric_id"] in (body or {}).get(sk.METRICS_KEY, {}):
                break
            if time.monotonic() > deadline:
                raise RuntimeError(f"stats not ready: {stats.status}")
            time.sleep(0.5)
        evidence = c.request("GET", evidence_path)
        if evidence.status != 200:
            raise RuntimeError(f"evidence {evidence.status}")
        STATE["evidence_total"] = evidence.json().get(sk.EVIDENCE_TOTAL)
    except Exception as exc:  # noqa: BLE001 - fail closed, as the Sprint 2 seeding does
        STATE.update(seeded=False, error=repr(exc))
        environment.process_exit_code = 1
        if environment.runner is not None:
            environment.runner.quit()
    finally:
        c.close()


class DashboardReadUser(_Base):
    wait_time = phased_pacing(1.0)

    def on_start(self) -> None:
        super().on_start()
        if not STATE.get("seeded"):
            return  # stopped by _Base.on_start; the run is already marked failed
        if not _anchor:
            _anchor.append(time.monotonic() + 1.0)
        self.due = _anchor[0] + reader_phase(next(_readers))
        time.sleep(max(0.0, self.due - time.monotonic()))  # gevent-patched: cooperative
        m = STATE["match_id"]
        self.reads = cycle(
            [
                ("score-sheet", k.path("sheet", match_id=m)[1]),
                ("corrections", k.path("history", match_id=m)[1]),
                ("match", f"/matches/{m}"),
                *_dashboard_paths(m),
            ]
        )

    @task
    def read(self) -> None:
        name, path = next(self.reads)
        self.client.get(path, headers=self.headers, name=name)
