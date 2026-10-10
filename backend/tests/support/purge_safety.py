"""Shared helpers for the deletion and purge safety tests of PE-R3S3-03-ITS (threat notes
T-DL-3, T-DL-4, T-AC-2, T-AC-3; deletion-and-purge.md §3.3, §4.2, §4.6; ADR 0045).

Used by ``tests/integration/test_pe_r3s3_03_deletion_and_purge_safety.py`` and the API binding
``tests/features/test_deletion_and_purge_safety.py``. Everything runs over the real app,
Postgres and object store; nothing here is a fake.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import httpx
import pytest
import sqlalchemy as sa

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support import tus
from tests.support.api import ApiDriver

MIB = 1024 * 1024
PART = 5 * MIB  # the part minimum: sent to the store as multipart part 1
CHUNK = 1 * MIB  # below the part minimum: staged as an object
LENGTH = 7 * MIB  # the upload stays open after both PATCHes
STORE_CALLS = ("delete", "delete_prefix", "abort_multipart")


# ------------------------------------------------------------------ store
def store() -> Any:
    return st.OBJECT_STORE.load().from_settings()


def upload_row(engine: Any, match_id: str) -> dict[str, Any]:
    with engine.connect() as conn:
        row = (
            conn.execute(
                sa.text(
                    "SELECT id, object_key, s3_upload_id, status FROM upload_sessions "
                    "WHERE match_id::text = :m"
                ),
                {"m": match_id},
            )
            .mappings()
            .one()
        )
    return dict(row)


def staged(engine: Any, match_id: str) -> list[str]:
    upload_id = upload_row(engine, match_id)["id"]
    return sorted(store().list_keys(prefix=f"staging/{upload_id.hex}/"))


def parts(key: str, upload_id: str) -> list[int] | None:
    """Part numbers of an open multipart upload; ``None`` once it is aborted or completed."""
    s = store()
    listed = s._client.list_multipart_uploads(Bucket=s.bucket, Prefix=key)
    if upload_id not in [u["UploadId"] for u in listed.get("Uploads", [])]:
        return None
    response = s._client.list_parts(Bucket=s.bucket, Key=key, UploadId=upload_id)
    return [int(p["PartNumber"]) for p in response.get("Parts", [])]


def digests(keys: list[str]) -> dict[str, str | None]:
    """``key -> sha256`` of every stored byte (``None`` when the object is gone)."""
    s = store()
    out: dict[str, str | None] = {}
    for key in keys:
        out[key] = None if s.size_of(key) is None else hashlib.sha256(s.get_bytes(key)).hexdigest()
    return out


def holdings(engine: Any, match_id: str) -> dict[str, Any]:
    """Every stored thing of one match: original bytes, staged bytes, open parts. The key of
    an open upload is not an object yet (its bytes are parts), so it is left out."""
    with engine.connect() as conn:
        keys = [
            str(k)
            for k in conn.execute(
                sa.text("SELECT object_key FROM media_assets WHERE match_id::text = :m"),
                {"m": match_id},
            ).scalars()
        ]
        uploads = (
            conn.execute(
                sa.text(
                    "SELECT id, object_key, s3_upload_id, status FROM upload_sessions "
                    "WHERE match_id::text = :m"
                ),
                {"m": match_id},
            )
            .mappings()
            .all()
        )
    chunks: list[str] = []
    open_parts: dict[str, list[int] | None] = {}
    for upload in uploads:
        chunks += sorted(store().list_keys(prefix=f"staging/{upload['id'].hex}/"))
        if upload["status"] != "complete":
            open_parts[str(upload["id"])] = parts(upload["object_key"], upload["s3_upload_id"])
    return {"objects": digests(sorted({*keys, *chunks})), "parts": open_parts}


# ------------------------------------------------------------------ matches of one owner
def received(api: ApiDriver, user: str, title: str) -> str:
    """A match whose whole video is stored (an original)."""
    client = api.as_user(user)
    match_id = api.run(sb.create_doubles(client, title))
    api.run(sb.receive_video(client, match_id))
    return match_id


def open_upload(api: ApiDriver, user: str, title: str) -> str:
    """A match whose upload is still receiving: one multipart part, then one staged chunk."""
    client = api.as_user(user)
    match_id = api.run(sb.create_doubles(client, title))
    data = tus.video_bytes(LENGTH)
    upload = api.run(tus.start(client, match_id, len(data)))
    at = 0
    for size in (PART, CHUNK):
        response = api.run(tus.patch(client, upload, at, data[at : at + size]))
        assert response.status_code == 204, response.text
        at += size
    return match_id


def left(engine: Any, ids: list[str]) -> dict[str, int]:
    """Rows that still hold any of ``ids`` (the NFR-066 b inventory), empty when none."""
    return {k: n for k, n in st.rows_holding(engine, ids).items() if n}


# ------------------------------------------------------------------ purge
def spy_store(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, tuple[Any, ...]]]:
    """Record every deleting store call the purge makes (and still make it)."""
    store_cls = st.OBJECT_STORE.load()
    calls: list[tuple[str, tuple[Any, ...]]] = []
    for name in STORE_CALLS:
        real = getattr(store_cls, name)

        def spy(self: Any, *args: Any, _name: str = name, _real: Any = real) -> Any:
            calls.append((_name, args))
            return _real(self, *args)

        monkeypatch.setattr(store_cls, name, spy)
    return calls


def purge(capfd: pytest.CaptureFixture[str]) -> tuple[int, list[dict[str, Any]]]:
    """One ``purge --once`` pass: its exit code and its JSON log lines."""
    capfd.readouterr()
    rc = st.PURGE_MAIN.load()(["--once"])
    out, err = capfd.readouterr()
    lines = [json.loads(line) for line in (out + err).splitlines() if line.startswith("{")]
    return rc, lines


def events(lines: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
    return [r for r in lines if r.get("event") == name]


# ------------------------------------------------------------------ snapshots (T-DL-4)
def snapshot_rows(engine: Any, match_id: str) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(
                sa.text("SELECT count(*) FROM metric_snapshots WHERE match_id::text = :m"),
                {"m": match_id},
            ).scalar_one()
        )


def insert_snapshot(engine: Any, match_id: str, owner_id: str) -> None:
    """A snapshot row written straight into the table (the orphan a lost race would leave)."""
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO metric_snapshots (match_id, metric_def_version, rules_version, "
                "owner_id, sheet_version, stats, computed_at) "
                "VALUES (:m, '0.1', 'orphan-test', :o, 1, '{}'::jsonb, now())"
            ),
            {"m": match_id, "o": owner_id},
        )


@contextmanager
def held_recomputes(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[Any]]:
    """Hold every ``ScoreSheetChanged`` instead of delivering it: the after-commit recompute is
    'in flight' and is released later by calling the real consumer with the held event."""
    from racket.matches.events import ScoreSheetChanged
    from racket.platform import events as bus

    held: list[Any] = []
    monkeypatch.setitem(bus._handlers, ScoreSheetChanged, [lambda event, bind: held.append(event)])
    yield held


def release(event: Any, engine: Any) -> None:
    """Deliver one held event to the real consumer (``analytics.service.on_sheet_changed``)."""
    from racket.analytics.service import on_sheet_changed

    on_sheet_changed(event, engine)


def blocked_by(engine: Any, pid: int) -> bool:
    """True when some session waits on a lock that the backend ``pid`` holds."""
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


def wait_until(predicate: Any, within_s: float) -> bool:
    deadline = time.monotonic() + within_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


# ------------------------------------------------------------------ DELETE /me race (T-AC-2)
async def _delete_me(client: httpx.AsyncClient) -> int:
    method, url = st.statscontract.path("delete_account")
    response = await client.request(method, url, json=st.statscontract.CONFIRM_BODY)
    return int(response.status_code)


async def _create(client: httpx.AsyncClient, title: str) -> tuple[int, str | None]:
    response = await client.post("/matches", json=sb.doubles_body(title))
    match_id = str(response.json()["id"]) if response.status_code == 201 else None
    return int(response.status_code), match_id


def race_creates_against_delete_me(
    api: ApiDriver, user: str, creates: int
) -> tuple[int, list[tuple[int, str | None]]]:
    """``creates`` x ``POST /matches`` and one ``DELETE /me`` of ``user``, all in flight at
    once (``DELETE /me`` in the middle). Returns the delete status and each create's outcome."""
    client = api.as_user(user)
    half = creates // 2

    async def race() -> tuple[int, list[tuple[int, str | None]]]:
        jobs: list[Any] = [_create(client, f"race {i}") for i in range(half)]
        jobs.append(_delete_me(client))
        jobs += [_create(client, f"race {i}") for i in range(half, creates)]
        results = await asyncio.gather(*jobs)
        deleted = results.pop(half)
        return int(deleted), list(results)

    return api.run(race())


def live_matches_of_deleted_accounts(engine: Any) -> int:
    """Live matches whose owner account is tombstoned: the T-AC-2 failure, before any pass."""
    with engine.connect() as conn:
        return int(
            conn.execute(
                sa.text(
                    "SELECT count(*) FROM matches m JOIN accounts a ON a.id = m.owner_id "
                    "WHERE m.deleted_at IS NULL AND a.deleted_at IS NOT NULL"
                )
            ).scalar_one()
        )


# ------------------------------------------------------------------ rally link (T-AC-3)
def rally_link(api: ApiDriver, user: str, match_id: str, number: int = 1) -> str:
    """The presigned video link of rally ``number``, as the score sheet hands it out."""
    client = api.as_user(user)
    row = api.run(sb.sheet(client, match_id)).json()["rows"][number - 1]
    method, url = sb.path("media", match_id=match_id, rally_id=row["rally_id"])
    response = api.run(client.request(method, url))
    assert response.status_code == 200, response.text
    return str(response.json()["url"])


def fetch(url: str) -> int:
    with httpx.Client(timeout=10) as http:
        return int(http.get(url, headers={"Range": "bytes=0-15"}).status_code)
