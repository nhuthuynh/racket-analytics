"""``ContextPorts.expire_uploads``, the purge pass's ST-038 step, with fakes (FR-024, NFR-066 d;
deletion-and-purge.md §4.4). Negative cases first: nothing abandoned means no store call and no
row delete; a store failure keeps the row (bytes first, then the row: never an orphan). Then the
order (abort the multipart upload, delete the staging folder, then forget the row), a missing
object counting as freed, the idle setting reaching the policy, and the ids-only log line."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from botocore.exceptions import ClientError

from racket.platform import purge
from racket.video_ingest.public import AbandonedUpload, MultipartRef, StagingPrefix

pytestmark = [pytest.mark.unit]

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
UPLOAD, MATCH, OWNER = uuid.UUID(int=1), uuid.UUID(int=2), uuid.UUID(int=3)
HEX = UPLOAD.hex


def _abandoned(upload_id: uuid.UUID = UPLOAD) -> AbandonedUpload:
    refs = (MultipartRef(f"originals/{upload_id.hex}", "mp-1"), StagingPrefix.of(upload_id))
    return AbandonedUpload(upload_id, MATCH, OWNER, refs)


class FakeStore:
    def __init__(self, log: list[str], error: Exception | None = None) -> None:
        self.log, self.error = log, error

    def abort_multipart(self, key: str, upload_id: str) -> None:
        if self.error is not None:
            raise self.error
        self.log.append(f"abort {key} {upload_id}")

    def delete_prefix(self, prefix: str) -> int:
        self.log.append(f"prefix {prefix}")
        return 1


@pytest.fixture
def seen(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {"log": [], "found": [_abandoned()], "idle": None}

    def abandoned_uploads(session: Any, now: datetime, idle: timedelta) -> list[AbandonedUpload]:
        state["idle"] = idle
        return list(state["found"])

    def forget_upload(session: Any, upload_id: uuid.UUID) -> None:
        state["log"].append(f"forget {upload_id.int}")

    monkeypatch.setattr(purge.video_ingest, "abandoned_uploads", abandoned_uploads)
    monkeypatch.setattr(purge.video_ingest, "forget_upload", forget_upload)
    return state


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "x"}}, "AbortMultipartUpload")


def test_nothing_abandoned_touches_neither_store_nor_rows(seen: dict[str, Any]) -> None:
    seen["found"] = []
    assert purge.ContextPorts().expire_uploads(object(), FakeStore(seen["log"]), NOW) == 0
    assert seen["log"] == []


def test_a_store_failure_keeps_the_row(seen: dict[str, Any]) -> None:
    store = FakeStore(seen["log"], error=_client_error("AccessDenied"))
    with pytest.raises(ClientError):
        purge.ContextPorts().expire_uploads(object(), store, NOW)
    assert not any(e.startswith("forget") for e in seen["log"])


def test_bytes_are_freed_first_then_the_row(seen: dict[str, Any]) -> None:
    freed = purge.ContextPorts().expire_uploads(object(), FakeStore(seen["log"]), NOW)
    assert freed == 1
    assert seen["log"] == [f"abort originals/{HEX} mp-1", f"prefix staging/{HEX}/", "forget 1"]


def test_a_multipart_upload_already_gone_counts_as_freed(seen: dict[str, Any]) -> None:
    store = FakeStore(seen["log"], error=_client_error("NoSuchUpload"))
    assert purge.ContextPorts().expire_uploads(object(), store, NOW) == 1
    assert seen["log"] == [f"prefix staging/{HEX}/", "forget 1"]


def test_the_idle_setting_reaches_the_policy(seen: dict[str, Any]) -> None:
    purge.ContextPorts().expire_uploads(object(), FakeStore(seen["log"]), NOW)
    assert seen["idle"] == timedelta(hours=24)  # FR-024 default
    purge.ContextPorts(upload_idle=timedelta(hours=2)).expire_uploads(
        object(), FakeStore(seen["log"]), NOW
    )
    assert seen["idle"] == timedelta(hours=2)


def test_each_expiry_is_logged_with_ids_only(
    seen: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="racket.purge")
    purge.ContextPorts().expire_uploads(object(), FakeStore(seen["log"]), NOW)
    lines = [r for r in caplog.records if getattr(r, "event", "") == "upload.expired"]
    assert len(lines) == 1
    line = lines[0]
    assert (line.upload_id, line.match_id, line.user_id) == (str(UPLOAD), str(MATCH), str(OWNER))
    assert "file_name" not in line.__dict__
    assert "object_key" not in line.__dict__
