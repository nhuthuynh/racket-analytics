"""Mandatory regression suite: worker crash (IT-00-04; testing-strategy §5; NFR-046;
AQS/OPS-02 disposability). Never deleted.

The worker is a real OS process. SIGTERM must hand the in-flight job back within 10 s
(NFR-046b); SIGKILL (sudden death) must not lose the job either. Re-runs leave no duplicate rows.
"""

from __future__ import annotations

import signal
import time
from collections.abc import Iterator
from contextlib import ExitStack
from typing import Any

import pytest

from tests.support import contract
from tests.support.api import ApiDriver
from tests.support.flows import create_match, upload_fixture
from tests.support.worker import media_facts_count, probe_job, wait_for, worker_process

pytestmark = [pytest.mark.red_until(story="ST-007"), pytest.mark.slow]

SLOW_PROBE = {contract.FAULT_INJECTION_ENV: "probe:sleep=60"}


@pytest.fixture
def stack() -> Iterator[ExitStack]:
    with ExitStack() as s:
        yield s


@pytest.fixture
def uploaded_match(api: ApiDriver) -> str:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "Crash test"))
    api.run(upload_fixture(ivy, match_id))
    return match_id


def _running(db: Any, match_id: str) -> Any:
    return wait_for(
        lambda: (j := probe_job(db, match_id)) and j.status == "running" and j, timeout=20
    )


def test_sigterm_requeues_within_10s_and_rerun_leaves_one_row(
    committed_db: Any, uploaded_match: str, stack: ExitStack
) -> None:
    proc = stack.enter_context(worker_process(**SLOW_PROBE))
    before = _running(committed_db, uploaded_match)

    t0 = time.monotonic()
    proc.send_signal(signal.SIGTERM)
    requeued = wait_for(
        lambda: (j := probe_job(committed_db, uploaded_match)) and j.status == "queued" and j,
        timeout=10,
    )

    assert time.monotonic() - t0 <= 10
    assert requeued.attempts == before.attempts + 1
    assert proc.wait(timeout=10) == 0, "worker should exit cleanly on SIGTERM"
    contract.WORKER_RUN_UNTIL_IDLE.load()()
    assert probe_job(committed_db, uploaded_match).status == "done"
    assert media_facts_count(committed_db, uploaded_match) == 1


def test_sigkill_mid_stage_does_not_lose_the_job(
    committed_db: Any, uploaded_match: str, stack: ExitStack
) -> None:
    proc = stack.enter_context(worker_process(**SLOW_PROBE))
    _running(committed_db, uploaded_match)

    proc.send_signal(signal.SIGKILL)
    proc.wait(timeout=10)
    # a fresh worker (no fault injection) must be able to pick the job up again
    stack.enter_context(worker_process())
    done = wait_for(
        lambda: (j := probe_job(committed_db, uploaded_match)) and j.status == "done" and j,
        timeout=60,
    )

    assert done.attempts >= 2
    assert media_facts_count(committed_db, uploaded_match) == 1


def test_two_workers_never_run_the_same_job_twice(
    committed_db: Any, uploaded_match: str, stack: ExitStack
) -> None:
    stack.enter_context(worker_process())
    stack.enter_context(worker_process())

    wait_for(
        lambda: (j := probe_job(committed_db, uploaded_match)) and j.status == "done" and j,
        timeout=60,
    )

    assert media_facts_count(committed_db, uploaded_match) == 1
    assert probe_job(committed_db, uploaded_match).attempts == 1
