"""The stage contract of the job runtime (Open Host Service R7 in the context map).

A context registers a ``Stage`` in ``racket.worker.stages.STAGES`` and owns its code. The runner
calls ``run`` inside one transaction that it commits together with "job done", so a stage's
writes and the job's completion are all-or-nothing [AQS/SEC-12]. If ``run`` raises, the
runner rolls that transaction back, then calls ``on_failure`` in a fresh transaction that also
marks the job failed with ``failure_reason`` (a short code, never exception text).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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


class Stage(Protocol):
    name: str
    failure_reason: str

    def run(self, ctx: StageContext) -> None: ...

    def on_failure(self, ctx: StageContext) -> None: ...


class ShutdownRequested(BaseException):
    """Raised inside a running stage when the worker receives SIGTERM (NFR-046b).

    A ``BaseException`` so that stage code catching ``Exception`` cannot swallow it.
    """
