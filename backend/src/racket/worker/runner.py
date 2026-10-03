"""Job runner: claim, run a stage, commit or fail closed, requeue on shutdown (ST-007).

* A claimed job is ``running`` with a lease. A heartbeat thread extends the lease while the
  stage runs; a worker that dies (SIGKILL) stops extending it, and another worker reclaims the
  job once the lease expires (``JobQueue.claim``) [AQS/OPS-02].
* The stage's writes and "job done" commit in one transaction. If the stage raises, that
  transaction is rolled back, and a fresh one marks the job ``failed`` with a reason code
  (NFR-047; AQS/SEC-12).
* SIGTERM during a stage raises ``ShutdownRequested`` in the stage; its writes are rolled back
  and the job is requeued with attempt + 1 (NFR-046b). SIGTERM between jobs just stops the loop.
* The stage span continues the trace stored on the job at enqueue [AQS/OPS-06].
"""

from __future__ import annotations

import logging
import os
import socket
import threading
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from functools import cache

from opentelemetry.trace import SpanKind, Status, StatusCode
from sqlalchemy.orm import Session, sessionmaker

from racket.analysis_jobs.domain import JobKey
from racket.analysis_jobs.queue import JobQueue
from racket.analysis_jobs.stage import ShutdownRequested, Stage, StageContext
from racket.platform.db import engine_for, session_factory
from racket.platform.settings import Settings
from racket.platform.storage import ObjectStore
from racket.platform.tracing import extract_context, tracer

log = logging.getLogger("racket.worker")


@dataclass
class ShutdownState:
    """Shared with the SIGTERM handler: ``in_stage`` says whether raising is safe."""

    stop: bool = False
    in_stage: bool = False


def new_worker_id(prefix: str = "w") -> str:
    return f"{prefix}-{socket.gethostname()[:32]}-{os.getpid()}-{uuid.uuid4().hex[:8]}"


class LeaseHeartbeat:
    def __init__(self, factory: sessionmaker[Session], job_id: uuid.UUID, worker_id: str,
                 lease: timedelta) -> None:  # fmt: skip
        self._factory, self._job_id, self._worker_id, self._lease = (
            factory,
            job_id,
            worker_id,
            lease,
        )
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._beat, name="lease-heartbeat", daemon=True)

    def __enter__(self) -> LeaseHeartbeat:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stopped.set()
        self._thread.join(timeout=5)

    def _beat(self) -> None:
        interval = max(0.5, self._lease.total_seconds() / 3)
        while not self._stopped.wait(interval):
            try:
                with self._factory() as session:
                    held = JobQueue(session, self._lease).extend_lease(
                        self._job_id, self._worker_id
                    )
                    session.commit()
                if not held:
                    log.warning(
                        "lease lost", extra={"event": "job.lease_lost", "job_id": str(self._job_id)}
                    )
                    return
            except Exception as exc:  # noqa: BLE001 - keep beating; the lease covers short outages
                log.warning(
                    "lease extend failed",
                    extra={"event": "job.lease_error", "exc_type": type(exc).__name__},
                )


@dataclass
class Runner:
    settings: Settings
    stages: Mapping[str, Stage]
    worker_id: str = field(default_factory=new_worker_id)
    shutdown: ShutdownState = field(default_factory=ShutdownState)

    def __post_init__(self) -> None:
        self.factory = session_factory(engine_for(self.settings.database_url))
        self.lease = timedelta(seconds=self.settings.worker_lease_seconds)
        self.store: Callable[[], ObjectStore] = cache(
            lambda: ObjectStore.from_settings(self.settings)
        )

    def run_one(self) -> bool:
        """Claim and run one job. False when nothing was claimable."""
        with self.factory() as session:
            job = JobQueue(session, self.lease).claim(self.worker_id, stages=tuple(self.stages))
            if job is None:
                session.rollback()
                return False
            job_id, key, attempt, carrier = job.id, job.key, job.attempts, dict(job.trace_context)
            session.commit()
        log.info("job claimed", extra={"event": "job.claimed", "job_id": str(job_id),
                                       "stage": key.stage, "attempt": attempt})  # fmt: skip
        self._execute(job_id, key, attempt, carrier)
        return True

    def run_until_idle(self, max_jobs: int = 100) -> int:
        ran = 0
        while ran < max_jobs and not self.shutdown.stop and self.run_one():
            ran += 1
        return ran

    # ------------------------------------------------------------ one job
    def _execute(
        self, job_id: uuid.UUID, key: JobKey, attempt: int, carrier: dict[str, str]
    ) -> None:
        stage = self.stages[key.stage]
        parent = extract_context(carrier)
        with tracer().start_as_current_span(f"stage {key.stage}", context=parent,
                                            kind=SpanKind.CONSUMER) as span:  # fmt: skip
            span.set_attribute("job.id", str(job_id))
            span.set_attribute("job.attempt", attempt)
            session = self.factory()
            try:
                with LeaseHeartbeat(self.factory, job_id, self.worker_id, self.lease):
                    self.shutdown.in_stage = True
                    try:
                        if self.shutdown.stop:
                            raise ShutdownRequested
                        stage.run(self._context(session, key, attempt))
                    finally:
                        self.shutdown.in_stage = False
                job = JobQueue(session, self.lease).lock_running(job_id, self.worker_id)
                if job is None:  # lost the lease meanwhile; another worker owns the job now
                    session.rollback()
                    log.warning(
                        "job abandoned", extra={"event": "job.abandoned", "job_id": str(job_id)}
                    )
                    return
                job.complete()
                session.commit()
                log.info("job done", extra={"event": "job.done", "job_id": str(job_id)})
            except ShutdownRequested:
                self._rollback(session)
                self._settle(job_id, key, attempt, requeue=True, stage=stage)
                span.set_attribute("job.requeued", True)
                raise
            except Exception as exc:  # noqa: BLE001 - any stage failure fails the job closed
                self._rollback(session)
                self._settle(job_id, key, attempt, requeue=False, stage=stage)
                span.set_status(Status(StatusCode.ERROR))
                log.error("job failed", extra={"event": "job.failed", "job_id": str(job_id),
                                               "reason": stage.failure_reason,
                                               "exc_type": type(exc).__name__})  # fmt: skip
            finally:
                session.close()

    def _settle(self, job_id: uuid.UUID, key: JobKey, attempt: int, *, requeue: bool,
                stage: Stage) -> None:  # fmt: skip
        with self.factory() as session:
            job = JobQueue(session, self.lease).lock_running(job_id, self.worker_id)
            if job is None:
                session.rollback()
                return
            if requeue:
                job.requeue()
                log.info("job requeued", extra={"event": "job.requeued", "job_id": str(job_id)})
            else:
                job.fail(stage.failure_reason)
                stage.on_failure(self._context(session, key, attempt))
            session.commit()

    def _context(self, session: Session, key: JobKey, attempt: int) -> StageContext:
        return StageContext(session=session, key=key, attempt=attempt, settings=self.settings,
                            store=self.store)  # fmt: skip

    @staticmethod
    def _rollback(session: Session) -> None:
        try:
            session.rollback()
        except Exception:  # noqa: BLE001 - an interrupted connection: drop it rather than reuse it
            session.invalidate()


def run_until_idle(max_jobs: int = 100) -> int:
    """ADR 0012 seam: claim and run jobs in-process until none is left. Reads the environment
    at call time, so ``APP_ENV``/fault injection set by a test apply."""
    from racket.worker.stages import STAGES

    runner = Runner(Settings.from_env(), STAGES, worker_id=new_worker_id("inproc"))
    return runner.run_until_idle(max_jobs)
