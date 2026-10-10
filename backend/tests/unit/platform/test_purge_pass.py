"""The purge pass plan with fakes (ST-050b; deletion-and-purge.md §4.2, §4.6; ADR 0042, 0045).

Negative cases first: an unsafe ref means no store call and no row delete for that match, which
stays due, and the next match is still purged; a store failure keeps the rows (objects before
rows, no orphan). Then the order: objects, then rows, root last."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from botocore.exceptions import ClientError

from racket.platform.purge import PurgeJob, _env_int, main
from racket.video_ingest.public import MultipartRef, OriginalKey, StagingPrefix, UnsafeObjectRef

pytestmark = [pytest.mark.unit]

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
A, B = uuid.UUID(int=1), uuid.UUID(int=2)
OWNER = uuid.UUID(int=9)
HEX = "0123456789abcdef0123456789abcdef"


class FakeSession:
    def __init__(self, log: list[str]) -> None:
        self.log = log

    def commit(self) -> None:
        self.log.append("commit")

    def rollback(self) -> None:
        self.log.append("rollback")

    def close(self) -> None:
        pass

    def __enter__(self) -> FakeSession:
        return self

    def __exit__(self, *exc: Any) -> None:
        pass


class Due:
    def __init__(self, match_id: uuid.UUID, age: timedelta = timedelta(0)) -> None:
        self.match_id, self.owner_id, self.deleted_at = match_id, OWNER, NOW - age


class FakePorts:
    def __init__(self, log: list[str], refs: dict[uuid.UUID, Any], due: list[Due]) -> None:
        self.log, self.refs, self.due = log, refs, due
        self.claimed: set[uuid.UUID] = set()

    def abandoned_uploads(self, session: Any, now: datetime, limit: int) -> list[uuid.UUID]:
        return []  # ST-038's step has its own tests (test_expire_uploads.py)

    def tombstone_deleted_accounts(self, session: Any, now: datetime) -> list[uuid.UUID]:
        return []

    def due_matches(self, session: Any, limit: int) -> list[Due]:
        return self.due[:limit]

    def claim(self, session: Any, match_id: uuid.UUID) -> bool:
        return match_id not in self.claimed

    def object_refs(self, session: Any, match_id: uuid.UUID) -> list[Any]:
        refs = self.refs[match_id]
        if isinstance(refs, Exception):
            raise refs
        return list(refs)

    def purge_rows(self, session: Any, match_id: uuid.UUID) -> int:
        self.log.append(f"rows {match_id.int}")
        return 3

    def orphan_snapshot_ids(self, session: Any) -> list[uuid.UUID]:
        return []

    def purge_orphan_snapshot(self, session: Any, match_id: uuid.UUID) -> None:
        self.log.append(f"orphan {match_id.int}")

    def due_accounts(self, session: Any, limit: int) -> list[uuid.UUID]:
        return []

    def claim_account(self, session: Any, account_id: uuid.UUID) -> bool:
        return True

    def purge_account(self, session: Any, account_id: uuid.UUID) -> None:
        self.log.append("account")


class FakeStore:
    def __init__(self, log: list[str], fail_on: str | None = None) -> None:
        self.log, self.fail_on = log, fail_on

    def _call(self, what: str) -> None:
        if self.fail_on and self.fail_on in what:
            raise ConnectionError("store down")
        self.log.append(what)

    def delete(self, key: str) -> None:
        self._call(f"delete {key}")

    def delete_prefix(self, prefix: str) -> int:
        self._call(f"prefix {prefix}")
        return 1

    def abort_multipart(self, key: str, upload_id: str) -> None:
        self._call(f"abort {key}")


def _job(ports: FakePorts, store: FakeStore, log: list[str]) -> PurgeJob:
    return PurgeJob(lambda: FakeSession(log), store, ports=ports, clock=lambda: NOW)


REFS = [
    MultipartRef(f"originals/{HEX}", "u1"),
    StagingPrefix(f"staging/{HEX}/"),
    OriginalKey(f"originals/{HEX}"),
]


def test_an_unsafe_ref_stops_every_store_call_for_that_match_and_the_next_is_purged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    log: list[str] = []
    ports = FakePorts(log, {A: UnsafeObjectRef("bad"), B: REFS}, [Due(A), Due(B)])
    result = _job(ports, FakeStore(log), log).run_once()
    assert "rows 1" not in log
    store_calls = [e for e in log if e.split()[0] in ("abort", "prefix", "delete")]
    assert len(store_calls) == 3  # B's three refs only: none for A
    assert log.index("rows 2") > log.index(f"delete originals/{HEX}")
    assert (result.matches, result.failed) == (1, 1)
    failed = [r for r in caplog.records if getattr(r, "event", "") == "purge.failed"]
    assert [(r.stage, r.error, r.match_id) for r in failed] == [
        ("objects", "UnsafeObjectRef", str(A))
    ]


def test_a_store_failure_keeps_every_row_and_fails_the_pass() -> None:
    log: list[str] = []
    ports = FakePorts(log, {A: REFS}, [Due(A)])
    result = _job(ports, FakeStore(log, fail_on="delete originals"), log).run_once()
    assert "rows 1" not in log
    assert "rollback" in log
    assert (result.matches, result.failed, result.exit_code) == (0, 1, 1)


def test_objects_go_first_then_rows_in_one_transaction() -> None:
    log: list[str] = []
    ports = FakePorts(log, {A: REFS}, [Due(A)])
    result = _job(ports, FakeStore(log), log).run_once()
    assert log[log.index(f"abort originals/{HEX}") :][:5] == [
        f"abort originals/{HEX}",
        f"prefix staging/{HEX}/",
        f"delete originals/{HEX}",
        "rows 1",
        "commit",
    ]
    assert (result.matches, result.failed, result.exit_code) == (1, 0, 0)


def test_a_match_another_pass_holds_is_skipped() -> None:
    log: list[str] = []
    ports = FakePorts(log, {A: REFS}, [Due(A)])
    ports.claimed.add(A)
    result = _job(ports, FakeStore(log), log).run_once()
    assert [e for e in log if e not in ("commit", "rollback")] == []
    assert (result.matches, result.exit_code) == (0, 0)


def test_a_tombstone_older_than_six_days_is_reported_overdue(
    caplog: pytest.LogCaptureFixture,
) -> None:
    log: list[str] = []
    ports = FakePorts(log, {A: UnsafeObjectRef("bad")}, [Due(A, timedelta(days=6, hours=1))])
    _job(ports, FakeStore(log), log).run_once()
    overdue = [r for r in caplog.records if getattr(r, "event", "") == "purge.overdue"]
    assert [(r.levelname, r.match_id) for r in overdue] == [("ERROR", str(A))]


@pytest.mark.parametrize("argv", [[], ["--twice"], ["--once", "extra"]])
def test_usage_errors_exit_2(argv: list[str]) -> None:
    assert main(argv) == 2


# Added test-first in the ST-050b PR (porting P13): behaviours of the ported pass that no unit
# test held (decisions/ST-050b.md). Negative cases first.


def test_a_tombstone_younger_than_the_alert_age_is_not_overdue(
    caplog: pytest.LogCaptureFixture,
) -> None:
    log: list[str] = []
    ports = FakePorts(log, {A: REFS}, [Due(A, timedelta(days=5, hours=23))])
    _job(ports, FakeStore(log), log).run_once()
    assert [r for r in caplog.records if getattr(r, "event", "") == "purge.overdue"] == []


def test_a_failed_orphan_sweep_fails_the_pass_after_the_matches_are_purged() -> None:
    log: list[str] = []
    ports = FakePorts(log, {A: REFS}, [Due(A)])
    ports.orphan_snapshot_ids = _raise  # type: ignore[method-assign]
    result = _job(ports, FakeStore(log), log).run_once()
    assert "rows 1" in log
    assert log[-1] == "rollback"
    assert (result.matches, result.failed, result.exit_code) == (1, 1, 1)


def test_a_store_error_other_than_not_found_keeps_the_rows() -> None:
    log: list[str] = []
    ports = FakePorts(log, {A: [OriginalKey(f"originals/{HEX}")]}, [Due(A)])
    store = ErrorStore(log, "AccessDenied")
    result = _job(ports, store, log).run_once()
    assert "rows 1" not in log
    assert (result.matches, result.failed) == (0, 1)


@pytest.mark.parametrize("code", ["404", "NoSuchKey", "NoSuchUpload", "NotFound"])
def test_an_object_already_gone_counts_as_deleted(code: str) -> None:
    log: list[str] = []
    ports = FakePorts(log, {A: [OriginalKey(f"originals/{HEX}")]}, [Due(A)])
    result = _job(ports, ErrorStore(log, code), log).run_once()
    assert "rows 1" in log
    assert (result.matches, result.failed, result.exit_code) == (1, 0, 0)


def test_orphan_snapshots_are_swept_and_logged_with_their_match_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="racket.purge")
    log: list[str] = []
    ports = FakePorts(log, {}, [])
    ports.orphan_snapshot_ids = lambda session: [B]  # type: ignore[method-assign]
    result = _job(ports, FakeStore(log), log).run_once()
    assert log == ["commit", "commit", "rollback", "orphan 2", "commit", "rollback"]
    swept = [r for r in caplog.records if getattr(r, "event", "") == "purge.orphan_swept"]
    assert [(r.kind, r.match_id) for r in swept] == [("snapshot", str(B))]
    assert result.exit_code == 0


@pytest.mark.parametrize("raw", ["abc", "0", "-1", "١", "1.5"])
def test_a_bad_purge_setting_is_refused(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv("PURGE_BATCH", raw)
    with pytest.raises(ValueError, match="PURGE_BATCH"):
        _env_int("PURGE_BATCH", 100, 1)


@pytest.mark.parametrize(("raw", "value"), [("", 100), (" 7 ", 7)])
def test_a_purge_setting_defaults_or_is_read(
    monkeypatch: pytest.MonkeyPatch, raw: str, value: int
) -> None:
    monkeypatch.setenv("PURGE_BATCH", raw)
    assert _env_int("PURGE_BATCH", 100, 1) == value


def _raise(session: Any) -> list[uuid.UUID]:
    raise RuntimeError("snapshot table unavailable")


class ErrorStore(FakeStore):
    def __init__(self, log: list[str], code: str) -> None:
        super().__init__(log)
        self.code = code

    def delete(self, key: str) -> None:
        raise ClientError({"Error": {"Code": self.code}}, "DeleteObject")
