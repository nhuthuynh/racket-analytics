"""The purge pass's ST-038 step (``PurgeJob`` with ``ContextPorts``) with fakes (FR-024,
NFR-066 d; deletion-and-purge.md §4.3, §4.4, §4.5). The video_ingest and matches ports are
faked; the job, the context ports and the ref deletion are real.

Negative cases first: nothing abandoned means no store call and no row delete; an upload of a
deleted match is left to that match's purge (fail-closed ref checks, §4.6; IT
``test_st_050b_purge_refs_fail_closed``), whether the match was deleted before the listing or
before the claim; an upload a request or another pass holds is skipped; a store failure keeps
that upload's row (bytes first, then the row: never an orphan) and, review round 1
(ST038-QA-1), frees the next upload and logs ``purge.failed`` with the upload's id; a refused
ref does the same. Then (PE-038-01) uploads of deleted matches never fill a batch. Then the
order (abort the multipart upload, delete the staging folder, then forget the row, then
commit), a missing object counting as freed, the idle setting reaching the ports, the batch
size, and the ids-only log line.

Review round 1 rewrote this file for the per-upload step (TCR row in decisions/ST-038.md)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from botocore.exceptions import ClientError

from racket.platform import purge
from racket.video_ingest.public import (
    AbandonedUpload,
    MultipartRef,
    StagingPrefix,
    UnsafeObjectRef,
)

pytestmark = [pytest.mark.unit]

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
UPLOAD, MATCH, OWNER = uuid.UUID(int=1), uuid.UUID(int=2), uuid.UUID(int=3)
OTHER, OTHER_MATCH = uuid.UUID(int=11), uuid.UUID(int=12)
HEX = UPLOAD.hex
PAGE = 500  # purge.UPLOAD_PAGE


def _abandoned(upload_id: uuid.UUID, match_id: uuid.UUID) -> AbandonedUpload:
    refs = (MultipartRef(f"originals/{upload_id.hex}", "mp-1"), StagingPrefix.of(upload_id))
    return AbandonedUpload(upload_id, match_id, OWNER, refs)


class FakeSession:
    def __init__(self, log: list[str]) -> None:
        self.log = log

    def commit(self) -> None:
        self.log.append("commit")

    def rollback(self) -> None:
        self.log.append("rollback")

    def __enter__(self) -> FakeSession:
        return self

    def __exit__(self, *exc: Any) -> None:
        pass


class FakeStore:
    def __init__(self, log: list[str], errors: dict[str, Exception] | None = None) -> None:
        self.log, self.errors = log, errors or {}

    def abort_multipart(self, key: str, upload_id: str) -> None:
        if key in self.errors:
            raise self.errors[key]
        self.log.append(f"abort {key} {upload_id}")

    def delete_prefix(self, prefix: str) -> int:
        self.log.append(f"prefix {prefix}")
        return 1


class Ports(purge.ContextPorts):
    """The real context ports; the pass's other steps have nothing to do."""

    def tombstone_deleted_accounts(self, session: Any, now: datetime) -> list[uuid.UUID]:
        return []

    def due_matches(self, session: Any, limit: int) -> list[Any]:
        return []

    def orphan_snapshot_ids(self, session: Any) -> list[uuid.UUID]:
        return []

    def due_accounts(self, session: Any, limit: int) -> list[uuid.UUID]:
        return []


