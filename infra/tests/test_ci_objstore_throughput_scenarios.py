"""Binds tests/features/ci_objstore_throughput.feature (CI-OBJSTORE-SLOW; NFR-073, NFR-074):
the real ci.yml, and the real runner telemetry script against a stand-in S3 endpoint."""

from __future__ import annotations

import os
import re
import subprocess
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
import yaml
from conftest import REPO_ROOT
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.unit
scenarios("ci_objstore_throughput.feature")

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"
SCRIPT = REPO_ROOT / "scripts" / "ci" / "objectstore_telemetry.sh"
FLOOR_TEST = "tests/integration/harness/test_ci_objstore_throughput.py"
CLIP_BYTES = 1_724_207


def _steps() -> list[dict[str, Any]]:
    return yaml.safe_load(CI.read_text())["jobs"]["integration"]["steps"]


def _first(steps: list[dict[str, Any]], needle: str) -> int:
    return next(i for i, s in enumerate(steps) if needle in s.get("run", ""))


# ---------------------------------------------------------------- the CI job
@given("the CI integration job", target_fixture="steps")
def job() -> list[dict[str, Any]]:
    return _steps()


def _floor_steps(steps: list[dict[str, Any]]) -> list[int]:
    return [i for i, s in enumerate(steps) if FLOOR_TEST in s.get("run", "")]


@then("the job checks the store's write throughput before the backend suites")
def floor_before_suites(steps: list[dict[str, Any]]) -> None:
    suites = _first(steps, "run_with_budget.py")
    services = _first(steps, "up -d --wait postgres objectstore")
    assert any(services < i < suites for i in _floor_steps(steps)), _floor_steps(steps)


@then("the job checks the store's write throughput again before the red_until rows")
def floor_before_red_until(steps: list[dict[str, Any]]) -> None:
    suites = _first(steps, "run_with_budget.py")
    red_until = next(i for i, s in enumerate(steps) if "red_until" in s.get("name", ""))
    assert any(suites < i < red_until for i in _floor_steps(steps)), _floor_steps(steps)


@then(
    parsers.parse(
        "each check is the backend floor test for the {size} MB clip from {writers:d} "
        "parallel writers"
    )
)
def floor_shape(steps: list[dict[str, Any]], size: str, writers: int) -> None:
    for i in _floor_steps(steps):
        step = steps[i]
        assert step.get("working-directory") == "backend", step
        assert isinstance(step.get("timeout-minutes"), int), step
        assert 0 < step["timeout-minutes"] <= 3, step
        assert "-n " not in step["run"], "the floor runs alone, not beside the suites"
    test = (REPO_ROOT / "backend" / FLOOR_TEST).read_text()
    assert f"WRITERS = {writers}" in test
    assert "SYNTHETIC_CLIP" in test
    assert f"{CLIP_BYTES:_}" in test, size


@then("the job records the runner facts once the services run")
def facts_step(steps: list[dict[str, Any]]) -> None:
    facts = _first(steps, "objectstore_telemetry.sh facts")
    services = _first(steps, "up -d --wait postgres objectstore")
    suites = _first(steps, "run_with_budget.py")
    # once the services run: the published port path only exists then
    assert services < facts < suites, (services, facts, suites)
    assert "reports/telemetry/" in steps[facts]["run"]


@then("the job samples the store during the suites and the red_until rows")
def watch_step(steps: list[dict[str, Any]]) -> None:
    watch = _first(steps, "objectstore_telemetry.sh watch")
    suites = _first(steps, "run_with_budget.py")
    assert watch < suites
    run = steps[watch]["run"]
    assert "reports/telemetry/" in run
    assert re.search(r"watch \S+ \d+", run), run
    assert "&" in run, "the watcher runs in the background"


@then("the job keeps the whole object store log and the telemetry on every run")
def kept_always(steps: list[dict[str, Any]]) -> None:
    keep = next(
        i
        for i, s in enumerate(steps)
        if "logs --no-color objectstore > reports/objectstore.log" in s.get("run", "")
        and s.get("if") == "always()"
    )
    upload = next(i for i, s in enumerate(steps) if s.get("with", {}).get("name") == "integration-reports")
    assert keep < upload
    assert steps[upload]["with"]["path"] == "reports/"
    assert steps[upload].get("if") == "always()"
    assert "--tail" not in steps[keep]["run"]


