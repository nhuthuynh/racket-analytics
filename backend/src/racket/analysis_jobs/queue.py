"""Postgres-backed job queue (ST-007; ADR 0008 part B, confirmed by SPIKE-09).

* ``enqueue`` is idempotent per ``JobKey`` (``INSERT … ON CONFLICT DO NOTHING``) and injects
  the current W3C trace context into the job, inside an "enqueue" PRODUCER span [AQS/OPS-06].
* ``claim`` takes the oldest claimable job with ``FOR UPDATE SKIP LOCKED``: queued jobs, and
  running jobs whose lease has expired (their worker died: SIGKILL, OOM, lost node). A
  reclaimed job counts as a new attempt.
* The queue never commits; the caller owns the transaction (unit of work).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import sqlalchemy as sa
from opentelemetry.trace import SpanKind
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, composite

from racket.analysis_jobs.domain import Job, JobKey, JobStatus
from racket.platform.db import StrEnumType, mapper_registry, metadata
from racket.platform.tracing import inject_current, tracer

DEFAULT_LEASE = timedelta(seconds=15)

jobs = sa.Table(
    "jobs",
    metadata,
    sa.Column("id", sa.Uuid(), primary_key=True),
    sa.Column("match_id", sa.Uuid(), nullable=False),
    sa.Column("pipeline_version", sa.String(64), nullable=False),
    sa.Column("stage", sa.String(64), nullable=False),
    sa.Column("status", StrEnumType(JobStatus), nullable=False),
    sa.Column("attempts", sa.Integer(), nullable=False),
    sa.Column("failure_reason", sa.String(64)),
    sa.Column("worker_id", sa.String(128)),
    sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
    sa.Column("trace_context", JSONB(), nullable=False),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint("match_id", "pipeline_version", "stage", name="uq_jobs_key"),
)

mapper_registry.map_imperatively(
    Job,
    jobs,
    properties={"key": composite(JobKey, jobs.c.match_id, jobs.c.pipeline_version, jobs.c.stage)},
)


def _now() -> datetime:
    return datetime.now(UTC)


def _uuid(value: uuid.UUID | str) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class JobQueue:
    def __init__(self, session: Session, lease: timedelta = DEFAULT_LEASE) -> None:
        self.session = session
        self.lease = lease

    def enqueue(self, key: JobKey, trace_context: dict[str, Any] | None = None) -> uuid.UUID:
        """The job ID for ``key``; a second enqueue of the same key returns the first job."""
        # The span name stays generic: the stage name is reserved for the worker's stage span.
        with tracer().start_as_current_span("job enqueue", kind=SpanKind.PRODUCER) as span:
            span.set_attribute("job.stage", key.stage)
            carrier = inject_current() if trace_context is None else trace_context
            now = _now()
            inserted = self.session.execute(
                pg_insert(jobs)
                .values(
                    id=uuid.uuid4(),
                    match_id=key.match_id,
                    pipeline_version=key.pipeline_version,
                    stage=key.stage,
                    status=JobStatus.QUEUED,
                    attempts=1,
                    trace_context=carrier,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_nothing(constraint="uq_jobs_key")
                .returning(jobs.c.id)
            ).scalar_one_or_none()
        if inserted is not None:
            return uuid.UUID(str(inserted))
        existing: uuid.UUID = self.session.execute(
            sa.select(jobs.c.id).where(
                jobs.c.match_id == key.match_id,
                jobs.c.pipeline_version == key.pipeline_version,
                jobs.c.stage == key.stage,
            )
        ).scalar_one()
        return existing

    def claim(self, worker_id: str, stages: tuple[str, ...] | None = None) -> Job | None:
        now = _now()
        claimable = sa.or_(
            jobs.c.status == JobStatus.QUEUED,
            sa.and_(jobs.c.status == JobStatus.RUNNING, jobs.c.lease_expires_at < now),
        )
        query = sa.select(Job).where(claimable)
        if stages is not None:
            query = query.where(jobs.c.stage.in_(stages))
        query = (
            query.order_by(jobs.c.created_at, jobs.c.id)
            .limit(1)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )
        job = self.session.execute(query).scalar_one_or_none()
        if job is None:
            return None
        if job.lease_expired(now):
            job.requeue()  # its worker died mid-stage: this is a new attempt
        job.start(worker_id=worker_id, lease_until=now + self.lease)
        self.session.flush()
        return job

    def get(self, job_id: uuid.UUID | str) -> Job:
        query = (
            sa.select(Job)
            .where(jobs.c.id == _uuid(job_id))
            .execution_options(populate_existing=True)
        )
        return self.session.execute(query).scalar_one()

    def for_match(self, match_id: uuid.UUID | str) -> list[Job]:
        query = (
            sa.select(Job)
            .where(jobs.c.match_id == _uuid(match_id))
            .order_by(jobs.c.created_at)
            .execution_options(populate_existing=True)
        )
        return list(self.session.execute(query).scalars())

    def lock_running(self, job_id: uuid.UUID, worker_id: str) -> Job | None:
        """The job, row-locked, if this worker still holds it (it may have lost the lease)."""
        query = (
            sa.select(Job)
            .where(
                jobs.c.id == job_id,
                jobs.c.status == JobStatus.RUNNING,
                jobs.c.worker_id == worker_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self.session.execute(query).scalar_one_or_none()

    def extend_lease(self, job_id: uuid.UUID, worker_id: str) -> bool:
        result = self.session.execute(
            sa.update(jobs)
            .where(
                jobs.c.id == job_id,
                jobs.c.status == JobStatus.RUNNING,
                jobs.c.worker_id == worker_id,
            )
            .values(lease_expires_at=_now() + self.lease)
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]
