"""ST-055 review round 1 (PE-055-R1-01): the weakness ranking read neither deadlocks with
``DELETE /me`` nor makes it fail, over the real app and Postgres.

``acl.ranking_for`` reads each match's live sheet under the match row ``FOR SHARE``
(``lock_live_sheet``) and holds every one of those locks to its commit. ``DELETE /me``
tombstones the owner's matches one at a time in ascending id order (``tombstone_owned_by``).
The global lock order (deletion-and-purge.md §3.1) therefore asks the reader to lock several
match rows in ascending id order too. Here the match with the larger id is played earlier, so a
read in ``(played_on, id)`` order locks it first: ``DELETE /me`` then holds the smaller one and
waits for the larger one, the reader waits for the smaller one, and Postgres aborts one side.

The reader starts first and keeps its first row lock until ``DELETE /me`` waits on it; then it
goes on. Not an accepted test file: new, so no TCR row is needed.
"""

from __future__ import annotations

import asyncio
import threading
import time
import uuid
from datetime import date
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from racket.coaching.weakness import acl
from tests.support import stats as st
from tests.support.api import ApiDriver

pytestmark = [pytest.mark.coaching]


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


def _wait_until_blocking(engine: Any, pid: int) -> None:
    deadline = time.monotonic() + 10
    while not _blocks_someone(engine, pid):  # DELETE /me now waits on the reader
        assert time.monotonic() < deadline, "DELETE /me never waited on the ranking read"
        time.sleep(0.01)


def _two_matches_larger_id_played_first(api: ApiDriver, engine: Any) -> list[uuid.UUID]:
    ids = sorted(
        uuid.UUID(st.tagged_example(api, "ivy", f"ST-055 race {n}")) for n in range(2)
    )
    smaller, larger = ids
    with engine.begin() as conn:
        for match_id, played_on in ((larger, date(2026, 1, 1)), (smaller, date(2026, 2, 1))):
            conn.execute(
                sa.text("UPDATE matches SET played_on = :d WHERE id = :id"),
                {"d": played_on, "id": match_id},
            )
    return ids


def test_st_055_ranking_read_racing_delete_me_neither_deadlocks_nor_fails(
    api: ApiDriver, committed_db: Any
) -> None:
    """PE-055-R1-01: the ranking read locks the match rows in ascending id order, the order
    ``DELETE /me`` takes them, so ``DELETE /me`` waits for the read and then succeeds."""
    client = api.as_user("ivy")
    _two_matches_larger_id_played_first(api, committed_db)
    owner = uuid.UUID(st.me_id(api, "ivy"))
    outcome: dict[str, Any] = {}
    locked = threading.Event()

    def ranking_read() -> None:
        with Session(committed_db) as session:
            try:
                pid = session.execute(sa.text("SELECT pg_backend_pid()")).scalar_one()
                held = {"done": False}

                def hold_after_first_lock(_c: Any, _cur: Any, statement: str, *_: Any) -> None:
                    if held["done"] or "FOR SHARE" not in " ".join(statement.split()).upper():
                        return
                    held["done"] = True
                    locked.set()
                    _wait_until_blocking(committed_db, pid)

                sa.event.listen(session.connection(), "after_cursor_execute", hold_after_first_lock)
                ranking = acl.ranking_for(session, owner)
                session.commit()
                outcome["read"] = ranking.games
            except Exception as exc:  # noqa: BLE001 - the outcome is the assertion
                session.rollback()
                outcome["read"] = type(getattr(exc, "orig", exc)).__name__

    async def delete_me() -> int:
        assert await asyncio.to_thread(locked.wait, 10), "the ranking read never locked"
        response = await client.request(
            *st.statscontract.path("delete_account"), json=st.statscontract.CONFIRM_BODY
        )
        return int(response.status_code)

    async def race() -> int:
        deleted, _ = await asyncio.gather(delete_me(), asyncio.to_thread(ranking_read))
        return deleted

    outcome["delete"] = api.run(race())

    assert outcome == {"read": 2, "delete": 202}  # the read saw both matches, live
    with committed_db.connect() as conn:
        live = conn.execute(
            sa.text("SELECT count(*) FROM matches WHERE owner_id = :o AND deleted_at IS NULL"),
            {"o": owner},
        ).scalar_one()
    assert live == 0
