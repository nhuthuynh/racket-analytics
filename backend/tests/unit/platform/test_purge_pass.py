"""The purge pass plan with fakes (ST-050b; deletion-and-purge.md §4.2, §4.6; ADR 0042, 0045).

Negative cases first: an unsafe ref means no store call and no row delete for that match, which
stays due, and the next match is still purged; a store failure keeps the rows (objects before
rows, no orphan). Then the order: objects, then rows, root last."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from racket.platform.purge import PurgeJob
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
