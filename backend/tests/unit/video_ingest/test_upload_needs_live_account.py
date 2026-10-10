"""SEC-S3-TM-05 (ST-051; deletion-and-purge.md §3.3): an upload is created only for a live
account. The account row is read ``FOR SHARE`` after the per-owner lock and the quota check
(C-02 order) and before anything is written; a deleted account is 401 and nothing is written,
not even a rate-limit hit. An expired upload of the match is replaced under its row lock only
once the account row is held (§3.1 global order account -> upload -> match; PE-051-01:
``DELETE /me`` holds the account row, then locks the upload row, so the other order
deadlocks); the 413 path, which also replaces it, takes the account row first as well. No I/O:
collaborators are recorders. Negative cases first.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from racket.platform.errors import Unauthenticated
from racket.platform.settings import Settings
from racket.video_ingest import service as service_module
from racket.video_ingest.repository import UploadRepository
from racket.video_ingest.service import UploadService

pytestmark = [pytest.mark.unit]

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


class _Session:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def rollback(self) -> None:
        self.calls.append("rollback")

    def commit(self) -> None:  # pragma: no cover - a commit here would be a defect
        self.calls.append("commit")


class _Stop(Exception):
    """Ends a live-account creation right after the account lock (the rest is IT-02-11)."""


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    recorded: list[str] = []
    monkeypatch.setattr(service_module.matches, "owns_match", lambda *a: True)
    monkeypatch.setattr(UploadRepository, "exists_for_match", lambda self, m: False)
    monkeypatch.setattr(
        UploadRepository, "lock_owner", lambda self, o: recorded.append("lock_owner")
    )

    def open_for_owner(self: Any, owner_id: uuid.UUID, now: datetime) -> tuple[int, int]:
        recorded.append("open_for_owner")
        return 0, 0

    def hit(self: Any, *args: Any, **kwargs: Any) -> None:
        recorded.append("rate_limit_hit")
        raise _Stop

    monkeypatch.setattr(UploadRepository, "open_for_owner", open_for_owner)
    monkeypatch.setattr(service_module.RateLimiter, "hit", hit)
    return recorded


def _create(calls: list[str], length: str = "10") -> None:
    settings = Settings.from_env(
        {"APP_ENV": "test", "DATABASE_URL": "postgresql://u:p@h/d", "S3_BUCKET_MEDIA": "b"}
    )
    service = UploadService(_Session(calls), store=None, settings=settings, clock=lambda: NOW)  # type: ignore[arg-type]
    service.create(
        owner_id=uuid.uuid4(), raw_match_id=str(uuid.uuid4()), upload_length=length,
        upload_metadata=None, route="/matches/{match_id}/uploads", method="POST",
    )  # fmt: skip


def _account(monkeypatch: pytest.MonkeyPatch, calls: list[str], live: bool) -> None:
    def lock_live_account(session: Any, account_id: uuid.UUID) -> bool:
        calls.append("lock_live_account")
        return live

    monkeypatch.setattr(service_module.players, "lock_live_account", lock_live_account)


def test_a_deleted_account_gets_401_and_nothing_is_written(
    calls: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _account(monkeypatch, calls, live=False)
    with pytest.raises(Unauthenticated):
        _create(calls)
    assert calls == ["lock_owner", "open_for_owner", "lock_live_account", "rollback"]


def test_a_live_account_goes_on_to_the_rate_limit_after_the_account_lock(
    calls: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _account(monkeypatch, calls, live=True)
    with pytest.raises(_Stop):
        _create(calls)
    assert calls == ["lock_owner", "open_for_owner", "lock_live_account", "rate_limit_hit"]


def _expired_upload(monkeypatch: pytest.MonkeyPatch, calls: list[str]) -> None:
    """The match has an expired upload: the creation replaces it under its row lock."""
    expired = SimpleNamespace(
        id=uuid.uuid4(), object_key="originals/x", s3_upload_id="u1", staged=[],
        is_expired=lambda now: True,
    )  # fmt: skip

    def for_match(self: Any, match_id: uuid.UUID, *, for_update: bool = False) -> Any:
        calls.append("lock_upload_row" if for_update else "read_upload_row")
        return expired

    monkeypatch.setattr(UploadRepository, "exists_for_match", lambda self, m: True)
    monkeypatch.setattr(UploadRepository, "for_match", for_match)
    monkeypatch.setattr(UploadRepository, "delete", lambda self, u: calls.append("delete_upload"))


def test_a_deleted_account_never_locks_the_expired_upload_row(
    calls: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _account(monkeypatch, calls, live=False)
    _expired_upload(monkeypatch, calls)
    with pytest.raises(Unauthenticated):
        _create(calls)
    assert calls == [
        "read_upload_row", "lock_owner", "open_for_owner", "lock_live_account", "rollback",
    ]  # fmt: skip


def test_the_account_lock_comes_before_the_expired_upload_row_lock(
    calls: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _account(monkeypatch, calls, live=True)
    _expired_upload(monkeypatch, calls)
    with pytest.raises(_Stop):
        _create(calls)
    assert calls == [
        "read_upload_row", "lock_owner", "open_for_owner",
        "lock_live_account", "lock_upload_row", "delete_upload", "rate_limit_hit",
    ]  # fmt: skip


def test_a_too_large_replacement_takes_the_account_lock_before_the_upload_row_lock(
    calls: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The 413 path replaces the expired upload too, so it locks the account row first; a
    deleted account is 401 there and nothing is written."""
    _account(monkeypatch, calls, live=False)
    _expired_upload(monkeypatch, calls)
    with pytest.raises(Unauthenticated):
        _create(calls, length=str(10**15))
    assert calls == ["read_upload_row", "lock_live_account", "rollback"]
