"""``JobQueue.enqueue_again`` (ST-018): after a refused video, a new upload for the same match
must be probed again, although the probe job key ``(match, pipeline, stage)`` is unique."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from racket.analysis_jobs.domain import JobKey, JobStatus
from racket.analysis_jobs.queue import JobQueue

pytestmark = pytest.mark.integration


def _key() -> JobKey:
    return JobKey(uuid.uuid4(), "v0", "probe")


@pytest.mark.parametrize("finish", ["complete", "fail"])
def test_a_finished_job_is_queued_again_as_a_fresh_first_attempt(
    db_session: Any, finish: str
) -> None:
    queue = JobQueue(db_session)
    key = _key()
    first = queue.enqueue(key)
    job = queue.claim("w-1")
    assert job is not None
    if finish == "complete":
        job.complete()
    else:
        job.fail("probe_failed")
    db_session.flush()

    again = queue.enqueue_again(key)

    assert again == first
    job = queue.get(again)
    assert (job.status, job.attempts, job.failure_reason) == (JobStatus.QUEUED, 1, None)


def test_a_queued_or_running_job_is_left_alone(db_session: Any) -> None:
    queue = JobQueue(db_session)
    key = _key()
    first = queue.enqueue(key)
    running = queue.claim("w-1")
    assert running is not None
    assert queue.enqueue_again(key) == first
    assert queue.get(first).status is JobStatus.RUNNING
    assert queue.get(first).worker_id == "w-1"


def test_a_new_key_is_simply_enqueued(db_session: Any) -> None:
    queue = JobQueue(db_session)
    job_id = queue.enqueue_again(_key())
    assert queue.get(job_id).status is JobStatus.QUEUED
