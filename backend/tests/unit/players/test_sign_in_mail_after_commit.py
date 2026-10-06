"""C-07 (PE-R3R-02): the sign-in email is sent only after the job's transaction committed, so
a link whose row was rolled back (lost lease, commit failure) is never mailed. The choice is
at-most-once delivery: a send that still fails after the runner's retries is logged and the
player asks for a new link (decision-log 2026-10-05). No I/O: session and mailer are doubles.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest
import sqlalchemy as sa

from racket.analysis_jobs.domain import JobKey
from racket.analysis_jobs.stage import StageContext
from racket.platform.settings import Settings
from racket.players.stages import SendSignInLinkStage

pytestmark = pytest.mark.unit


class _Session:
    def __init__(self) -> None:
        self.inserted = 0

    def execute(self, statement: Any, params: Any = None) -> Any:
        if isinstance(statement, sa.Insert):
            self.inserted += 1
        request = SimpleNamespace(id=uuid.uuid4(), email="ivy@example.test", email_key="k" * 16)
        return SimpleNamespace(one_or_none=lambda: request)


class _Mailer:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, to: str, message: Any) -> None:
        self.sent.append(to)


def test_the_email_is_sent_after_commit_not_inside_the_transaction() -> None:
    mailer, session = _Mailer(), _Session()
    settings = Settings.from_env({"APP_ENV": "test", "DATABASE_URL": "postgresql://u:p@h/d",
                                  "S3_BUCKET_MEDIA": "b"})  # fmt: skip
    ctx = StageContext(session=session, key=JobKey(uuid.uuid4(), "v0", "send_sign_in_link"),  # type: ignore[arg-type]
                       attempt=1, settings=settings, store=lambda: None)  # type: ignore[arg-type,return-value]  # fmt: skip
    SendSignInLinkStage(mailer).run(ctx)
    assert session.inserted == 1
    assert mailer.sent == []
    assert len(ctx.after_commit) == 1
    ctx.after_commit[0]()
    assert mailer.sent == ["ivy@example.test"]
