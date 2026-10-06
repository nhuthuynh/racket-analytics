"""IT-00-03 (queue <-> worker, ST-007): enqueue, claim, complete; a second claim of the same
key does nothing; enqueue is idempotent per (match_id, pipeline_version, stage) (AQS/OPS-02)."""

from __future__ import annotations

import uuid
from typing import Any

from tests.support import contract


def _key(match_id: uuid.UUID, stage: str = "probe") -> Any:
    return contract.JOB_KEY.load()(match_id=match_id, pipeline_version="p0", stage=stage)


def test_enqueue_claim_complete(db_session: Any) -> None:
    queue = contract.JOB_QUEUE.load()(db_session)
    job_id = queue.enqueue(_key(uuid.uuid4()))

    job = queue.claim(worker_id="w1")
    assert job is not None
    assert job.id == job_id
    assert job.status == "running"

    job.complete()
    db_session.flush()
    assert queue.get(job_id).status == "done"
    assert queue.claim(worker_id="w2") is None


def test_same_key_enqueued_twice_is_one_job(db_session: Any) -> None:
    queue = contract.JOB_QUEUE.load()(db_session)
    match_id = uuid.uuid4()

    first = queue.enqueue(_key(match_id))
    second = queue.enqueue(_key(match_id))

    assert first == second
    assert len(queue.for_match(match_id)) == 1


def test_running_job_is_not_claimed_again(db_session: Any) -> None:
    queue = contract.JOB_QUEUE.load()(db_session)
    queue.enqueue(_key(uuid.uuid4()))

    assert queue.claim(worker_id="w1") is not None
    assert queue.claim(worker_id="w2") is None


def test_concurrent_claims_on_separate_connections_skip_locked(committed_db: Any) -> None:
    from sqlalchemy.orm import Session

    queue_cls = contract.JOB_QUEUE.load()
    with Session(committed_db) as setup:
        queue_cls(setup).enqueue(_key(uuid.uuid4()))
        setup.commit()

    with Session(committed_db) as a, Session(committed_db) as b:
        got_a = queue_cls(a).claim(worker_id="a")
        got_b = queue_cls(b).claim(worker_id="b")  # must not block, must not get the same job
        assert got_a is not None
        assert got_b is None
