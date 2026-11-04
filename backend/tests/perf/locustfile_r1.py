"""Locust run of the R1 reads at 50 RPS (ST-074; NFR-010.1-.9; goal-scorecard G05-01).

Every user seeds its own account first (one seeded demo account per user, NFR-010 common
method), as ``live_plan.seed`` does: magic-link sign-in, the adult age confirmation (flags on),
a doubles match, the fixture by tus, the coach's worked example tagged and its stats current,
then ``POST /me/plan``. Seeding goes
through the web origin (the tus Location carries its ``/api`` prefix); the load targets the
API port. A seeding failure stops the run (fails closed).

Then each user reads once a second on its own fixed phase (open loop, ``pacing``), in rotation:

* ``match``: GET /matches/{id} (NFR-010.1-.2);
* ``score-sheet``: GET /matches/{id}/score-sheet (NFR-010.3-.4);
* ``dashboard:stats`` and ``dashboard:evidence``: the two dashboard reads of
  ``locustfile_sprint04._dashboard_paths`` (NFR-010.5-.6);
* ``plan``: GET /me/plan (NFR-010.7-.8).

Warm-up: ``R1_WARMUP_S`` (default 60) seconds after the last user finished seeding, the
statistics are reset, so the ``--csv`` stats file holds the measured window only and its
history file shows the reset. ``scripts/ci/perf_verdict.py --per-endpoint
match,score-sheet,dashboard,plan --warmup-s 60`` checks that and gates each read.

    uvx --from locust==2.46.7 locust -f backend/tests/perf/locustfile_r1.py --headless \\
      -u 50 -r 50 -t 8m --csv reports/perf/r1-1 --only-summary

Defaults fit ``make up``: API ``RA_API`` = http://127.0.0.1:8000 (``--host`` overrides),
origin ``RA_ORIGIN`` = https://localhost:3000, CA ``RA_CACERT``, else ``.local/demo/root.crt``
(copied by ``make demo``), else TLS unverified on loopback only (ADR 0029),
``MAILPIT_API_URL`` = http://127.0.0.1:8025. Sign-in needs the
per-IP auth limits raised (``AUTH_LINK_LIMIT_PER_IP``/``AUTH_EXCHANGE_LIMIT_PER_IP``), as in
the CI perf jobs. Not collected by pytest (the file name does not start with ``test_``).
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from itertools import count, cycle
from pathlib import Path
from typing import Any

import gevent
from locust import FastHttpUser, events, task

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "scripts" / "measure"))
import live_plan as lp  # noqa: E402
import statscontract as sk  # noqa: E402
import statslib as st  # noqa: E402
import tagcontract as k  # noqa: E402
from live_goal import new_match  # noqa: E402
from live_stats import _poll_stats, _reference, sign_in_as  # noqa: E402
from live_tagging import Session, upload_video  # noqa: E402
from livehttp import Client, ssl_context  # noqa: E402
from pacing import phased_pacing, reader_phase  # noqa: E402

FIXTURE = REPO / "fixtures" / "clips" / "synthetic-60s" / "clip.mp4"
ORIGIN = os.environ.get("RA_ORIGIN", "https://localhost:3000").rstrip("/")
DEMO_CA = REPO / ".local" / "demo" / "root.crt"
EVIDENCE = {"metric_id": "AN-01", "side": "A"}  # as locustfile_sprint04 (G03-05)
MAILPIT = os.environ.get("MAILPIT_API_URL", "http://127.0.0.1:8025")
WARMUP_S = float(os.environ.get("R1_WARMUP_S", "60"))
STATE: dict[str, Any] = {"seeded": 0, "error": None, "reset_at": None}
_readers = count()


def r1_reads(match_id: str) -> list[tuple[str, str]]:
    """The R1 reads of one seeded account, as (Locust name, path)."""
    return [
        ("match", f"/matches/{match_id}"),
        ("score-sheet", k.path("sheet", match_id=match_id)[1]),
        ("dashboard:stats", sk.path("stats", match_id=match_id)[1]),
        ("dashboard:evidence", sk.path("evidence", match_id=match_id, **EVIDENCE)[1]),
        ("plan", "/me/plan"),
    ]


def seed_account() -> tuple[str, str]:
    """One fresh account with a tagged match, current stats and a plan: (cookie, match id).
    The steps of ``live_plan.seed`` plus the adult age confirmation that FEATURE_AGE_GATE
    requires before any other call (404 with the flag off)."""
    cacert = os.environ.get("RA_CACERT") or (str(DEMO_CA) if DEMO_CA.is_file() else None)
    # Without a CA file: loopback only (livehttp never relaxes TLS beyond it; ADR 0029).
    c = Client(f"{ORIGIN}/api", ORIGIN, ssl_context(cacert, cacert is None))
    if not sign_in_as(c, MAILPIT, f"r1-{uuid.uuid4().hex[:12]}@example.com"):
        raise RuntimeError("sign-in failed")
    age = c.request("POST", "/me/age-confirmation", json_body={"is_adult": True}).status
    if age not in (200, 404):
        raise RuntimeError(f"age confirmation {age}")
    match_id = new_match(c)
    if not match_id or not upload_video(c, match_id, FIXTURE.read_bytes(), 120)["ok"]:
        raise RuntimeError("match or upload failed")
    sess = Session(c, match_id)
    sess.call("start_game", {**k.START_GAME_BODY, "first_serving_side": "A"})
    codes = {sess.call("tag", tag).status for tag in st.STATS_TAGS}
    _, diffs = _poll_stats(c, match_id, _reference(st.STATS_TAGS), 120.0)
    if diffs or codes != {201}:
        raise RuntimeError(f"tagging: {codes} {diffs[:3]}")
    if (status := c.request("POST", "/me/plan", json_body=lp.PREFS).status) != 201:
        raise RuntimeError(f"POST /me/plan {status}")
    evidence = sk.path("evidence", match_id=match_id, **EVIDENCE)
    if (status := c.request(*evidence).status) != 200:
        raise RuntimeError(f"evidence {status}")
    return c.cookie, match_id


def _reset_after_warmup(environment: Any) -> None:
    environment.runner.stats.reset_all()
    STATE["reset_at"] = time.time()


@events.test_stop.add_listener
def report(**_: Any) -> None:
    print(f"locustfile_r1: {STATE}", file=sys.stderr)


class R1ReadUser(FastHttpUser):
    host = os.environ.get("RA_API", "http://127.0.0.1:8000")
    wait_time = phased_pacing(1.0)

    def on_start(self) -> None:
        try:
            cookie, match_id = seed_account()
        except Exception as exc:  # noqa: BLE001 - any seeding failure stops the run
            STATE["error"] = repr(exc)[:500]
            self.environment.process_exit_code = 1
            self.environment.runner.quit()
            return
        self.headers = {"Cookie": cookie, "Origin": ORIGIN}
        self.reads = cycle(r1_reads(match_id))
        STATE["seeded"] += 1
        runner = self.environment.runner
        if STATE["seeded"] == runner.target_user_count:
            gevent.spawn_later(WARMUP_S, _reset_after_warmup, self.environment)
        self.due = time.monotonic() + reader_phase(next(_readers))
        time.sleep(max(0.0, self.due - time.monotonic()))  # gevent-patched: cooperative

    @task
    def read(self) -> None:
        name, path = next(self.reads)
        self.client.get(path, headers=self.headers, name=name)
