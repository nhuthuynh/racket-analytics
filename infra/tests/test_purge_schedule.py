"""SRE-PURGE slice (a) (NFR-066 c, NFR-047; ADR 0038 Proposed): the scheduler that runs the
purge/expiry job at least daily. Slice (b), the Compose ``purge`` service that runs it, follows
once QA decides the test-change row for the built-services inventory
(docs/sprints/03/decisions/SRE-PURGE-a.md).

The scheduler is ``infra/docker/purge_schedule.py`` (standard library only, shipped in the API
image). It runs the job's command, writes one JSON log line per run to stdout, survives a failed
run, keeps a heartbeat for the Compose healthcheck and stops cleanly on SIGTERM. The job itself
(``python -m racket.platform.purge --once``) belongs to ST-050 and PE-3; these tests stand in a
small command for it. Negative cases first.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from conftest import REPO_ROOT

SCHEDULER = REPO_ROOT / "infra" / "docker" / "purge_schedule.py"
DOCKERFILE = REPO_ROOT / "infra" / "docker" / "backend.Dockerfile"
DAY_S = 86400


def env_for(tmp_path: Path, **extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("PURGE_")}
    env["PURGE_HEARTBEAT_FILE"] = str(tmp_path / "heartbeat")
    env.update(extra)
    return env


def run_scheduler(
    tmp_path: Path, cmd: list[str], timeout: float = 10, **extra: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCHEDULER), *cmd],
        capture_output=True,
        text=True,
        env=env_for(tmp_path, **extra),
        timeout=timeout,
        check=False,
    )


def start_scheduler(tmp_path: Path, cmd: list[str], **extra: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, str(SCHEDULER), *cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env_for(tmp_path, **extra),
    )


def wait_for(predicate, timeout: float = 10.0) -> bool:  # type: ignore[no-untyped-def]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def stop(proc: subprocess.Popen[str]) -> tuple[int, list[dict], str]:
    proc.send_signal(signal.SIGTERM)
    out, err = proc.communicate(timeout=5)
    return proc.returncode, [json.loads(ln) for ln in out.splitlines() if ln.strip()], err


def counter_cmd(path: Path, rc: int = 0) -> list[str]:
    return ["sh", "-c", f'echo run >> "{path}"; exit {rc}']


def lines(path: Path) -> int:
    return len(path.read_text().splitlines()) if path.exists() else 0


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
@pytest.mark.parametrize("value", [str(DAY_S + 1), "172800", "0", "-5", "abc", "1.5", ""])
def test_an_interval_longer_than_a_day_or_not_a_positive_integer_is_refused(
    tmp_path: Path, value: str
) -> None:
    ran = tmp_path / "ran"
    res = run_scheduler(tmp_path, counter_cmd(ran), PURGE_INTERVAL_S=value)
    assert res.returncode == 2, (res.stdout, res.stderr)
    assert "PURGE_INTERVAL_S" in res.stderr
    assert not ran.exists(), "the job must not run under a refused schedule"


@pytest.mark.unit
def test_no_command_is_a_usage_error(tmp_path: Path) -> None:
    res = run_scheduler(tmp_path, [])
    assert res.returncode == 2
    assert "usage" in res.stderr.lower()


@pytest.mark.unit
def test_a_failed_run_is_logged_as_an_error_and_the_schedule_keeps_going(tmp_path: Path) -> None:
    ran = tmp_path / "ran"
    proc = start_scheduler(tmp_path, counter_cmd(ran, rc=3), PURGE_INTERVAL_S="1", PURGE_TICK_S="1")
    try:
        assert wait_for(lambda: lines(ran) >= 2), "the scheduler stopped after a failed run"
    finally:
        rc, logs, err = stop(proc)
    assert rc == 0, err
    runs = [r for r in logs if r.get("event") == "purge.run"]
    assert len(runs) >= 2
    assert all(r["status"] == "failed" and r["exit_code"] == 3 for r in runs)
    assert all(r["level"] == "ERROR" for r in runs)
    assert [r["consecutive_failures"] for r in runs[:2]] == [1, 2]


@pytest.mark.unit
def test_a_job_that_cannot_start_is_a_failed_run_not_a_crash(tmp_path: Path) -> None:
    proc = start_scheduler(
        tmp_path, [str(tmp_path / "no-such-job")], PURGE_INTERVAL_S="1", PURGE_TICK_S="1"
    )
    try:
        assert wait_for(lambda: proc.poll() is not None or (tmp_path / "heartbeat").exists())
        time.sleep(1.5)
        assert proc.poll() is None, "the scheduler exited when the job could not start"
    finally:
        rc, logs, err = stop(proc)
    runs = [r for r in logs if r.get("event") == "purge.run"]
    assert runs, (logs, err)
    assert runs[0]["status"] == "failed"
    assert rc == 0


@pytest.mark.unit
def test_sigterm_during_a_run_is_passed_to_the_job_and_the_scheduler_exits_promptly(
    tmp_path: Path,
) -> None:
    started, got_term = tmp_path / "started", tmp_path / "got-term"
    job = [
        "sh",
        "-c",
        f'trap \'echo x > "{got_term}"; exit 143\' TERM; echo x > "{started}"; '
        "while :; do sleep 0.1; done",
    ]
    proc = start_scheduler(tmp_path, job, PURGE_INTERVAL_S="60", PURGE_TICK_S="1")
    assert wait_for(started.exists)
    t0 = time.monotonic()
    rc, logs, err = stop(proc)
    assert time.monotonic() - t0 < 5
    assert rc == 0, err
    assert got_term.exists(), "the in-flight job did not receive SIGTERM"
    assert logs[-1]["event"] == "purge.schedule.stopped"


@pytest.mark.unit
def test_logs_carry_no_command_output(tmp_path: Path) -> None:
    # The job's own stdout passes through untouched; the scheduler never embeds it in its
    # records (a job line could carry an id or a key, NFR-069).
    ran = tmp_path / "ran"
    job = ["sh", "-c", f'echo secret-looking-output; echo run >> "{ran}"']
    proc = start_scheduler(tmp_path, job, PURGE_INTERVAL_S="60", PURGE_TICK_S="1")
    try:
        assert wait_for(lambda: lines(ran) >= 1)
        time.sleep(0.3)
    finally:
        proc.send_signal(signal.SIGTERM)
        out, _ = proc.communicate(timeout=5)
    records = [json.loads(ln) for ln in out.splitlines() if ln.startswith("{")]
    assert all("secret-looking-output" not in json.dumps(r) for r in records)


@pytest.mark.unit
def test_the_job_runs_at_start_and_again_every_interval(tmp_path: Path) -> None:
    ran = tmp_path / "ran"
    proc = start_scheduler(tmp_path, counter_cmd(ran), PURGE_INTERVAL_S="1", PURGE_TICK_S="1")
    try:
        assert wait_for(lambda: lines(ran) >= 1, timeout=3), "no run at start"
        assert wait_for(lambda: lines(ran) >= 3, timeout=6), "no repeat every interval"
    finally:
        rc, logs, err = stop(proc)
    assert rc == 0, err
    start = logs[0]
    assert start["event"] == "purge.schedule.started"
    assert start["interval_s"] == 1
    runs = [r for r in logs if r.get("event") == "purge.run"]
    assert runs[0]["status"] == "ok"
    assert runs[0]["exit_code"] == 0
    assert runs[0]["level"] == "INFO"
    assert runs[0]["consecutive_failures"] == 0
    for r in runs:
        assert {"ts", "logger", "msg", "run", "duration_ms", "next_run_in_s"} <= r.keys()
        assert r["ts"].endswith("Z")


@pytest.mark.unit
def test_default_interval_is_one_day(tmp_path: Path) -> None:
    ran = tmp_path / "ran"
    proc = start_scheduler(tmp_path, counter_cmd(ran), PURGE_TICK_S="1")
    try:
        assert wait_for(lambda: lines(ran) >= 1)
    finally:
        _, logs, _ = stop(proc)
    assert logs[0]["interval_s"] == DAY_S


@pytest.mark.unit
def test_the_heartbeat_is_kept_fresh_between_runs(tmp_path: Path) -> None:
    beat = tmp_path / "heartbeat"
    ran = tmp_path / "ran"
    proc = start_scheduler(tmp_path, counter_cmd(ran), PURGE_INTERVAL_S="60", PURGE_TICK_S="1")
    try:
        assert wait_for(lambda: lines(ran) >= 1)
        assert wait_for(beat.exists)
        first = beat.stat().st_mtime
        assert wait_for(lambda: beat.stat().st_mtime > first, timeout=4)
    finally:
        stop(proc)


@pytest.mark.unit
def test_the_api_image_ships_the_scheduler() -> None:
    text = DOCKERFILE.read_text()
    api_stage = text.split("FROM base AS api", 1)[1].split("\nFROM ", 1)[0]
    assert "COPY infra/docker/purge_schedule.py /opt/racket/purge_schedule.py" in api_stage
