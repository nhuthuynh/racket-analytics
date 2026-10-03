"""Helpers to run the worker as a real OS process and to observe jobs (ST-007)."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

from sqlalchemy.orm import Session

from tests.support import contract
from tests.support.paths import BACKEND

T = TypeVar("T")


def wait_for(predicate: Callable[[], T], timeout: float, interval: float = 0.1) -> T:
    """Poll ``predicate`` until it returns a truthy value or ``timeout`` seconds pass."""
    deadline = time.monotonic() + timeout
    while True:
        value = predicate()
        if value:
            return value
        if time.monotonic() >= deadline:
            raise TimeoutError(f"condition not met within {timeout} s")
        time.sleep(interval)


@contextmanager
def worker_process(**env: str) -> Iterator[subprocess.Popen[bytes]]:
    """``python -m racket.worker`` with APP_ENV=test and extra environment variables."""
    full_env = {**os.environ, "APP_ENV": "test", **env}
    proc = subprocess.Popen(
        [sys.executable, "-m", contract.WORKER_MODULE],
        cwd=BACKEND,
        env=full_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        yield proc
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGKILL)
        proc.wait(timeout=10)


def jobs_for_match(engine: Any, match_id: str) -> list[Any]:
    queue_cls = contract.JOB_QUEUE.load()
    with Session(engine) as session:
        return list(queue_cls(session).for_match(match_id))


def probe_job(engine: Any, match_id: str) -> Any:
    """The single probe job of a match, or None."""
    jobs = [j for j in jobs_for_match(engine, match_id) if j.key.stage == contract.PROBE_STAGE_NAME]
    assert len(jobs) <= 1, f"duplicate probe jobs for one key: {jobs}"
    return jobs[0] if jobs else None


def media_facts_count(engine: Any, match_id: str) -> int:
    with Session(engine) as session:
        return int(contract.COUNT_MEDIA_FACTS.load()(session, match_id))
