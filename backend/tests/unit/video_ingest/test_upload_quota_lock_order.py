"""C-02 (PE-R3R-01, major): the per-owner lock is taken before the open-upload quota is read.

sprint-02 §5 TDD order: 1. the per-owner lock comes before ``_check_quota`` (this file, no I/O:
collaborators are replaced by recorders); 2. IT-02-11, 8 parallel creations -> exactly 3 x 201
(senior-qa-engineer, integration lane).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from racket.platform.settings import Settings
from racket.video_ingest import service as service_module
from racket.video_ingest.repository import UploadRepository
from racket.video_ingest.service import UploadQuotaExceeded, UploadService

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


class _Session:
    """Stands in for the ORM session; only ``rollback`` / ``commit`` may be called."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def rollback(self) -> None:
        self.calls.append("rollback")

    def commit(self) -> None:  # pragma: no cover - a commit here would be a defect
        self.calls.append("commit")


@pytest.fixture
def order(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    monkeypatch.setattr(service_module.matches, "owns_match", lambda *a: True)
    monkeypatch.setattr(UploadRepository, "exists_for_match", lambda self, m: False)

    def lock_owner(self: Any, owner_id: uuid.UUID) -> None:
        calls.append("lock_owner")

    def open_for_owner(self: Any, owner_id: uuid.UUID, now: datetime) -> tuple[int, int]:
        calls.append("open_for_owner")
        return 3, 30  # at the quota: the creation is refused before any rate hit or S3 call

    monkeypatch.setattr(UploadRepository, "lock_owner", lock_owner, raising=False)
    monkeypatch.setattr(UploadRepository, "open_for_owner", open_for_owner)
    return calls


def _service() -> UploadService:
    settings = Settings.from_env(
        {"APP_ENV": "test", "DATABASE_URL": "postgresql://u:p@h/d", "S3_BUCKET_MEDIA": "b"}
    )
    return UploadService(_Session(), store=None, settings=settings, clock=lambda: NOW)  # type: ignore[arg-type]


def test_a_creation_without_the_owner_lock_never_reads_the_quota(order: list[str]) -> None:
    with pytest.raises(UploadQuotaExceeded):
        _service().create(
            owner_id=uuid.uuid4(), raw_match_id=str(uuid.uuid4()), upload_length="10",
            upload_metadata=None, route="/matches/{match_id}/uploads", method="POST",
        )  # fmt: skip
    assert order == ["lock_owner", "open_for_owner"]


def test_the_repository_has_a_per_owner_lock() -> None:
    assert callable(getattr(UploadRepository, "lock_owner", None))
