"""Run the purge/expiry job on a schedule (SRE-PURGE; NFR-066 c, NFR-047; ADR 0038 Proposed).

Usage (the Compose ``purge`` service):
    python /opt/racket/purge_schedule.py python -m racket.platform.purge --once

* Runs the command once at start, then every ``PURGE_INTERVAL_S`` seconds (default 86400).
  An interval that is not a whole number from 1 to 86400 is refused (exit 2): NFR-066 (c)
  asks for at least one purge a day.
* One JSON line per run on stdout (``event`` ``purge.run``, ``status`` ok/failed, exit code,
  duration, consecutive failures). A failed run, or a job that cannot start, is logged at ERROR
  and the schedule keeps going; Compose restarts the scheduler only if it dies.
* The job's own output passes through unchanged and is never copied into these records; nor
  are its arguments (only the program name is logged), since an argument could carry a secret.
* ``PURGE_HEARTBEAT_FILE`` (default ``/tmp/purge-heartbeat``) is touched every
  ``PURGE_TICK_S`` seconds (default 10), also while a run is in progress, for the healthcheck.
* SIGTERM/SIGINT: an in-flight job gets SIGTERM and is waited for; then the scheduler exits 0.

Standard library only: it ships in the API image next to the backend, not inside it.
"""

from __future__ import annotations

import contextlib
import json
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

MAX_INTERVAL_S = 86400
LOGGER = "racket.purge.schedule"
USAGE = "usage: purge_schedule.py <command> [args...]"


class Refused(Exception):
    pass


def log(level: str, event: str, msg: str, **fields: Any) -> None:
    record = {
        "ts": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "level": level,
        "logger": LOGGER,
        "msg": msg,
        "event": event,
        **fields,
    }
    print(json.dumps(record), flush=True)


def whole_seconds(name: str, default: int, maximum: int) -> int:
    raw = os.environ.get(name, str(default))
    if not raw.isdigit() or not 1 <= int(raw) <= maximum:
        raise Refused(f"{name} must be a whole number of seconds from 1 to {maximum}, got {raw!r}")
    return int(raw)


class Scheduler:
    def __init__(self, cmd: list[str], interval: int, tick: int, heartbeat: Path) -> None:
        self.cmd = cmd
        self.interval = interval
        self.tick = tick
        self.heartbeat = heartbeat
        self.stopping = False
        self.child: subprocess.Popen[bytes] | None = None

    def on_signal(self, signum: int, _frame: object) -> None:
        self.stopping = True
        if self.child is not None and self.child.poll() is None:
            self.child.send_signal(signal.SIGTERM)

    def beat(self) -> None:
        # A missing heartbeat shows up in the healthcheck, not as a crash.
        with contextlib.suppress(OSError):
            self.heartbeat.touch()

    def run_once(self) -> int:
        try:
            # Fixed argv from the compose file, no shell; output goes straight to our stdout.
            self.child = subprocess.Popen(self.cmd)  # noqa: S603
        except OSError as exc:
            log(
                "ERROR",
                "purge.job.not_started",
                "the purge job could not start",
                exc_type=type(exc).__name__,
            )
            return 127
        while True:
            self.beat()
            try:
                return self.child.wait(timeout=min(self.tick, 1))
            except subprocess.TimeoutExpired:
                continue

    def sleep_until(self, due: float) -> None:
        while not self.stopping:
            left = due - time.monotonic()
            if left <= 0:
                return
            self.beat()
            time.sleep(min(self.tick, left))

    def loop(self) -> None:
        log(
            "INFO",
            "purge.schedule.started",
            "purge schedule started",
            interval_s=self.interval,
            program=Path(self.cmd[0]).name,
        )
        run, failures = 0, 0
        while not self.stopping:
            run += 1
            started = time.monotonic()
            rc = self.run_once()
            self.child = None
            ok = rc == 0
            failures = 0 if ok else failures + 1
            log(
                "INFO" if ok else "ERROR",
                "purge.run",
                "purge run finished" if ok else "purge run failed",
                run=run,
                status="ok" if ok else "failed",
                exit_code=rc,
                duration_ms=round((time.monotonic() - started) * 1000),
                consecutive_failures=failures,
                next_run_in_s=self.interval,
            )
            self.sleep_until(started + self.interval)
        log("INFO", "purge.schedule.stopped", "purge schedule stopped", runs=run)


def main(argv: list[str]) -> int:
    cmd = argv[1:]
    if cmd[:1] == ["--"]:
        cmd = cmd[1:]
    if not cmd:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        interval = whole_seconds("PURGE_INTERVAL_S", MAX_INTERVAL_S, MAX_INTERVAL_S)
        tick = whole_seconds("PURGE_TICK_S", 10, 300)
    except Refused as exc:
        print(f"purge_schedule: refused: {exc}", file=sys.stderr)
        return 2
    # /tmp is the container's private tmpfs (read-only root filesystem).
    heartbeat = Path(os.environ.get("PURGE_HEARTBEAT_FILE", "/tmp/purge-heartbeat"))  # noqa: S108
    sched = Scheduler(cmd, interval, tick, heartbeat)
    signal.signal(signal.SIGTERM, sched.on_signal)
    signal.signal(signal.SIGINT, sched.on_signal)
    sched.loop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