@pytest.fixture
def seen(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """``uploads``: upload id -> match id of every abandoned upload; ``deleted``: deleted
    matches (``deleted_before_claim``: deleted between the listing and the claim); ``held``:
    rows a request or another pass locks; ``unsafe``: uploads whose refs are refused."""
    state: dict[str, Any] = {
        "log": [],
        "uploads": {UPLOAD: MATCH},
        "deleted": set(),
        "deleted_before_claim": set(),
        "held": set(),
        "unsafe": set(),
        "idle": [],
        "pages": 0,
    }

    def abandoned_upload_ids(
        session: Any, now: datetime, idle: timedelta, *, after: Any = None, limit: int = 100
    ) -> list[tuple[uuid.UUID, uuid.UUID]]:
        state["idle"].append(idle)
        state["pages"] += 1
        rows = sorted((u, m) for u, m in state["uploads"].items() if after is None or u > after)
        return rows[:limit]

    def claim_abandoned_upload(
        session: Any, upload_id: uuid.UUID, now: datetime, idle: timedelta
    ) -> AbandonedUpload | None:
        state["idle"].append(idle)
        if upload_id in state["held"] or upload_id not in state["uploads"]:
            return None
        if upload_id in state["unsafe"]:
            raise UnsafeObjectRef("bad shape")
        state["deleted"] |= state["deleted_before_claim"]
        return _abandoned(upload_id, state["uploads"][upload_id])

    def forget_upload(session: Any, upload_id: uuid.UUID) -> None:
        state["log"].append(f"forget {upload_id.int}")

    def live_ids(session: Any, ids: list[uuid.UUID]) -> set[uuid.UUID]:
        return {i for i in ids if i not in state["deleted"]}

    vi = purge.video_ingest
    monkeypatch.setattr(vi, "abandoned_upload_ids", abandoned_upload_ids, raising=False)
    monkeypatch.setattr(vi, "claim_abandoned_upload", claim_abandoned_upload, raising=False)
    monkeypatch.setattr(vi, "forget_upload", forget_upload)
    monkeypatch.setattr(purge.matches, "live_ids", live_ids)
    return state


def _run(
    seen: dict[str, Any],
    store: FakeStore | None = None,
    *,
    idle: timedelta | None = None,
    batch: int = 100,
) -> purge.PassResult:
    ports = Ports() if idle is None else Ports(upload_idle=idle)
    job = purge.PurgeJob(
        lambda: FakeSession(seen["log"]),
        store or FakeStore(seen["log"]),
        ports=ports,
        clock=lambda: NOW,
        batch=batch,
    )
    return job.run_once()


def _work(seen: dict[str, Any]) -> list[str]:
    return [e for e in seen["log"] if e not in ("commit", "rollback")]


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "x"}}, "AbortMultipartUpload")


def test_nothing_abandoned_touches_neither_store_nor_rows(seen: dict[str, Any]) -> None:
    seen["uploads"] = {}
    result = _run(seen)
    assert _work(seen) == []
    assert (result.uploads, result.failed) == (0, 0)


def test_an_upload_of_a_deleted_match_is_left_to_the_match_purge(seen: dict[str, Any]) -> None:
    seen["deleted"] = {MATCH}
    result = _run(seen)
    assert _work(seen) == []
    assert (result.uploads, result.failed) == (0, 0)


def test_an_upload_whose_match_is_deleted_before_the_claim_is_left_alone(
    seen: dict[str, Any],
) -> None:
    seen["deleted_before_claim"] = {MATCH}
    result = _run(seen)
    assert _work(seen) == []
    assert (result.uploads, result.failed) == (0, 0)


def test_an_upload_a_request_or_another_pass_holds_is_skipped(seen: dict[str, Any]) -> None:
    seen["held"] = {UPLOAD}
    result = _run(seen)
    assert _work(seen) == []
    assert (result.uploads, result.failed) == (0, 0)


def test_a_store_failure_keeps_the_row(seen: dict[str, Any]) -> None:
    store = FakeStore(seen["log"], {f"originals/{HEX}": _client_error("AccessDenied")})
    result = _run(seen, store)
    assert not any(e.startswith("forget") for e in seen["log"])
    assert (result.uploads, result.failed, result.exit_code) == (0, 1, 1)


