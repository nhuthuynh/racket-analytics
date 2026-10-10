"""ST-051 review round 1 (PE-051-01, SQA-051-01, PE-051-02): ``DELETE /me`` over the real app
and Postgres neither deadlocks with the transactions that race it nor leaves a sign-in link.

The global lock order is the account row, then the match's upload row, then the match row
(deletion-and-purge.md §3.1, §3.3 (1)). Each race below replays the other transaction with the
real service or repository calls. ``DELETE /me`` starts once that transaction holds its first
row lock, which it keeps until ``DELETE /me`` waits on it; then it goes on. Out of order,
Postgres finds a deadlock and aborts one side (``DELETE /me`` answers 500).

1. The completing tus ``PATCH`` holds the upload row, then marks the match uploaded.
2. An upload creation that replaces an expired upload of the match (``UploadService.create``).
3. SEC-S3-TM-06 (T-AC-3): a link and a link request of the address, made before ``DELETE /me``,
   are gone after it, and the link signs in to nothing; another address's rows are untouched.

Not an accepted test file: new, so no TCR row is needed.
"""

from __future__ import annotations

import asyncio
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from racket.matches import public as matches_port
from racket.players.domain import MagicLinkToken
from racket.players.service import AccountDeletion, LinkRefused, MagicLinkService
from racket.video_ingest.repository import MediaRepository, UploadRepository
from racket.video_ingest.service import UploadService
from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support import tus
from tests.support.api import ApiDriver


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


async def _delete_me_once(client: Any, locked: threading.Event) -> int:
    """``DELETE /me`` once the racing transaction holds its first row lock."""
    assert await asyncio.to_thread(locked.wait, 10), "the racing transaction never locked"
    return await _delete_me(client)


def _wait_until_blocking(engine: Any, pid: int) -> None:
    deadline = time.monotonic() + 10
    while not _blocks_someone(engine, pid):  # DELETE /me now waits on this transaction
        assert time.monotonic() < deadline, "DELETE /me never waited on the racing transaction"
        time.sleep(0.01)


async def _delete_me(client: Any) -> int:
    response = await client.request(
        *st.statscontract.path("delete_account"), json=st.statscontract.CONFIRM_BODY
    )
    return int(response.status_code)


def test_st_051_delete_me_racing_the_completing_patch_neither_deadlocks_nor_fails(
    api: ApiDriver, committed_db: Any
) -> None:
    """SQA-051-01: the PATCH locks the upload row, then the match row; ``DELETE /me`` must take
    each match's upload row before the match row, as ``DELETE /matches/{id}`` does."""
    client = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(client, "ST-051 patch race"))
    upload = api.run(tus.start(client, match_id, length=1000))
    upload_id = uuid.UUID(upload.url.rsplit("/", 1)[1])
    outcome: dict[str, Any] = {}
    locked = threading.Event()

    def completing_patch() -> None:
        with Session(committed_db) as session:
            try:
                pid = session.execute(sa.text("SELECT pg_backend_pid()")).scalar_one()
                row = UploadRepository(session).lock_nowait(upload_id)
                assert row is not None
                locked.set()
                _wait_until_blocking(committed_db, pid)
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
            _delete_me_once(client, locked), asyncio.to_thread(completing_patch)
        )
        return deleted

    outcome["delete"] = api.run(race())

    assert outcome == {"patch": "ok", "delete": 202}
    with committed_db.connect() as conn:
        live = conn.execute(
            sa.text("SELECT count(*) FROM matches WHERE id = :id AND deleted_at IS NULL"),
            {"id": match_id},
        ).scalar_one()
    assert live == 0


