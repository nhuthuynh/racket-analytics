"""Steps for tests/features/job_resilience.feature (ST-007 with ST-009; NFR-046, NFR-047;
AQS/OPS-02 disposability, AQS/SEC-12 fail closed).

The worker runs as a real OS process; SIGTERM is a real signal. Fault injection uses the
RACKET_FAULT_INJECTION seam, which the worker honours only when APP_ENV=test.
"""

from __future__ import annotations

import signal
import subprocess
import time
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.support import contract
from tests.support.api import ApiDriver
from tests.support.flows import create_match, upload_fixture
from tests.support.format import status_label
from tests.support.worker import media_facts_count, probe_job, wait_for, worker_process

pytestmark = [pytest.mark.red_until(story="ST-007"), pytest.mark.slow]

scenarios("job_resilience.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@pytest.fixture
def workers() -> Iterator[Callable[..., subprocess.Popen[bytes]]]:
    """Start worker processes; all are killed after the scenario."""
    with ExitStack() as stack:
        yield lambda **env: stack.enter_context(worker_process(**env))


def _uploaded_match(api: ApiDriver) -> str:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "Resilience test"))
    api.run(upload_fixture(ivy, match_id))
    return match_id


@given("a probe job is running for Ivy's match")
def probe_running(
    api: ApiDriver,
    committed_db: Any,
    ctx: dict[str, Any],
    workers: Callable[..., subprocess.Popen[bytes]],
) -> None:
    ctx["match_id"] = _uploaded_match(api)
    ctx["proc"] = workers(**{contract.FAULT_INJECTION_ENV: "probe:sleep=60"})
    job = wait_for(
        lambda: (j := probe_job(committed_db, ctx["match_id"])) and j.status == "running" and j,
        timeout=20,
    )
    ctx["attempts_before"] = job.attempts


@when("the worker is told to shut down")
def sigterm(ctx: dict[str, Any]) -> None:
    ctx["signalled_at"] = time.monotonic()
    ctx["proc"].send_signal(signal.SIGTERM)


@then("the job is back in the queue within 10 seconds")
def requeued(committed_db: Any, ctx: dict[str, Any]) -> None:
    job = wait_for(
        lambda: (j := probe_job(committed_db, ctx["match_id"])) and j.status == "queued" and j,
        timeout=10,
    )
    assert time.monotonic() - ctx["signalled_at"] <= 10
    assert job.attempts == ctx["attempts_before"] + 1
    assert ctx["proc"].wait(timeout=10) is not None


@then("after it runs again the match has exactly one set of media facts")
def one_set_of_facts(api: ApiDriver, committed_db: Any, ctx: dict[str, Any]) -> None:
    contract.WORKER_RUN_UNTIL_IDLE.load()()
    assert probe_job(committed_db, ctx["match_id"]).status == "done"
    assert media_facts_count(committed_db, ctx["match_id"]) == 1
    response = api.request("ivy", "GET", contract.MATCH.format(match_id=ctx["match_id"]))
    assert response.json()["media"] is not None


@given("the probe stage will fail after writing part of its result")
def will_fail(api: ApiDriver, ctx: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv(contract.FAULT_INJECTION_ENV, "probe:fail_after_partial_write")
    ctx["match_id"] = _uploaded_match(api)


@when("the job runs")
def job_runs() -> None:
    contract.WORKER_RUN_UNTIL_IDLE.load()()


@then("the job is marked failed")
def marked_failed(committed_db: Any, ctx: dict[str, Any]) -> None:
    job = probe_job(committed_db, ctx["match_id"])
    assert job is not None
    assert job.status == "failed"
    assert job.failure_reason


@then("the match shows no media facts")
def no_media(api: ApiDriver, committed_db: Any, ctx: dict[str, Any]) -> None:
    assert media_facts_count(committed_db, ctx["match_id"]) == 0
    response = api.request("ivy", "GET", contract.MATCH.format(match_id=ctx["match_id"]))
    assert response.json()["media"] is None


@then('the match shows "We could not read this video"')
def shows_failure(api: ApiDriver, ctx: dict[str, Any]) -> None:
    response = api.request("ivy", "GET", contract.MATCH.format(match_id=ctx["match_id"]))
    assert status_label(response.json()["status"]) == "We could not read this video"
