"""Locust run of ``GET /me/plan`` at 50 RPS (SRE-VERIFY04R3-01; G04-02 c; NFR-019 read side).

The goal's configuration (goal-scorecard G04-02 c, ``live_plan.py --load``): one fresh account
seeded as ``live_plan.seed`` does (sign-in, a doubles match, the fixture by tus, the coach's
worked example tagged, stats current), then ``POST /me/plan`` with the goal's preferences.
``PlanReadUser`` x 50 each read the plan once a second on a fixed phase (open loop,
``pacing.phased_pacing``), so 50 users make 50 RPS. A seeding failure stops the run and marks
it not seeded (fails closed). ``scripts/ci/plan_load_verdict.py`` gates the run.

    MAILPIT_API_URL=http://127.0.0.1:8025 RA_ORIGIN=https://localhost:3000 RA_CACERT=root.crt \\
    RA_PERF_STATE=reports/perf/plan_state.json \\
    uvx --from locust==2.46.7 locust -f backend/tests/perf/locustfile_plan.py --headless \\
      --host http://127.0.0.1:8000 -u 50 -r 50 -t 100s --csv reports/perf/plan --only-summary

Not collected by pytest (the file name does not start with ``test_``).
"""

from __future__ import annotations

import json
import os
import sys
import time
from argparse import Namespace
from itertools import count
from pathlib import Path
from typing import Any

from locust import FastHttpUser, events, task

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pacing import phased_pacing, reader_phase

MEASURE = Path(__file__).resolve().parents[3] / "scripts" / "measure"
sys.path.insert(0, str(MEASURE))
import live_plan as lp  # noqa: E402
from livehttp import ssl_context  # noqa: E402

FIXTURE = MEASURE.parents[1] / "fixtures" / "clips" / "synthetic-60s" / "clip.mp4"
ORIGIN = os.environ.get("RA_ORIGIN", "https://localhost:3000").rstrip("/")
STATE: dict[str, Any] = {"seeded": False}
_readers = count()
_anchor: list[float] = []


@events.test_start.add_listener
def seed(environment: Any, **_: Any) -> None:
    args = Namespace(
        api=f"{ORIGIN}/api",
        origin=ORIGIN,
        mailpit=os.environ.get("MAILPIT_API_URL", "http://127.0.0.1:8025"),
        data=FIXTURE.read_bytes(),
        result_timeout=120.0,
    )
    steps: dict[str, Any] = {}
    try:
        c, match_id, _ = lp.seed(args, ssl_context(os.environ.get("RA_CACERT"), False), steps)
        if not match_id:
            raise RuntimeError(f"seeding failed: {steps}")
        generated = c.request("POST", "/me/plan", json_body=lp.PREFS).status
        if generated != 201:
            raise RuntimeError(f"POST /me/plan {generated}")
        STATE.update(seeded=True, cookie=c.cookie)
    except Exception as exc:  # noqa: BLE001 - any seeding failure stops the run, fail closed
        STATE["error"] = repr(exc)[:500]
        environment.process_exit_code = 1
        if environment.runner is not None:
            environment.runner.quit()


@events.quitting.add_listener
def write_state(environment: Any, **_: Any) -> None:
    if out := os.environ.get("RA_PERF_STATE"):
        public = {key: STATE[key] for key in ("seeded", "error") if key in STATE}
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")


class PlanReadUser(FastHttpUser):
    wait_time = phased_pacing(1.0)

    def on_start(self) -> None:
        if not STATE.get("seeded"):
            self.stop()  # seeding failed; the run is already marked failed
            return
        self.headers = {"Cookie": STATE["cookie"], "Origin": ORIGIN}
        if not _anchor:
            _anchor.append(time.monotonic() + 1.0)
        self.due = _anchor[0] + reader_phase(next(_readers))
        time.sleep(max(0.0, self.due - time.monotonic()))  # gevent-patched: cooperative

    @task
    def read(self) -> None:
        self.client.get("/me/plan", headers=self.headers, name="plan")
