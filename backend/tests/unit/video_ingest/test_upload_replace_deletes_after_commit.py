"""C-16 (PE-R2-S1-05): replacing an expired upload deletes its stored bytes only after the new
creation commits. A creation that is then refused (malformed metadata 400, quota 429, …) rolls
the database back, so the expired session must keep its bytes. No I/O: recorders stand in.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from racket.platform.errors import BadRequest
from racket.platform.settings import Settings
from racket.video_ingest import service as service_module
from racket.video_ingest.repository import UploadRepository
from racket.video_ingest.service import UploadService

pytestmark = pytest.mark.unit

NOW = datetime(2026, 10, 5, 12, tzinfo=UTC)


class _Store:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def abort_multipart(self, key: str, upload_id: str) -> None:
        self.calls.append("abort_multipart")

    def delete(self, key: str) -> None:
        self.calls.append("delete")


class _Session:
    def rollback(self) -> None:
        pass


@pytest.fixture
def expired(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    upload = SimpleNamespace(
        id=uuid.uuid4(),
        object_key="originals/x",
        s3_upload_id="u1",
        staged=[SimpleNamespace(key="staging/x/1")],
        is_expired=lambda now: True,
    )
    monkeypatch.setattr(service_module.matches, "owns_match", lambda *a: True)
    monkeypatch.setattr(UploadRepository, "exists_for_match", lambda self, m: True)
    monkeypatch.setattr(UploadRepository, "for_match", lambda self, m, for_update=False: upload)
    monkeypatch.setattr(UploadRepository, "delete", lambda self, u: None)
    return upload


def test_a_refused_replacement_leaves_the_expired_uploads_bytes(expired: Any) -> None:
    store = _Store()
    settings = Settings.from_env(
        {"APP_ENV": "test", "DATABASE_URL": "postgresql://u:p@h/d", "S3_BUCKET_MEDIA": "b"}
    )
    service = UploadService(_Session(), store, settings, clock=lambda: NOW)  # type: ignore[arg-type]
    with pytest.raises(BadRequest):
        service.create(
            owner_id=uuid.uuid4(),
            raw_match_id=str(uuid.uuid4()),
            upload_length="10",
            upload_metadata="filename not-base64!!",
            route="r",
            method="POST",
        )
    assert store.calls == []
