"""IT-03-09 (ST-038; FR-024, NFR-066 d, ADR 0006): scheduler <-> store <-> DB, abandoned uploads.

Replaces IT-02-07 (ST-038 is committed in Sprint 3 and runs on the ST-050 purge job). The clock
is injected by moving the upload's timestamps back in the database (the job reads the stored
times; nothing else changes). Order of the TDD plan (sprint-03 §5 ``UploadExpiryPolicy``):

1. idle 23 h 59 min -> not expired: still resumable, bytes kept;
2. idle 24 h -> expired by one purge pass: HEAD and PATCH refused (404 or 410), the staged bytes
   and the multipart upload freed, the upload no longer offered for resume;
3. a completed upload is never expired by this rule.

Written red first (QA-ACC-3): ``red_until`` ST-038.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
import sqlalchemy as sa

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support import tus
from tests.support.api import ApiDriver
from tests.support.paths import SYNTHETIC_CLIP

pytestmark = [pytest.mark.red_until(story="ST-038")]

CHUNK = 1024 * 1024  # below the 5 MiB part minimum, so the bytes are staged as an object


def _staged(engine: Any, match_id: str) -> list[str]:
    """Staged chunk objects of the match's upload (``staging/<upload id>/<offset>``)."""
    with engine.connect() as conn:
        ids = (
            conn.execute(
                sa.text("SELECT id FROM upload_sessions WHERE match_id::text = :m"), {"m": match_id}
            )
            .scalars()
            .all()
        )
    store = st.OBJECT_STORE.load().from_settings()
    return [k for i in ids for k in store.list_keys(prefix=f"staging/{i.hex}/")]


def _abandoned(api: ApiDriver, title: str) -> tuple[str, tus.Upload]:
    client = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(client, title))
    data = SYNTHETIC_CLIP.read_bytes()
    upload = api.run(tus.start(client, match_id, len(data)))
    response = api.run(tus.patch(client, upload, 0, data[:CHUNK]))
    assert response.status_code == 204, response.text
    return match_id, upload


def _age(engine: Any, match_id: str, by: timedelta) -> None:
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "UPDATE upload_sessions SET created_at = created_at - :d, "
                "updated_at = updated_at - :d WHERE match_id::text = :m"
            ),
            {"d": by, "m": match_id},
        )


def test_it_03_09_an_upload_idle_for_23h59_is_kept(api: ApiDriver, committed_db: Any) -> None:
    match_id, upload = _abandoned(api, "IT-03-09 kept")
    staged = _staged(committed_db, match_id)
    assert staged, "positive control: the first chunk is staged in the store"
    _age(committed_db, match_id, timedelta(hours=23, minutes=59))
    st.run_purge_once()
    assert api.run(tus.offset(api.as_user("ivy"), upload)) == CHUNK
    assert _staged(committed_db, match_id) == staged


def test_it_03_09_an_upload_idle_for_24h_is_expired_and_its_bytes_freed(
    api: ApiDriver, committed_db: Any
) -> None:
    match_id, upload = _abandoned(api, "IT-03-09 expired")
    with committed_db.connect() as conn:
        upload_ids = (
            conn.execute(
                sa.text("SELECT id FROM upload_sessions WHERE match_id::text = :m"), {"m": match_id}
            )
            .scalars()
            .all()
        )
    assert _staged(committed_db, match_id), "positive control: the first chunk is staged"
    _age(committed_db, match_id, timedelta(hours=24))
    st.run_purge_once()
    client = api.as_user("ivy")
    assert api.run(tus.head(client, upload)).status_code in (404, 410)
    assert api.run(tus.patch(client, upload, CHUNK, b"x" * 16)).status_code in (404, 410)
    with committed_db.connect() as conn:
        open_sessions = conn.execute(
            sa.text("SELECT count(*) FROM upload_sessions WHERE match_id::text = :m"),
            {"m": match_id},
        ).scalar_one()
    assert open_sessions == 0
    store = st.OBJECT_STORE.load().from_settings()
    assert [k for i in upload_ids for k in store.list_keys(prefix=f"staging/{i.hex}/")] == []
    match = api.request("ivy", "GET", f"/matches/{match_id}").json()
    assert match.get("upload") in (None, {}), f"the expired upload is still offered: {match}"


def test_it_03_09_a_completed_upload_never_expires(api: ApiDriver, committed_db: Any) -> None:
    client = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(client, "IT-03-09 complete"))
    api.run(sb.receive_video(client, match_id))
    keys = st.object_keys_of(committed_db, match_id)
    _age(committed_db, match_id, timedelta(days=30))
    with committed_db.begin() as conn:
        conn.execute(
            sa.text(
                "UPDATE media_assets SET created_at = created_at - interval '30 days' "
                "WHERE match_id::text = :m"
            ),
            {"m": match_id},
        )
    st.run_purge_once()
    assert api.request("ivy", "GET", f"/matches/{match_id}").json()["status"] == "video_received"
    assert st.keys_still_stored(keys) == keys
