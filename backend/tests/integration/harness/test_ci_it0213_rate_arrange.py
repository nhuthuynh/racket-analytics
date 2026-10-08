"""CI-IT0213-HANG regression: the per-account rate test's arrange step must not depend on the
object store's write throughput.

Root cause (docs/sprints/03/ci-status.md, CI-IT0213-HANG): in scheduled run 37764445816 the
120 s budget of ``test_it_02_13_parallel_commands_never_pass_the_per_account_rate[1]`` ran out
before the parallel burst started. Its arrange step uploaded the 1.72 MB clip 12 times in a
row (2,586,311 bytes of S3 writes per match, 31 MB in all); the store took writes at about
64 KiB/s for those two minutes, and the timeout stack shows the only API thread waiting on an
S3 ``UploadPart`` response. No thread waited on Postgres.
"""

from __future__ import annotations

import os
import time
from typing import Any

import pytest

from tests.support import contract
from tests.support.api import ApiDriver
from tests.support.rate_burst import matches_with_video
from tests.support.slow_store import slow_object_store

pytestmark = pytest.mark.slow
ARRANGE_WRITE_BUDGET = 16 * 1024  # bytes sent to the object store for 12 matches


@pytest.fixture
def bytes_written(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Sizes of the bodies this test's in-process API sends to the object store."""
    sizes: list[int] = []
    store_class = contract.OBJECT_STORE.load()
    real_put, real_part = store_class.put_bytes, store_class.upload_part

    def put_bytes(store: Any, key: str, data: bytes) -> None:
        sizes.append(len(data))
        real_put(store, key, data)

    def upload_part(store: Any, key: str, upload_id: str, number: int, data: bytes) -> str:
        sizes.append(len(data))
        return str(real_part(store, key, upload_id, number, data))

    monkeypatch.setattr(store_class, "put_bytes", put_bytes)
    monkeypatch.setattr(store_class, "upload_part", upload_part)
    return sizes


@pytest.fixture
def many_uploads(monkeypatch: pytest.MonkeyPatch) -> None:
    """The limits IT-02-13 sets for its 12 uploads (``five_per_minute``)."""
    monkeypatch.setenv("UPLOAD_CREATE_LIMIT_PER_HOUR", "1000")
    monkeypatch.setenv("UPLOAD_MAX_OPEN_SESSIONS", "1000")


def test_the_rate_arrange_sends_almost_nothing_to_the_object_store(
    many_uploads: None, bytes_written: list[int], api: ApiDriver, committed_db: Any
) -> None:
    ivy = api.as_user("ivy")
    match_ids = matches_with_video(api, ivy, "CI-IT0213 bytes", 12)
    assert len(match_ids) == 12
    assert len(bytes_written) >= 12  # every match really went through an upload
    assert sum(bytes_written) <= ARRANGE_WRITE_BUDGET, sum(bytes_written)


def test_the_slow_store_proxy_slows_writes_and_keeps_them_intact() -> None:
    """Positive control for ``slow_object_store`` (testing-strategy rule 8): 48 KiB at
    64 KiB/s take at least 0.7 s, and the object read back is the object written."""
    store_class = contract.OBJECT_STORE.load()
    endpoint = os.environ["S3_ENDPOINT_URL"]
    data = os.urandom(48 * 1024)
    key = f"test-own/ci-it0213-{os.getpid()}-{time.monotonic_ns()}"
    with slow_object_store(endpoint) as slow_endpoint:
        os.environ["S3_ENDPOINT_URL"] = slow_endpoint
        try:
            slow = store_class.from_settings()
        finally:
            os.environ["S3_ENDPOINT_URL"] = endpoint
        started = time.monotonic()
        slow.put_bytes(key, data)
        took = time.monotonic() - started
        try:
            assert took >= 0.7, took
            assert slow.get_bytes(key) == data
        finally:
            slow.delete(key)