def test_st_051_delete_me_racing_an_upload_creation_that_replaces_an_expired_one(
    api: ApiDriver, committed_db: Any
) -> None:
    """PE-051-01: the creation must take the account row ``FOR SHARE`` before it locks the
    expired upload row it replaces (§3.3 (1)); ``DELETE /me`` holds the account row
    ``FOR UPDATE`` and then locks the same upload row."""
    client = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(client, "ST-051 creation race"))
    api.run(tus.start(client, match_id, length=1000))
    owner_id = uuid.UUID(st.me_id(api, "ivy"))
    with committed_db.begin() as conn:  # the upload is past its expiry; a creation replaces it
        conn.execute(
            sa.text("UPDATE upload_sessions SET expires_at = :t WHERE match_id = :m"),
            {"t": datetime.now(UTC) - timedelta(hours=1), "m": match_id},
        )
    state = api.app.state
    outcome: dict[str, Any] = {}
    locked = threading.Event()

    def creation() -> None:
        with Session(committed_db) as session:
            try:
                pid = session.execute(sa.text("SELECT pg_backend_pid()")).scalar_one()
                held = {"done": False}

                def hold_after_first_lock(_c: Any, _cur: Any, statement: str, *_: Any) -> None:
                    sql = " ".join(statement.split()).upper()
                    if held["done"] or not ("FOR UPDATE" in sql or "FOR SHARE" in sql):
                        return
                    held["done"] = True
                    locked.set()
                    _wait_until_blocking(committed_db, pid)

                sa.event.listen(session.connection(), "after_cursor_execute", hold_after_first_lock)
                UploadService(session, state.object_store(), state.settings).create(
                    owner_id=owner_id, raw_match_id=match_id, upload_length="1000",
                    upload_metadata=None, route="/matches/{match_id}/uploads", method="POST",
                )  # fmt: skip
                outcome["create"] = "ok"
            except Exception as exc:  # noqa: BLE001 - the outcome is the assertion
                session.rollback()
                outcome["create"] = type(getattr(exc, "orig", exc)).__name__

    async def race() -> int:
        deleted, _ = await asyncio.gather(
            _delete_me_once(client, locked), asyncio.to_thread(creation)
        )
        return deleted

    outcome["delete"] = api.run(race())

    assert outcome == {"create": "ok", "delete": 202}
    with committed_db.connect() as conn:
        live = conn.execute(
            sa.text("SELECT count(*) FROM matches WHERE owner_id = :o AND deleted_at IS NULL"),
            {"o": owner_id},
        ).scalar_one()
        receiving = conn.execute(
            sa.text(
                "SELECT count(*) FROM upload_sessions WHERE owner_id = :o AND status = 'receiving'"
            ),
            {"o": owner_id},
        ).scalar_one()
    assert (live, receiving) == (0, 0)


def _account_with_address(engine: Any, email: str, key: str) -> uuid.UUID:
    account_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO accounts (id, email, email_key, display_name, created_at) "
                "VALUES (:id, :e, :k, 'Ivy', now())"
            ),
            {"id": account_id, "e": email, "k": key},
        )
    return account_id


def _link_and_request(engine: Any, email: str, key: str) -> str:
    token = f"st051-{uuid.uuid4().hex}"
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO sign_in_links (token_sha256, email_key, email, created_at, expires_at)"
                " VALUES (:d, :k, :e, now(), now() + interval '15 minutes')"
            ),
            {"d": MagicLinkToken.digest_of(token), "k": key, "e": email},
        )
        conn.execute(
            sa.text(
                "INSERT INTO sign_in_requests (id, email, email_key, created_at)"
                " VALUES (:id, :e, :k, now())"
            ),
            {"id": uuid.uuid4(), "e": email, "k": key},
        )
    return token


def _sign_in_rows(engine: Any, email: str, key: str) -> dict[str, int]:
    with engine.connect() as conn:
        return {
            table: int(
                conn.execute(
                    sa.text(f"SELECT count(*) FROM {table} WHERE email = :e OR email_key = :k"),
                    {"e": email, "k": key},
                ).scalar_one()
            )
            for table in ("sign_in_links", "sign_in_requests")
        }


def test_st_051_a_link_requested_before_delete_me_is_gone_and_signs_in_to_nothing(
    api: ApiDriver, committed_db: Any
) -> None:
    """PE-051-02, SEC-S3-TM-06 (T-AC-3; §3.2 step 4): the links and requests of the address are
    deleted before the address is nulled; another address's rows stay."""
    ivy = ("ivy.st051@example.test", "a" * 64)
    carlos = ("carlos.st051@example.test", "c" * 64)
    me = _account_with_address(committed_db, *ivy)
    _account_with_address(committed_db, *carlos)
    token = _link_and_request(committed_db, *ivy)
    _link_and_request(committed_db, *carlos)
    assert _sign_in_rows(committed_db, *ivy) == {"sign_in_links": 1, "sign_in_requests": 1}

    with Session(committed_db) as session:
        AccountDeletion(session).delete(me, st.statscontract.CONFIRM_BODY)

    assert _sign_in_rows(committed_db, *ivy) == {"sign_in_links": 0, "sign_in_requests": 0}
    assert _sign_in_rows(committed_db, *carlos) == {"sign_in_links": 1, "sign_in_requests": 1}
    before = _accounts_and_sessions(committed_db)
    with Session(committed_db) as session, pytest.raises(LinkRefused):
        MagicLinkService(session, api.app.state.settings).exchange(token, "203.0.113.9", None)
    assert _accounts_and_sessions(committed_db) == before  # no account, no session


def _accounts_and_sessions(engine: Any) -> tuple[int, int]:
    with engine.connect() as conn:
        accounts = conn.execute(sa.text("SELECT count(*) FROM accounts")).scalar_one()
        sessions = conn.execute(sa.text("SELECT count(*) FROM sessions")).scalar_one()
    return int(accounts), int(sessions)
