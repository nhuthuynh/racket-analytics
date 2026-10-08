"""Binds tests/features/purge_schedule.feature (SRE-PURGE-a; NFR-066 c, NFR-047; ADR 0038).

The scheduler runs as PID 1 of a real container: the Python base image of
``infra/docker/backend.Dockerfile`` (through ``DOCKERHUB_REGISTRY``), the script mounted where
the API image copies it (``/opt/racket/purge_schedule.py``), read-only root, ``/tmp`` tmpfs, all
capabilities dropped, unprivileged user. That is the API image's runtime contract without the
backend, which the job (ST-050) needs and the scheduler does not. ``docker stop`` delivers the
SIGTERM, as Compose will in slice (b).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import uuid
from collections.abc import Iterator
from datetime import datetime
from typing import Any

import pytest
from conftest import REPO_ROOT
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]
scenarios("purge_schedule.feature")

SCHEDULER = REPO_ROOT / "infra" / "docker" / "purge_schedule.py"
DOCKERFILE = REPO_ROOT / "infra" / "docker" / "backend.Dockerfile"
IN_IMAGE = "/opt/racket/purge_schedule.py"


def _python_image() -> str:
    match = re.search(r"^ARG PYTHON_IMAGE=python:([\w.\-]+)$", DOCKERFILE.read_text(), re.M)
    assert match, "backend.Dockerfile pins its Python base image"
    registry = os.environ.get("DOCKERHUB_REGISTRY", "docker.io")
    return f"{registry}/library/python:{match.group(1)}"


def _docker_ok() -> bool:
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


def _docker(*args: str, timeout: float = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=timeout, check=False
    )


@pytest.fixture
def world() -> Iterator[dict[str, Any]]:
    if not _docker_ok():
        pytest.skip("docker not available (the infra CI job runs this on ubuntu-24.04)")
    state: dict[str, Any] = {"name": f"ra-purge-test-{uuid.uuid4().hex[:8]}", "env": {}}
    yield state
    _docker("rm", "-f", state["name"])


def _logs(world: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], str]:
    res = _docker("logs", world["name"])
    records = [json.loads(ln) for ln in res.stdout.splitlines() if ln.startswith("{")]
    plain = [ln for ln in res.stdout.splitlines() if not ln.startswith("{")]
    return records, plain, res.stderr


def _wait_for(predicate, timeout: float = 30.0) -> bool:  # type: ignore[no-untyped-def]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.2)
    return False


def _runs(world: dict[str, Any]) -> list[dict[str, Any]]:
    return [r for r in _logs(world)[0] if r.get("event") == "purge.run"]


def _state(world: dict[str, Any]) -> dict[str, Any]:
    res = _docker("inspect", "--format", "{{json .State}}", world["name"])
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


# ---------------------------------------------------------------- given
@given(parsers.parse("the purge schedule is set to every {seconds:d} seconds"))
def interval(world: dict[str, Any], seconds: int) -> None:
    world["env"]["PURGE_INTERVAL_S"] = str(seconds)
    world["env"]["PURGE_TICK_S"] = "1"


@given(parsers.parse("the heartbeat tick is {seconds:d} seconds"))
def tick(world: dict[str, Any], seconds: int) -> None:
    world["env"]["PURGE_TICK_S"] = str(seconds)


@given(parsers.parse('a purge job that prints "{text}" and fails with exit code {rc:d}'))
def failing_job(world: dict[str, Any], text: str, rc: int) -> None:
    world["job"] = ["sh", "-c", f"echo {text}; exit {rc}"]


@given(parsers.parse('a purge job that prints "{text}"'))
def printing_job(world: dict[str, Any], text: str) -> None:
    world["job"] = ["sh", "-c", f"echo {text}"]


@given("a purge job that runs until it is told to stop")
def long_job(world: dict[str, Any]) -> None:
    world["job"] = [
        "sh",
        "-c",
        "trap 'echo job-got-term; exit 143' TERM; echo job-started; while :; do sleep 0.1; done",
    ]


# ---------------------------------------------------------------- when
@when("the purge schedule starts in a container")
def start(world: dict[str, Any]) -> None:
    env_args = [a for k, v in world["env"].items() for a in ("-e", f"{k}={v}")]
    res = _docker(
        "run", "-d", "--name", world["name"],
        "--read-only", "--tmpfs", "/tmp", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--user", "65534:65534",
        "-v", f"{SCHEDULER}:{IN_IMAGE}:ro",
        *env_args,
        _python_image(), "python", IN_IMAGE, *world["job"],
        timeout=300,
    )  # fmt: skip
    assert res.returncode == 0, res.stderr


@when("the container is stopped while the job is running")
def stop_container(world: dict[str, Any]) -> None:
    assert _wait_for(lambda: "job-started" in _logs(world)[1]), _logs(world)
    t0 = time.monotonic()
    res = _docker("stop", "-t", "30", world["name"])
    world["stop_s"] = time.monotonic() - t0
    assert res.returncode == 0, res.stderr


@when("the container is stopped after the first run has finished")
def stop_between_runs(world: dict[str, Any]) -> None:
    assert _wait_for(lambda: len(_runs(world)) >= 1), _logs(world)
    time.sleep(0.5)  # the scheduler is now waiting for the next run
    assert _state(world)["Running"], _logs(world)
    t0 = time.monotonic()
    res = _docker("stop", "-t", "30", world["name"])
    world["stop_s"] = time.monotonic() - t0
    assert res.returncode == 0, res.stderr


# ---------------------------------------------------------------- then
@then(parsers.parse('the container exits with code {rc:d} naming "{name}"'))
def exits_naming(world: dict[str, Any], rc: int, name: str) -> None:
    assert _wait_for(lambda: not _state(world)["Running"]), "the refused schedule kept running"
    assert _state(world)["ExitCode"] == rc
    assert name in _logs(world)[2]


@then("the purge job never ran")
def never_ran(world: dict[str, Any]) -> None:
    records, plain, _ = _logs(world)
    assert "job-ran" not in plain
    assert not [r for r in records if r.get("event") == "purge.run"]


@then(
    parsers.parse(
        'at least {count:d} runs are logged as JSON lines with status "{status}" at level "{level}"'
    )
)
def runs_logged(world: dict[str, Any], count: int, status: str, level: str) -> None:
    assert _wait_for(lambda: len(_runs(world)) >= count), _logs(world)
    runs = _runs(world)
    assert all(r["status"] == status and r["level"] == level for r in runs), runs
    assert all(r["logger"] == "racket.purge.schedule" and r["ts"].endswith("Z") for r in runs)
    assert _logs(world)[1].count("job-ran") >= count, "the job's own output did not pass through"


@then(parsers.parse("the consecutive failures of the first two runs are {a:d} and {b:d}"))
def consecutive(world: dict[str, Any], a: int, b: int) -> None:
    assert [r["consecutive_failures"] for r in _runs(world)[:2]] == [a, b]


@then("the container is still running with a fresh heartbeat")
def alive(world: dict[str, Any]) -> None:
    assert _state(world)["Running"], _logs(world)
    age = _docker(
        "exec", world["name"], "python", "-c",
        "import os, time; print(time.time() - os.path.getmtime('/tmp/purge-heartbeat'))",
    )  # fmt: skip
    assert age.returncode == 0, age.stderr
    assert float(age.stdout) < 10


@then(parsers.parse("the container exits with code {rc:d} within {seconds:d} seconds"))
def exits_within(world: dict[str, Any], rc: int, seconds: int) -> None:
    assert world["stop_s"] < seconds, world["stop_s"]
    assert _state(world)["ExitCode"] == rc, _logs(world)


@then("the purge job received SIGTERM")
def job_got_term(world: dict[str, Any]) -> None:
    assert "job-got-term" in _logs(world)[1], _logs(world)


@then(parsers.parse('the last log line is "{event}"'))
def last_line(world: dict[str, Any], event: str) -> None:
    records = _logs(world)[0]
    assert records, "no JSON log lines"
    assert records[-1]["event"] == event, records


def _ts(record: dict[str, Any]) -> datetime:
    return datetime.fromisoformat(record["ts"].replace("Z", "+00:00"))


@then(
    parsers.parse(
        'the first run is logged with status "{status}" at level "{level}" '
        "announcing the next run in {seconds:d} seconds"
    )
)
def first_run(world: dict[str, Any], status: str, level: str, seconds: int) -> None:
    assert _wait_for(lambda: len(_runs(world)) >= 1), _logs(world)
    run = _runs(world)[0]
    assert (run["run"], run["status"], run["level"], run["exit_code"]) == (1, status, level, 0)
    assert run["next_run_in_s"] == seconds
    assert run["consecutive_failures"] == 0


@then(
    parsers.parse(
        "the second run is logged between {low:d} and {high:d} seconds after the first, "
        'also with status "{status}"'
    )
)
def second_run(world: dict[str, Any], low: int, high: int, status: str) -> None:
    assert _wait_for(lambda: len(_runs(world)) >= 2, timeout=high + 10), _logs(world)
    first, second = _runs(world)[:2]
    gap = (_ts(second) - _ts(first)).total_seconds()
    assert low - 0.5 <= gap <= high, (gap, first, second)
    assert second["run"] == 2
    assert second["status"] == status


@then(parsers.parse('the job\'s own output "{text}" passed through for each run'))
def output_passed_through(world: dict[str, Any], text: str) -> None:
    _, plain, _ = _logs(world)
    assert plain.count(text) >= len(_runs(world)) >= 2, plain
