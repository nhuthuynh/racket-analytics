"""CI-PERF-GATES integration: a real Locust 2.46.7 run (the CI pin) with a slow start-up
reproduces the PR #6 failure shape and shows the windowed verdict measures only the
steady state.

The locustfile below seeds for ``SEED_S`` seconds in ``test_start`` (as
``locustfile_sprint02.py`` signs in, uploads and tags), which Locust counts inside
``--run-time``. A local threaded HTTP server answers every request, so the steady rate is
the users' ``constant_throughput(1)`` sum. Needs ``uvx`` (CI installs uv) and PyPI access.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from conftest import REPO_ROOT

pytestmark = pytest.mark.integration

SCRIPT = REPO_ROOT / "scripts" / "ci" / "perf_verdict.py"
LOCUST = "locust==2.46.7"  # same pin as the perf-baseline job
USERS = 20
SEED_S = 12
RUN_S = 45  # 12 s start-up + ~33 s steady window

LOCUSTFILE = """
import time
from itertools import cycle
from locust import FastHttpUser, constant_throughput, events, task

@events.test_start.add_listener
def seed(environment, **_):
    time.sleep(SEED_S)  # stands in for sign-in, upload and tagging

class U(FastHttpUser):
    wait_time = constant_throughput(1)
    def on_start(self):
        self.names = cycle(["score-sheet", "corrections", "match", "correct", "undo"])
    @task
    def hit(self):
        self.client.get("/", name=next(self.names))
"""


class _Ok(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *_: object) -> None:
        pass


@pytest.fixture(scope="module")
def slow_start_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if shutil.which("uvx") is None:
        pytest.fail("uvx not on PATH: install uv (CI: pip install uv) - fails closed, no skip")
    d = tmp_path_factory.mktemp("locust")
    (d / "lf.py").write_text(LOCUSTFILE.replace("SEED_S", str(SEED_S)))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Ok)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        res = subprocess.run(
            ["uvx", "--from", LOCUST, "locust", "-f", str(d / "lf.py"), "--headless",
             "--host", f"http://127.0.0.1:{srv.server_address[1]}", "-u", str(USERS),
             "-r", str(USERS), "-t", f"{RUN_S}s", "--csv", str(d / "perf"), "--only-summary"],
            capture_output=True, text=True, timeout=RUN_S + 240, check=False,
        )  # fmt: skip
    finally:
        srv.shutdown()
    assert (d / "perf_stats_history.csv").exists(), res.stdout + res.stderr
    (d / "state.json").write_text(json.dumps({"seeded": True, "restored_byte_identical": True}))
    return d


def _verdict(d: Path, *extra: str) -> tuple[int, dict]:
    out = d / f"verdict{len(extra)}.json"
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--stats", str(d / "perf_stats.csv"), "--state",
         str(d / "state.json"), "--rps", str(USERS), "--json", str(out), *extra],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert out.exists(), res.stdout + res.stderr
    return res.returncode, json.loads(out.read_text())


def test_whole_run_rate_is_dragged_down_by_start_up(slow_start_run: Path) -> None:
    # The bug, reproduced: no product change, yet the whole-run rate misses 95% of target.
    rc, body = _verdict(slow_start_run)
    assert body["achieved_rps"] < 0.95 * USERS, body
    assert body["checks"]["achieved_rps"] is False
    assert rc == 1


def test_windowed_rate_measures_the_steady_state(slow_start_run: Path) -> None:
    rc, body = _verdict(
        slow_start_run,
        "--history", str(slow_start_run / "perf_stats_history.csv"),
        "--users", str(USERS), "--min-window", "25",
    )  # fmt: skip
    assert body["window"]["warm_up_s"] >= SEED_S - 1, body["window"]
    assert body["window"]["seconds"] >= 25, body["window"]
    assert body["achieved_rps"] >= 0.95 * USERS, body
    assert body["run_rps"] < 0.95 * USERS
    assert rc == 0, body["checks"]
