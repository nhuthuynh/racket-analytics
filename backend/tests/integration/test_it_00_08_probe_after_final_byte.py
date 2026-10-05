"""IT-00-08 (API <-> queue, ST-008): no probe job exists until the final byte is stored
(NFR-060; AQS/SEC-07 2.3.1)."""

from __future__ import annotations

from typing import Any

from tests.support import tus
from tests.support.api import ApiDriver
from tests.support.flows import create_match
from tests.support.worker import probe_job

DATA = bytes(range(256)) * 400


def test_probe_enqueued_only_after_last_byte(api: ApiDriver, committed_db: Any) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(create_match(ivy, "IT-00-08"))
    upload = api.run(tus.start(ivy, match_id, len(DATA)))
    assert probe_job(committed_db, match_id) is None

    api.run(tus.patch(ivy, upload, 0, DATA[:-1]))
    assert probe_job(committed_db, match_id) is None, "probe enqueued before the final byte"

    api.run(tus.patch(ivy, upload, len(DATA) - 1, DATA[-1:]))
    job = probe_job(committed_db, match_id)
    assert job is not None
    assert job.status == "queued"
