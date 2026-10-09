"""ST-050a integration (FR-006, NFR-066 a; api-sprint-03 §4.1; ADR 0042): ``DELETE
/matches/{match_id}`` tombstones the match over the real app and Postgres, and every read of it
answers 404 at once. The purge (NFR-066 b) is ST-050b and is not exercised here.

Negative cases first: an unknown and a malformed id get the same 404 as another account's
match; a body with any key besides ``confirm`` is 422 ``unknown_field`` and changes nothing.
Then Ivy deletes: 202 ``{deleted, purge_due_by}`` with ``purge_due_by`` = the stored
``deleted_at`` + 7 days and ``Cache-Control: no-store``; the match, stats, evidence, score
sheet, video, rally media and history answer 404 and the list omits it; a scorebook command and
a second DELETE get the same 404 as a match that never existed. A receiving upload of the
deleted match is expired under its row lock and its tus HEAD and PATCH answer the 404 of an
unknown upload (not the owner's 410 for an expired one).
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from racket.matches import public as matches_port
from racket.video_ingest.repository import MediaRepository, UploadRepository
from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support import tus
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


def test_st_050a_a_receiving_upload_of_a_deleted_match_is_expired_and_answers_404(
    api: ApiDriver, committed_db: Any
) -> None:
    client = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(client, "ST-050a upload"))
    upload = api.run(tus.start(client, match_id, length=1000))
    sent = api.run(tus.patch(client, upload, 0, tus.video_bytes(100)))
    assert sent.status_code == 204, sent.text
    missing = tus.Upload(url=upload.url.rsplit("/", 1)[0] + f"/{uuid.uuid4()}", length=1)

    assert st.delete_match(api, "ivy", match_id).status_code == 202

    with committed_db.connect() as conn:
        status, file_name = conn.execute(
            sa.text("SELECT status, file_name FROM upload_sessions WHERE match_id = :id"),
            {"id": match_id},
        ).one()
    assert (status, file_name) == ("expired", None)
    head = api.run(tus.head(client, upload))
    assert (head.status_code, head.content) == (404, api.run(tus.head(client, missing)).content)
    chunk = tus.video_bytes(100)
    patch = api.run(tus.patch(client, upload, 100, chunk))
    assert _strip(patch) == _strip(api.run(tus.patch(client, missing, 100, chunk)))
    assert patch.status_code == 404


def _blocks_someone(engine: Any, pid: int) -> bool:
    with engine.connect() as conn:
        return bool(
            conn.execute(
                sa.text(
                    "SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock'"
                    " AND :pid = ANY(pg_blocking_pids(pid))"
                ),
                {"pid": pid},
            ).scalar_one()
        )


def test_st_050a_delete_racing_the_completing_patch_neither_deadlocks_nor_fails(
    api: ApiDriver, committed_db: Any
) -> None:
    """PE-050a-01 / QA-50a-R1-01: the completing tus PATCH locks the upload row (NOWAIT), then
    the match row (``_complete`` -> ``mark_uploaded``). DELETE must take them in the same order,
    or the two deadlock and Postgres aborts one side (a 500). Here the PATCH's transaction is
    replayed with the real repository calls and held between its two locks while DELETE runs."""
    client = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(client, "ST-050a race"))
    upload = api.run(tus.start(client, match_id, length=1000))
    upload_id = uuid.UUID(upload.url.rsplit("/", 1)[1])
    outcome: dict[str, Any] = {}

    def completing_patch() -> None:
        with Session(committed_db) as session:
            try:
                pid = session.execute(sa.text("SELECT pg_backend_pid()")).scalar_one()
                row = UploadRepository(session).lock_nowait(upload_id)
                assert row is not None
                deadline = time.monotonic() + 10
                while not _blocks_someone(committed_db, pid):  # DELETE now waits on a lock
                    assert time.monotonic() < deadline, "DELETE never waited on the PATCH"
                    time.sleep(0.01)
                asset_id = MediaRepository(session).add_asset(
                    owner_id=row.owner_id, match_id=row.match_id,
                    object_key=row.object_key, size_bytes=row.length,
                )  # fmt: skip
                matches_port.mark_uploaded(session, row.match_id, row.owner_id, asset_id)
                session.commit()
                outcome["patch"] = "ok"
            except Exception as exc:  # noqa: BLE001 - the outcome is the assertion
                session.rollback()
                outcome["patch"] = type(getattr(exc, "orig", exc)).__name__

    async def race() -> int:
        deleted, _ = await asyncio.gather(
            client.request(
                *st.statscontract.path("delete_match", match_id=match_id),
                json=st.statscontract.CONFIRM_BODY,
            ),
            asyncio.to_thread(completing_patch),
        )
        return deleted.status_code

    outcome["delete"] = api.run(race())

    assert outcome == {"patch": "ok", "delete": 202}
    assert st.request(api, "ivy", "match", match_id=match_id).status_code == 404
