"""JobKey and the Job state machine (ST-007; sprint-00 §5 TDD plan, in order; AQS/OPS-02)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from racket.analysis_jobs.domain import InvalidJobTransition, Job, JobKey, JobStatus

MATCH = uuid.uuid4()
NOW = datetime(2026, 10, 5, 9, 0, tzinfo=UTC)


def key(stage: str = "probe", match_id: uuid.UUID = MATCH) -> JobKey:
    return JobKey(match_id=match_id, pipeline_version="v0", stage=stage)


def running_job() -> Job:
    job = Job.queued(key())
    job.start(worker_id="w1", lease_until=NOW + timedelta(seconds=15))
    return job


# ---------------------------------------------------------------- JobKey
# 1. two keys with the same (match_id, pipeline_version, stage) are equal
def test_same_triple_is_the_same_key() -> None:
    same = JobKey(match_id=str(MATCH), pipeline_version="v0", stage="probe")  # type: ignore[arg-type]

    assert key() == same
    assert hash(key()) == hash(key())


# 2. a different stage gives a different key
def test_different_stage_is_a_different_key() -> None:
    assert key("probe") != key("normalise")
    assert key() != key(match_id=uuid.uuid4())


@pytest.mark.parametrize("stage", ["", "Probe", "probe;drop", "x" * 65])
def test_stage_name_must_be_a_short_identifier(stage: str) -> None:
    with pytest.raises(ValueError, match="stage"):
        key(stage)


# ---------------------------------------------------------------- Job state machine
def test_new_job_is_queued_on_its_first_attempt() -> None:
    job = Job.queued(key())

    assert job.status == "queued"
    assert job.status is JobStatus.QUEUED
    assert job.attempts == 1
    assert job.failure_reason is None


# 1. complete from queued fails (must be running)
def test_complete_from_queued_fails() -> None:
    job = Job.queued(key())

    with pytest.raises(InvalidJobTransition):
        job.complete()

    assert job.status is JobStatus.QUEUED


# 2. fail from running -> failed with reason
def test_fail_from_running_records_the_reason() -> None:
    job = running_job()

    job.fail("probe_failed")

    assert job.status is JobStatus.FAILED
    assert job.failure_reason == "probe_failed"
    assert job.worker_id is None


def test_failure_reason_must_be_a_code_not_an_exception_text() -> None:
    job = running_job()

    with pytest.raises(ValueError, match="reason"):
        job.fail("RuntimeError: SELECT * FROM jobs password=hunter2")

    assert job.status is JobStatus.RUNNING


# 3. requeue from running -> queued with attempt + 1
def test_requeue_from_running_increments_the_attempt() -> None:
    job = running_job()

    job.requeue()

    assert job.status is JobStatus.QUEUED
    assert job.attempts == 2
    assert job.worker_id is None
    assert job.lease_expires_at is None


def test_requeue_from_queued_fails() -> None:
    with pytest.raises(InvalidJobTransition):
        Job.queued(key()).requeue()


# 4. complete twice is idempotent
def test_complete_twice_is_idempotent() -> None:
    job = running_job()

    job.complete()
    job.complete()

    assert job.status is JobStatus.DONE
    assert job.attempts == 1


def test_start_needs_a_queued_job() -> None:
    job = running_job()

    with pytest.raises(InvalidJobTransition):
        job.start(worker_id="w2", lease_until=NOW)


def test_lease_expiry_is_judged_against_a_given_clock() -> None:
    job = running_job()

    assert job.lease_expired(NOW) is False
    assert job.lease_expired(NOW + timedelta(seconds=16)) is True
    assert Job.queued(key()).lease_expired(NOW) is False
