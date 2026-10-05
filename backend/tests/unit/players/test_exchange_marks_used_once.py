"""C-28 (SEC-R1-S1-04): the exchange marks a link used with ``used_at IS NULL`` in the UPDATE
and needs exactly one row changed (T-ML-3 defence in depth beside the row lock). No I/O: a
session double answers the SELECT with an unused link and the UPDATE with a row count."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
import sqlalchemy as sa

from racket.platform.settings import Settings
from racket.players.service import LinkRefused, MagicLinkService

pytestmark = pytest.mark.unit

NOW = datetime(2026, 10, 5, 12, tzinfo=UTC)
ROW = {"token_sha256": "a" * 64, "email_key": "b" * 16, "email": "ivy@example.test",
       "created_at": NOW, "expires_at": NOW + timedelta(minutes=15), "used_at": None}  # fmt: skip


class _Session:
    def __init__(self, rowcount: int) -> None:
        self.rowcount, self.updates, self.rolled_back = rowcount, [], False

    def execute(self, statement: Any, params: Any = None) -> Any:
        if isinstance(statement, sa.Update):
            self.updates.append(str(statement.compile(compile_kwargs={"literal_binds": False})))
            return SimpleNamespace(rowcount=self.rowcount)
        row = SimpleNamespace(**ROW, _mapping=ROW)
        return SimpleNamespace(one_or_none=lambda: row)

    def rollback(self) -> None:
        self.rolled_back = True

    def commit(self) -> None:  # pragma: no cover - a commit here would be a defect
        raise AssertionError("committed a refused exchange")


def _service(session: _Session, monkeypatch: pytest.MonkeyPatch) -> MagicLinkService:
    monkeypatch.setattr(MagicLinkService, "_limit", lambda self, *a, **k: None)
    settings = Settings.from_env({"APP_ENV": "test", "DATABASE_URL": "postgresql://u:p@h/d",
                                  "S3_BUCKET_MEDIA": "b"})  # fmt: skip
    return MagicLinkService(session, settings, clock=lambda: NOW)  # type: ignore[arg-type]


def test_a_link_used_by_someone_else_in_between_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _Session(rowcount=0)
    with pytest.raises(LinkRefused):
        _service(session, monkeypatch).exchange("t" * 43, "127.0.0.1", None)
    assert session.rolled_back
    assert "used_at IS NULL" in session.updates[0]
