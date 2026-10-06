"""Locust baseline for the Sprint 2 endpoints (ST-039 slice 3, SRE; NFR-010, NFR-013, NFR-041).

At test start, one fresh account signs in by magic link, creates a doubles match, uploads the
fixture and tags the 6-rally journey, with the goal harness in ``scripts/measure`` (no second
copy of the routes: they live only in ``tagcontract.py``). Then:

* ``ReadUser`` x (users - 1), one request per second each: GET score sheet, GET correction
  history, GET match, in rotation (NFR-010 read baseline, NFR-041 availability);
* ``CorrectionUser`` x 1: a correction of one rally's winner, then an undo, with the
  ``If-Match`` version of the previous answer (NFR-013 correction round trip). One user only,
  so its versions never race.

When the run's time limit stops the correction user with a correction in flight, the server
may still apply it with no undo to follow; ``perf_restore`` undoes that one correction (version
parity) before the check (CI run 37505286086). At the end the sheet must be byte-identical
to the one after seeding (C-04), and the state goes to ``RA_PERF_STATE`` (JSON) for
``scripts/ci/perf_verdict.py``.

    MAILPIT_API_URL=http://127.0.0.1:8025 RA_ORIGIN=https://localhost:3000 RA_CACERT=root.crt \
    RA_PERF_STATE=reports/perf/perf_state.json \
    uvx --from locust==2.46.7 locust -f backend/tests/perf/locustfile_sprint02.py --headless \
      --host http://127.0.0.1:8000 -u 51 -r 51 -t 60s --csv reports/perf/perf --only-summary

Not collected by pytest (the file name does not start with ``test_``).
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
from itertools import cycle
from pathlib import Path
from typing import Any

from locust import FastHttpUser, constant_throughput, events, task

MEASURE = Path(__file__).resolve().parents[3] / "scripts" / "measure"
sys.path.insert(0, str(MEASURE))
import tagcontract as k  # noqa: E402
import taglib as t  # noqa: E402
from live_goal import new_match  # noqa: E402
from live_tagging import Session, _tag_all, upload_video  # noqa: E402
from livehttp import Client, sign_in, ssl_context  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from perf_restore import restore_orphan_correction  # noqa: E402

FIXTURE = MEASURE.parents[1] / "fixtures" / "clips" / "synthetic-60s" / "clip.mp4"
STATE: dict[str, Any] = {"seeded": False}
CORRECTION = {"field": "winning_side", "value": "A"}


ORIGIN = os.environ.get("RA_ORIGIN", "https://localhost:3000")


def _client(base: str) -> Client:
    return Client(base, ORIGIN, ssl_context(os.environ.get("RA_CACERT"), False))


def _seed_api() -> str:
    # Seeding goes through the web origin: in Compose the tus Location carries the /api prefix
    # of the web rewrite, so an upload started on the bare API port cannot continue there
    # (measured 2026-10-06). The load itself targets --host (the API port, NFR-010).
    return os.environ.get("RA_SEED_API") or f"{ORIGIN.rstrip('/')}/api"


@events.test_start.add_listener
def seed(environment: Any, **_: Any) -> None:
    c = _client(_seed_api())
    try:
        if not sign_in(c, os.environ.get("MAILPIT_API_URL", "http://127.0.0.1:8025"))["ok"]:
            raise RuntimeError("sign-in failed")
        match_id = new_match(c)
        if not match_id or not upload_video(c, match_id, FIXTURE.read_bytes(), 120)["ok"]:
            raise RuntimeError("match or upload failed")
        s = Session(c, match_id)
        tagged = _tag_all(s, t.JOURNEY_TAGS, "A", check_each=False)
        if not tagged["ok"]:
            raise RuntimeError(f"tagging failed: {tagged['diffs']}")
        _, sheet = s.sheet()
        STATE.update(
            seeded=True,
            cookie=c.cookie,
            origin=c.origin,
            match_id=match_id,
            rally_ids=tagged["rally_ids"],
            version=s.version,
            seed_version=s.version,
            baseline=t.canonical_bytes(sheet).decode(),
        )
    except Exception as exc:  # noqa: BLE001 - any seeding failure stops the run, fail closed
        STATE["error"] = repr(exc)
        environment.process_exit_code = 1
        if environment.runner is not None:
            environment.runner.quit()
    finally:
        c.close()


def _server_version(c: Client) -> int:
    method, path = k.path("sheet", match_id=STATE["match_id"])
    r = c.request(method, path)
    if r.status != 200:
        raise RuntimeError(f"score sheet {r.status}")
    return int(str(r.headers.get("ETag", "")).strip('"'))


def _undo(c: Client, version: int) -> None:
    method, path = k.path("undo", match_id=STATE["match_id"])
    r = c.request(method, path, headers={k.VERSION_HEADER: str(version)})
    if r.status != 200:
        raise RuntimeError(f"undo {r.status}")


@events.quitting.add_listener
def write_state(environment: Any, **_: Any) -> None:
    if STATE.get("seeded"):
        c = _client(environment.host)
        c.cookie = STATE["cookie"]
        try:
            STATE["orphan_undone"] = restore_orphan_correction(
                lambda: _server_version(c), lambda v: _undo(c, v), STATE["seed_version"]
            )
            _, sheet = Session(c, STATE["match_id"]).sheet()
            STATE["restored_byte_identical"] = (
                t.canonical_bytes(sheet).decode() == STATE["baseline"]
            )
        finally:
            c.close()
    out = os.environ.get("RA_PERF_STATE")
    if out:
        public = {
            key: STATE[key]
            for key in ("seeded", "error", "restored_byte_identical", "pairs", "orphan_undone")
            if key in STATE
        }
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")


class _Base(FastHttpUser):  # geventhttpclient: less generator CPU than requests
    abstract = True

    def on_start(self) -> None:
        if not STATE.get("seeded"):
            self.stop()  # seeding failed; the run is already marked failed
        self.headers = {"Cookie": STATE["cookie"], "Origin": STATE["origin"]}


class ReadUser(_Base):
    wait_time = constant_throughput(1)

    def on_start(self) -> None:
        super().on_start()
        # Spread the readers over the second: with every user on the same phase, each second
        # arrived as one burst of 50 requests (measured 2026-10-06: p50 ~400 ms in Locust
        # against p50 17 ms from the open-loop tag_latency.py on the same stack).
        time.sleep(random.random())  # noqa: S311 - load-shape jitter, not security
        m = STATE["match_id"]
        self.reads = cycle(
            [
                ("score-sheet", k.path("sheet", match_id=m)[1]),
                ("corrections", k.path("history", match_id=m)[1]),
                ("match", f"/matches/{m}"),
            ]
        )

    @task
    def read(self) -> None:
        name, path = next(self.reads)
        self.client.get(path, headers=self.headers, name=name)


class CorrectionUser(_Base):
    fixed_count = 1
    wait_time = constant_throughput(1)

    def _command(self, name: str, body: Any = None, rally_id: str = "") -> bool:
        method, path = k.path(name, match_id=STATE["match_id"], rally_id=rally_id)
        headers = {**self.headers, k.VERSION_HEADER: str(STATE["version"])}
        with self.client.request(
            method, path, json=body, headers=headers, name=name, catch_response=True
        ) as r:
            if r.status_code != 200:
                r.failure(f"{r.status_code} {r.text[:120]}")
                return False
            STATE["version"] = r.json().get(k.VERSION_KEY, STATE["version"])
            return True

    @task
    def correct_then_undo(self) -> None:
        # Rally 2's winner to A: the journey's own correction (G02-01 step 7), valid for its
        # ending and player, so a refusal here is a real failure, never a bad sample.
        # A pair cut by the run's end is put back after the run (perf_restore, version parity).
        if self._command("correct", CORRECTION, STATE["rally_ids"][1]) and self._command("undo"):
            STATE["pairs"] = STATE.get("pairs", 0) + 1
