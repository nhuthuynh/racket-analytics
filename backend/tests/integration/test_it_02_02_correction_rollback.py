"""IT-02-02 (ST-032; NFR-047 fail closed): a failure injected in the middle of a correction
replay rolls back everything; the sheet, the rallies, the audit trail and the version are
unchanged.

The failure is injected through the service seam (``get_scorebook_service``, ADR 0012): the
repository writes the whole difference of the correction, then raises before the commit.
Positive control: the same correction without the injection changes the sheet.
"""

from __future__ import annotations

from typing import Annotated, Any

import sqlalchemy as sa
from fastapi import Depends
from sqlalchemy.orm import Session

from racket.matches.scorebook.api import get_scorebook_service
from racket.matches.scorebook.repository import ScorebookRepository
from racket.matches.scorebook.service import ScorebookService
from racket.platform.db import get_session
from tests.support import scorebook as sb
from tests.support.api import ApiDriver

CORRECTION = {"field": "winning_side", "value": "A"}


class FailingRepository(ScorebookRepository):
    def save(self, *args: Any, **kwargs: Any) -> None:
        super().save(*args, **kwargs)  # every row of the difference is written ...
        raise RuntimeError("injected failure before the commit (IT-02-02)")  # ... then this


def failing_service(session: Annotated[Session, Depends(get_session)]) -> ScorebookService:
    service = ScorebookService(session)
    service.books = FailingRepository(session)
    return service


def _snapshot(engine: Any, match_id: str) -> dict[str, Any]:
    with engine.connect() as conn:
        one = conn.execute
        return {
            "version": one(
                sa.text("SELECT version FROM matches WHERE id = :m"), {"m": match_id}
            ).scalar_one(),
            "rallies": one(
                sa.text(
                    "SELECT id, winning_side, ending, withdrawn FROM match_rallies "
                    "WHERE match_id = :m ORDER BY seq"
                ),
                {"m": match_id},
            ).all(),
            "corrections": one(
                sa.text("SELECT count(*) FROM match_corrections WHERE match_id = :m"),
                {"m": match_id},
            ).scalar_one(),
        }


def _correct(api: ApiDriver, match_id: str, rally_id: str) -> Any:
    ivy = api.as_user("ivy")
    version = api.run(sb.version_of(ivy, match_id))
    return api.run(
        sb.command(
            ivy, "correct", version=version, body=CORRECTION, match_id=match_id, rally_id=rally_id
        )
    )


def test_it_02_02_a_failure_mid_correction_rolls_back_everything(
    api: ApiDriver, committed_db: Any
) -> None:
    match_id = sb.ready_tagged_match(api, "ivy", title="IT-02-02")
    ivy = api.as_user("ivy")
    before_sheet = api.run(sb.sheet(ivy, match_id)).json()
    rally_2 = before_sheet["rows"][1]["rally_id"]  # B won; changing it re-scores rallies 2..6
    before = _snapshot(committed_db, match_id)

    api.app.dependency_overrides[get_scorebook_service] = failing_service
    try:
        response = _correct(api, match_id, rally_2)
    finally:
        api.app.dependency_overrides.pop(get_scorebook_service, None)

    assert response.status_code == 500, response.text
    assert response.json()["error"]["code"] == "internal_error"
    assert _snapshot(committed_db, match_id) == before
    assert sb.canonical(api.run(sb.sheet(ivy, match_id)).json()) == sb.canonical(before_sheet)

    # Positive control: the same correction, not injected, is saved and re-scores the sheet.
    ok = _correct(api, match_id, rally_2)
    assert ok.status_code == 200, ok.text
    assert sb.canonical(api.run(sb.sheet(ivy, match_id)).json()) != sb.canonical(before_sheet)
    after = _snapshot(committed_db, match_id)
    assert after["corrections"] == before["corrections"] + 1
    assert after["version"] == before["version"] + 1
