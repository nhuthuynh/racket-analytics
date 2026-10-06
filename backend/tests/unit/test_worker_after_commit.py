"""PE-R3-02: post-commit side effects run after the job's commit, are retried, never raise."""

from __future__ import annotations

import uuid
from typing import Any

from racket.analysis_jobs.stage import StageContext
from racket.worker.runner import AFTER_COMMIT_ATTEMPTS, Runner


def _ctx(callbacks: list[Any]) -> StageContext:
    ctx = StageContext(session=None, key=None, attempt=1, settings=None, store=lambda: None)  # type: ignore[arg-type]
    ctx.after_commit.extend(callbacks)
    return ctx


def test_a_step_that_always_fails_is_tried_a_bounded_number_of_times_and_not_raised() -> None:
    calls: list[int] = []

    def failing() -> None:
        calls.append(1)
        raise OSError("object store down")

    Runner._after_commit(uuid.uuid4(), _ctx([failing]))

    assert len(calls) == AFTER_COMMIT_ATTEMPTS


def test_a_transient_failure_is_retried_and_later_steps_still_run() -> None:
    calls: list[str] = []

    def flaky() -> None:
        calls.append("flaky")
        if calls.count("flaky") == 1:
            raise OSError("transient")

    Runner._after_commit(uuid.uuid4(), _ctx([flaky, lambda: calls.append("next")]))

    assert calls == ["flaky", "flaky", "next"]


def test_each_context_has_its_own_list() -> None:
    assert _ctx([]).after_commit is not _ctx([]).after_commit
