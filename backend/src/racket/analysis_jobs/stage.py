"""The stage contract of the job runtime (Open Host Service R7 in the context map).

A context registers a ``Stage`` in ``racket.worker.stages.STAGES`` and owns its code. The runner
calls ``run`` inside one transaction that it commits together with "job done", so a stage's
writes and the job's completion are all-or-nothing [AQS/SEC-12]. If ``run`` raises, the
runner rolls that transaction back, then calls ``on_failure`` in a fresh transaction that also
marks the job failed with ``failure_reason`` (a short code, never exception text).

Side effects outside the database (deleting an object, for example) must not happen inside
``run``: the runner can still roll the transaction back after ``run`` returns (lost lease,
commit failure). A stage registers them with ``StageContext.after_commit``; the runner runs them
only once the transaction has committed, retrying each a few times (PE-R1-08 / PE-R3-02).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy.orm import Session

from racket.analysis_jobs.domain import JobKey
from racket.platform.settings import Settings
from racket.platform.storage import ObjectStore


@dataclass(frozen=True)
class StageContext:
    session: Session
    key: JobKey
    attempt: int
    settings: Settings
    store: Callable[[], ObjectStore]
    after_commit: list[Callable[[], None]] = field(default_factory=list)


class Stage(Protocol):
    name: str
    failure_reason: str

    def run(self, ctx: StageContext) -> None: ...

    def on_failure(self, ctx: StageContext) -> None: ...


class ShutdownRequested(BaseException):
    """Raised inside a running stage when the worker receives SIGTERM (NFR-046b).

    A ``BaseException`` so that stage code catching ``Exception`` cannot swallow it.
    """
