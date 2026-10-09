"""ST-050a integration (FR-006, NFR-066 a; api-sprint-03 §4.1; ADR 0042): ``DELETE
/matches/{match_id}`` tombstones the match over the real app and Postgres, and every read of it
answers 404 at once. The purge (NFR-066 b) is ST-050b and is not exercised here.

Negative cases first: an unknown and a malformed id get the same 404 as another account's
match; a body with any key besides ``confirm`` is 422 ``unknown_field`` and changes nothing.
Then Ivy deletes: 202 ``{deleted, purge_due_by}`` with ``purge_due_by`` = the stored
``deleted_at`` + 7 days and ``Cache-Control: no-store``; the match, stats, evidence, score
sheet, video, rally media and history answer 404 and the list omits it; a scorebook command and
a second DELETE get the same 404 as a match that never existed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import sqlalchemy as sa

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver


def _strip(response: Any) -> tuple[int, Any]:
    body = response.json() if response.content else None
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        body["error"].pop("support_ref", None)
    return response.status_code, body


def _absent(api: ApiDriver, user: str) -> tuple[int, Any]:
    return _strip(st.delete_match(api, user, str(uuid.uuid4())))


def _listed(api: ApiDriver, user: str, match_id: str) -> bool:
    response = st.request(api, user, "matches")
    assert response.status_code == 200, response.text
    body = response.json()
    items = body["items"] if isinstance(body, dict) else body
    return any(item["id"] == match_id for item in items)


def test_st_050a_unknown_malformed_and_foreign_ids_get_the_same_404(
    api: ApiDriver, committed_db: Any
) -> None:
    match_id = st.tagged_example(api, "ivy", "ST-050a BOLA")
    before = st.rows_holding(committed_db, [match_id])
    foreign = st.delete_match(api, "carlos", match_id)
    method, _ = st.statscontract.path("delete_match", match_id=match_id)
    malformed = api.request(
        "carlos", method, "/matches/not-a-uuid", json=st.statscontract.CONFIRM_BODY
    )
    assert foreign.status_code == 404, foreign.text
    assert _strip(foreign) == _absent(api, "carlos") == _strip(malformed)
    assert st.rows_holding(committed_db, [match_id]) == before
    assert _listed(api, "ivy", match_id)


def test_st_050a_an_unknown_key_is_422_unknown_field_and_deletes_nothing(
    api: ApiDriver, committed_db: Any
) -> None:
    match_id = st.tagged_example(api, "ivy", "ST-050a unknown key")
    before = st.rows_holding(committed_db, [match_id])
    response = st.delete_match(api, "ivy", match_id, body={"confirm": "delete", "also": 1})
    assert st.refusal(response) == (422, "validation_failed", [(None, "unknown_field")])
    assert st.rows_holding(committed_db, [match_id]) == before
    assert _listed(api, "ivy", match_id)


def test_st_050a_delete_is_202_and_every_read_answers_404_at_once(
    api: ApiDriver, committed_db: Any
) -> None:
    match_id = st.tagged_example(api, "ivy", "ST-050a tombstone")
    rally_id = sb.sheet_body(api, "ivy", match_id)["rows"][0]["rally_id"]
    client = api.as_user("ivy")
    version = api.run(sb.version_of(client, match_id))
    started = datetime.now(UTC)

    response = st.delete_match(api, "ivy", match_id)

    assert response.status_code == 202, response.text
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert set(body) == {"deleted", "purge_due_by"}
    assert body["deleted"] is True
    with committed_db.connect() as conn:
        deleted_at = conn.execute(
            sa.text("SELECT deleted_at FROM matches WHERE id = :id"), {"id": match_id}
        ).scalar_one()
    assert started - timedelta(seconds=1) <= deleted_at <= datetime.now(UTC)
    due = (deleted_at + timedelta(days=7)).astimezone(UTC).replace(microsecond=0)
    assert body["purge_due_by"] == due.isoformat().replace("+00:00", "Z")

    reads = [
        st.statscontract.path("match", match_id=match_id),
        st.statscontract.path("stats", match_id=match_id),
        st.statscontract.path("evidence", match_id=match_id, metric_id="AN-01", side="A"),
        sb.path("sheet", match_id=match_id),
        sb.path("video", match_id=match_id),
        sb.path("media", match_id=match_id, rally_id=rally_id),
        sb.path("history", match_id=match_id),
    ]
    for method, url in reads:
        got = api.request("ivy", method, url)
        assert got.status_code == 404, f"{method} {url}: {got.status_code}"
    assert not _listed(api, "ivy", match_id)

    tag = dict(st.WORKED_EXAMPLE[0])
    command = api.run(sb.command(client, "tag", version=version, body=tag, match_id=match_id))
    assert command.status_code == 404, command.text
    assert _strip(st.delete_match(api, "ivy", match_id)) == _absent(api, "ivy")
