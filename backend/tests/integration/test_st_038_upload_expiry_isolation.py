"""ST-038 review round 1 (PE-038-01, ST038-QA-1): the upload expiry step on the local stack
(Postgres and the object store), job <-> store <-> DB. NFR-066 d; deletion-and-purge.md §4.3,
§4.4, §4.5.

Negative cases first:

1. a fresh upload (not abandoned) is neither locked nor blocked while the step frees another
   upload: a second connection takes its row ``FOR UPDATE NOWAIT`` from inside the store call
   (a tus ``PATCH`` uses ``lock_nowait`` and would otherwise answer ``OffsetMismatch``);
2. a permanent store error on one abandoned upload frees the others, keeps that upload's row
   and bytes, and logs ``purge.failed`` with ``kind=upload`` and its ``upload_id``;
3. more than a batch of uploads of deleted matches (left to the match purge) do not starve a
   live abandoned upload.

The clock is injected by moving the upload's timestamps back in the database, as in IT-03-09.
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from botocore.exceptions import ClientError

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support import tus
from tests.support.api import ApiDriver
from tests.support.paths import SYNTHETIC_CLIP

CHUNK = 1024 * 1024  # below the 5 MiB part minimum, so the bytes are staged as an object


def _upload(api: ApiDriver, title: str) -> tuple[str, tus.Upload]:
    client = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(client, title))
    data = SYNTHETIC_CLIP.read_bytes()
    upload = api.run(tus.start(client, match_id, len(data)))
    response = api.run(tus.patch(client, upload, 0, data[:CHUNK]))
    assert response.status_code == 204, response.text
    return match_id, upload


def _upload_id(engine: Any, match_id: str) -> uuid.UUID:
    with engine.connect() as conn:
        return uuid.UUID(
            str(
                conn.execute(
                    sa.text("SELECT id FROM upload_sessions WHERE match_id::text = :m"),
                    {"m": match_id},
                ).scalar_one()
            )
        )


def _age(engine: Any, match_id: str, by: timedelta) -> None:
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "UPDATE upload_sessions SET created_at = created_at - :d, "
                "updated_at = updated_at - :d WHERE match_id::text = :m"
            ),
            {"d": by, "m": match_id},
        )


def _staged(upload_id: uuid.UUID) -> list[str]:
    return list(
        st.OBJECT_STORE.load().from_settings().list_keys(prefix=f"staging/{upload_id.hex}/")
    )


def _row_count(engine: Any, upload_id: uuid.UUID) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(
                sa.text("SELECT count(*) FROM upload_sessions WHERE id = :u"), {"u": upload_id}
            ).scalar_one()
        )


def _purge_once() -> int:
    return int(st.PURGE_MAIN.load()(["--once"]))


def test_st_038_a_fresh_upload_is_neither_locked_nor_blocked_during_the_step(
    api: ApiDriver, committed_db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    old_match, _ = _upload(api, "ST-038 idle")
    fresh_match, fresh = _upload(api, "ST-038 fresh")
    old_id, fresh_id = _upload_id(committed_db, old_match), _upload_id(committed_db, fresh_match)
    _age(committed_db, old_match, timedelta(hours=25))

    store_cls = st.OBJECT_STORE.load()
    real_abort = store_cls.abort_multipart
    probes: list[str] = []

    def probing_abort(self: Any, key: str, s3_upload_id: str) -> None:
        # inside the step, while the idle upload is being freed
        with committed_db.connect() as conn, conn.begin():
            try:
                conn.execute(
                    sa.text("SELECT id FROM upload_sessions WHERE id = :u FOR UPDATE NOWAIT"),
                    {"u": fresh_id},
                ).all()
                probes.append("free")
            except sa.exc.OperationalError as exc:
                probes.append(type(exc.orig).__name__)
        real_abort(self, key, s3_upload_id)

    monkeypatch.setattr(store_cls, "abort_multipart", probing_abort)
    assert _purge_once() == 0
    assert probes == ["free"], f"the fresh upload's row was locked during the step: {probes}"
    assert _row_count(committed_db, old_id) == 0, "positive control: the idle upload is freed"
    assert _row_count(committed_db, fresh_id) == 1
    assert api.run(tus.offset(api.as_user("ivy"), fresh)) == CHUNK


def test_st_038_a_store_failure_on_one_upload_does_not_stop_the_others(
    api: ApiDriver,
    committed_db: Any,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    bad_match, _ = _upload(api, "ST-038 store refuses")
    good_match, _ = _upload(api, "ST-038 freed")
    bad_id, good_id = _upload_id(committed_db, bad_match), _upload_id(committed_db, good_match)
    _age(committed_db, bad_match, timedelta(hours=30))  # the oldest: listed first on every pass
    _age(committed_db, good_match, timedelta(hours=25))
    bad_staged = _staged(bad_id)
    assert bad_staged, "positive control: the failing upload has staged bytes"
    assert _staged(good_id), "positive control: the other upload has staged bytes"

    bad_keys = _keys_of(committed_db, bad_id)
    store_cls = st.OBJECT_STORE.load()
    real_abort = store_cls.abort_multipart

    def refusing_abort(self: Any, key: str, s3_upload_id: str) -> None:
        if key in bad_keys:  # a permanent error for this upload only
            raise ClientError({"Error": {"Code": "AccessDenied", "Message": "x"}}, "Abort")
        real_abort(self, key, s3_upload_id)

    monkeypatch.setattr(store_cls, "abort_multipart", refusing_abort)
    caplog.set_level(logging.INFO, logger="racket.purge")
    assert _purge_once() == 1, "the failed upload makes the pass exit 1"

    assert _row_count(committed_db, good_id) == 0, "the other abandoned upload is freed"
    assert _staged(good_id) == []
    assert _row_count(committed_db, bad_id) == 1, "the failed upload keeps its row (no orphan)"
    assert _staged(bad_id) == bad_staged
    failed = [r for r in caplog.records if getattr(r, "event", "") == "purge.failed"]
    assert [(r.kind, getattr(r, "upload_id", None), r.error) for r in failed] == [
        ("upload", str(bad_id), "ClientError")
    ]


def _keys_of(engine: Any, upload_id: uuid.UUID) -> list[str]:
    with engine.connect() as conn:
        return [
            str(k)
            for k in conn.execute(
                sa.text("SELECT object_key FROM upload_sessions WHERE id = :u"), {"u": upload_id}
            ).scalars()
        ]


def _columns(conn: Any, table: str) -> list[str]:
    return [
        str(c)
        for c in conn.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = :t "
                "ORDER BY ordinal_position"
            ),
            {"t": table},
        ).scalars()
    ]


def _clone_as_deleted(engine: Any, match_id: str, copies: int, older_by: timedelta) -> None:
    """``copies`` deleted matches, each with an expired upload older than the live one (rows
    copied from the live match; each gets its own ids and original key)."""
    with engine.begin() as conn:
        m_cols, u_cols = _columns(conn, "matches"), _columns(conn, "upload_sessions")
        m_over = {"id": ":mid", "deleted_at": "now()"}
        u_over = {
            "id": ":uid",
            "match_id": ":mid",
            "object_key": ":key",
            "status": "'expired'",
            "updated_at": "updated_at - :d",
            "created_at": "created_at - :d",
            "file_name": "NULL",
        }
        m_sql = (
            f"INSERT INTO matches ({', '.join(m_cols)}) SELECT "
            + ", ".join(m_over.get(c, c) for c in m_cols)
            + " FROM matches WHERE id::text = :src"
        )
        u_sql = (
            f"INSERT INTO upload_sessions ({', '.join(f'{chr(34)}{c}{chr(34)}' for c in u_cols)}) "
            "SELECT "
            + ", ".join(u_over.get(c, f'"{c}"') for c in u_cols)
            + " FROM upload_sessions WHERE match_id::text = :src"
        )
        for _ in range(copies):
            mid, uid = uuid.uuid4(), uuid.uuid4()
            conn.execute(sa.text(m_sql), {"mid": mid, "src": match_id})
            conn.execute(
                sa.text(u_sql),
                {"mid": mid, "uid": uid, "key": f"originals/{uuid.uuid4().hex}", "d": older_by,
                 "src": match_id},
            )  # fmt: skip


def test_st_038_uploads_of_deleted_matches_do_not_starve_a_live_abandoned_upload(
    api: ApiDriver, committed_db: Any
) -> None:
    live_match, _ = _upload(api, "ST-038 live abandoned")
    live_id = _upload_id(committed_db, live_match)
    _age(committed_db, live_match, timedelta(hours=25))
    _clone_as_deleted(committed_db, live_match, copies=101, older_by=timedelta(hours=24))
    with committed_db.connect() as conn:
        waiting = conn.execute(
            sa.text("SELECT count(*) FROM upload_sessions WHERE status = 'expired'")
        ).scalar_one()
    assert waiting == 101, "positive control: more than one batch is ahead of the live upload"

    _purge_once()  # the deleted matches are the match purge's; its exit code is not the point
    assert _row_count(committed_db, live_id) == 0, "the live abandoned upload was starved"
    assert _staged(live_id) == []