def test_a_store_failure_on_one_upload_frees_the_next_and_names_the_failed_one(
    seen: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    """ST038-QA-1: the failing upload is listed first on every pass; it must not block the rest."""
    seen["uploads"] = {UPLOAD: MATCH, OTHER: OTHER_MATCH}
    store = FakeStore(seen["log"], {f"originals/{HEX}": _client_error("AccessDenied")})
    result = _run(seen, store)
    assert "forget 1" not in seen["log"]
    assert _work(seen)[-3:] == [
        f"abort originals/{OTHER.hex} mp-1",
        f"prefix staging/{OTHER.hex}/",
        "forget 11",
    ]
    assert seen["log"][seen["log"].index("forget 11") + 1] == "commit"
    assert (result.uploads, result.failed, result.exit_code) == (1, 1, 1)
    failed = [r for r in caplog.records if getattr(r, "event", "") == "purge.failed"]
    assert [(r.kind, getattr(r, "upload_id", None), r.stage, r.error) for r in failed] == [
        ("upload", str(UPLOAD), "objects", "ClientError")
    ]


def test_a_refused_ref_fails_that_upload_only(
    seen: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    seen["uploads"] = {UPLOAD: MATCH, OTHER: OTHER_MATCH}
    seen["unsafe"] = {UPLOAD}
    result = _run(seen)
    assert "forget 11" in seen["log"]
    assert "forget 1" not in seen["log"]
    assert not any(HEX in e for e in _work(seen))
    assert (result.uploads, result.failed) == (1, 1)
    failed = [r for r in caplog.records if getattr(r, "event", "") == "purge.failed"]
    assert [(getattr(r, "upload_id", None), r.stage, r.error) for r in failed] == [
        (str(UPLOAD), "objects", "UnsafeObjectRef")
    ]


def test_uploads_of_deleted_matches_never_fill_the_batch(seen: dict[str, Any]) -> None:
    """PE-038-01 (b): more uploads of deleted matches than one page, then a live one."""
    waiting = {uuid.UUID(int=100 + i): uuid.UUID(int=10_000 + i) for i in range(PAGE + 1)}
    live_upload, live_match = uuid.UUID(int=99_999), uuid.UUID(int=99_998)
    seen["uploads"] = {**waiting, live_upload: live_match}
    seen["deleted"] = set(waiting.values())
    result = _run(seen, batch=1)
    assert _work(seen) == [
        f"abort originals/{live_upload.hex} mp-1",
        f"prefix staging/{live_upload.hex}/",
        f"forget {live_upload.int}",
    ]
    assert result.uploads == 1


def test_the_batch_bounds_the_uploads_of_one_pass(seen: dict[str, Any]) -> None:
    seen["uploads"] = {UPLOAD: MATCH, OTHER: OTHER_MATCH}
    assert _run(seen, batch=1).uploads == 1
    assert [e for e in seen["log"] if e.startswith("forget")] == ["forget 1"]


def test_bytes_are_freed_first_then_the_row(seen: dict[str, Any]) -> None:
    result = _run(seen)
    assert result.uploads == 1
    assert _work(seen) == [f"abort originals/{HEX} mp-1", f"prefix staging/{HEX}/", "forget 1"]
    assert seen["log"][seen["log"].index("forget 1") + 1] == "commit"


def test_a_multipart_upload_already_gone_counts_as_freed(seen: dict[str, Any]) -> None:
    store = FakeStore(seen["log"], {f"originals/{HEX}": _client_error("NoSuchUpload")})
    result = _run(seen, store)
    assert (result.uploads, result.failed) == (1, 0)
    assert _work(seen) == [f"prefix staging/{HEX}/", "forget 1"]


def test_the_idle_setting_reaches_the_ports(seen: dict[str, Any]) -> None:
    _run(seen)
    assert set(seen["idle"]) == {timedelta(hours=24)}  # FR-024 default
    seen["idle"] = []
    _run(seen, idle=timedelta(hours=2))
    assert set(seen["idle"]) == {timedelta(hours=2)}


def test_each_expiry_is_logged_with_ids_only(
    seen: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="racket.purge")
    _run(seen)
    lines = [r for r in caplog.records if getattr(r, "event", "") == "upload.expired"]
    assert len(lines) == 1
    line = lines[0]
    assert (line.upload_id, line.match_id, line.user_id) == (str(UPLOAD), str(MATCH), str(OWNER))
    assert "file_name" not in line.__dict__
    assert "object_key" not in line.__dict__