# ---------------------------------------------------------------- the telemetry script
class _FakeS3(BaseHTTPRequestHandler):
    """Stands in for the store: takes any PUT/DELETE and remembers the body sizes."""

    sizes: list[int] = []

    def do_PUT(self) -> None:  # noqa: N802 (http.server API)
        length = int(self.headers.get("Content-Length", "0"))
        self.sizes.append(len(self.rfile.read(length)))
        self.send_response(200)
        self.end_headers()

    def do_DELETE(self) -> None:  # noqa: N802
        self.send_response(204)
        self.end_headers()

    def log_message(self, *args: object) -> None:
        pass


@pytest.fixture
def fake_store() -> Iterator[str]:
    _FakeS3.sizes = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeS3)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()


@given("the runner telemetry script", target_fixture="telemetry")
def telemetry(tmp_path: Path, fake_store: str) -> dict[str, Any]:
    assert SCRIPT.is_file(), SCRIPT
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "S3_ENDPOINT_URL": fake_store,
        "S3_ACCESS_KEY_ID": "k",
        "S3_SECRET_ACCESS_KEY": "s",
        "S3_REGION": "us-east-1",
        "S3_BUCKET_MEDIA": "b",
    }
    return {"env": env, "out": tmp_path / "telemetry" / "out.txt"}


def _run(telemetry: dict[str, Any], mode: str) -> str:
    res = subprocess.run(
        ["bash", str(SCRIPT), mode, str(telemetry["out"])],
        env=telemetry["env"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    return telemetry["out"].read_text()


@when("it records the runner facts", target_fixture="text")
def facts(telemetry: dict[str, Any]) -> str:
    return _run(telemetry, "facts")


@when("it takes one sample of a running store", target_fixture="text")
def sample(telemetry: dict[str, Any]) -> str:
    return _run(telemetry, "sample")


SECTIONS = {
    "the Docker daemon settings and the store's published port path": [
        "## docker daemon",
        "## published port path",
    ],
    "the conntrack settings and the firewall rules for invalid packets": [
        "## conntrack settings",
        "## invalid-packet rules",
    ],
    "the free disk, the memory and the kernel": ["## disk", "## memory", "## kernel"],
}


@then(parsers.parse("the facts name {what}"))
def facts_name(text: str, what: str) -> None:
    for header in SECTIONS[what]:
        assert re.search(rf"^{re.escape(header)}$", text, re.M), (header, text[:2000])


@then(parsers.parse("the sample times one {size} MB write to the store"))
def sample_write(text: str, size: str) -> None:
    assert _FakeS3.sizes == [CLIP_BYTES], _FakeS3.sizes
    line = re.search(r"^write bytes=(\d+) seconds=([0-9.]+) MBps=([0-9.]+) http=200$", text, re.M)
    assert line is not None, text
    assert int(line.group(1)) == CLIP_BYTES, size


@then("the sample holds the TCP retransmission and timeout counters")
def sample_tcp(text: str) -> None:
    assert re.search(r"^## tcp counters$", text, re.M), text
    assert re.search(r"RetransSegs", text), text
    assert re.search(r"TCPTimeouts", text), text


@then("the sample holds the conntrack statistics and the store's sockets")
def sample_ct(text: str) -> None:
    assert re.search(r"^## conntrack stats$", text, re.M), text
    assert re.search(r"^## store sockets$", text, re.M), text
    assert re.search(r"^# sample \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", text, re.M), text


def test_a_failed_write_is_recorded_not_fatal(tmp_path: Path) -> None:
    """A store that refuses the write must not stop the watcher: the sample says so."""
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(tmp_path),
        "S3_ENDPOINT_URL": "http://127.0.0.1:9",  # discard port: connection refused
        "S3_ACCESS_KEY_ID": "k",
        "S3_SECRET_ACCESS_KEY": "s",
        "S3_REGION": "us-east-1",
        "S3_BUCKET_MEDIA": "b",
    }
    out = tmp_path / "s.txt"
    res = subprocess.run(
        ["bash", str(SCRIPT), "sample", str(out)],
        env=env,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert re.search(r"^write bytes=1724207 .* http=000$", out.read_text(), re.M), out.read_text()


def test_an_unknown_mode_is_refused(tmp_path: Path) -> None:
    res = subprocess.run(
        ["bash", str(SCRIPT), "nonsense", str(tmp_path / "x")],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert res.returncode == 2
    assert "usage" in res.stderr
