"""Vision Analysis job runtime, domain part: ``JobKey`` and the ``Job`` state machine (ST-007).

Pure Python (ddd-guidelines §4.5). A job is one unit of pipeline work identified by
``(match_id, pipeline_version, stage)``; it is idempotent per key and requeued on worker
shutdown [AQS/OPS-02]. ``attempts`` is the number of the current attempt, starting at 1.
Persistence maps ``Job`` imperatively in ``racket.analysis_jobs.queue``.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

_STAGE = re.compile(r"[a-z][a-z0-9_]{0,63}")
_REASON = re.compile(r"[a-z][a-z0-9_]{0,63}")


class InvalidJobTransition(RuntimeError):
    pass


@dataclass(frozen=True)
class JobKey:
    match_id: uuid.UUID
    pipeline_version: str
    stage: str

    def __post_init__(self) -> None:
        if not isinstance(self.match_id, uuid.UUID):
            object.__setattr__(self, "match_id", uuid.UUID(str(self.match_id)))
        if not _STAGE.fullmatch(self.stage or ""):
            raise ValueError("stage must be a lower-case identifier of at most 64 characters")
        if not 1 <= len(self.pipeline_version or "") <= 64:
            raise ValueError("pipeline_version must have 1 to 64 characters")


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(eq=False)
class Job:
    id: uuid.UUID
    key: JobKey
    status: JobStatus = JobStatus.QUEUED
    attempts: int = 1
    failure_reason: str | None = None
    worker_id: str | None = None
    lease_expires_at: datetime | None = None
    trace_context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @classmethod
    def queued(cls, key: JobKey, trace_context: dict[str, Any] | None = None) -> Job:
        return cls(id=uuid.uuid4(), key=key, trace_context=dict(trace_context or {}))

    # ------------------------------------------------------------ transitions
    def start(self, *, worker_id: str, lease_until: datetime) -> None:
        self._require(JobStatus.QUEUED, "start")
        self.status = JobStatus.RUNNING
        self.worker_id = worker_id
        self.lease_expires_at = lease_until
        self._touch()

    def complete(self) -> None:
        if self.status is JobStatus.DONE:
            return
        self._require(JobStatus.RUNNING, "complete")
        self.status = JobStatus.DONE
        self._release()

    def fail(self, reason: str) -> None:
        if not _REASON.fullmatch(reason or ""):
            raise ValueError("failure reason must be a short code, not free text")
        self._require(JobStatus.RUNNING, "fail")
        self.status = JobStatus.FAILED
        self.failure_reason = reason
        self._release()

    def requeue(self) -> None:
        self._require(JobStatus.RUNNING, "requeue")
        self.status = JobStatus.QUEUED
        self.attempts += 1
        self._release()

    def lease_expired(self, now: datetime) -> bool:
        return (
            self.status is JobStatus.RUNNING
            and self.lease_expires_at is not None
            and self.lease_expires_at < now
        )

    # ------------------------------------------------------------ helpers
    def _require(self, expected: JobStatus, action: str) -> None:
        if self.status != expected:
            raise InvalidJobTransition(f"cannot {action} a job that is {self.status}")

    def _release(self) -> None:
        self.worker_id = None
        self.lease_expires_at = None
        self._touch()

    def _touch(self) -> None:
        self.updated_at = _now()
