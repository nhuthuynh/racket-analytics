"""Mandatory regression suite: fail closed (IT-00-05; testing-strategy §5; NFR-047;
AQS/SEC-12). Never deleted.

A stage that raises after a partial write leaves no rows and marks the job failed.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.support import contract
from tests.support.api import ApiDriver
from tests.support.flows import create_match, upload_fixture
from tests.support.worker import media_facts_count, probe_job


@pytest.fixture
def failing_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv(contract.FAULT_INJECTION_ENV, "probe:fail_after_partial_write")


def test_partial_write_is_rolled_back_and_job_failed(
    api: ApiDriver, committed_db: Any, failing_probe: None
) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "Fail closed"))
    api.run(upload_fixture(ivy, match_id))

    contract.WORKER_RUN_UNTIL_IDLE.load()()

    job = probe_job(committed_db, match_id)
    assert job is not None
    assert job.status == "failed"
    assert job.failure_reason
    assert media_facts_count(committed_db, match_id) == 0
    match = api.request("ivy", "GET", contract.MATCH.format(match_id=match_id)).json()
    assert match["media"] is None
    assert match["status"] == "probe_failed"


def test_failure_reason_holds_no_internals(
    api: ApiDriver, committed_db: Any, failing_probe: None
) -> None:
    """The reason shown to users and stored on the job is a code, not an exception dump."""
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "Fail closed 2"))
    api.run(upload_fixture(ivy, match_id))

    contract.WORKER_RUN_UNTIL_IDLE.load()()

    response = api.request("ivy", "GET", contract.MATCH.format(match_id=match_id))
    assert "Traceback" not in response.text
    assert "Error" not in response.text.replace("We could not read this video", "")


def test_fault_injection_is_ignored_outside_test_env(
    api: ApiDriver, committed_db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The fault-injection seam must never be live in dev or prod."""
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv(contract.FAULT_INJECTION_ENV, "probe:fail_after_partial_write")
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "Fault ignored"))
    api.run(upload_fixture(ivy, match_id))

    contract.WORKER_RUN_UNTIL_IDLE.load()()

    assert probe_job(committed_db, match_id).status == "done"
