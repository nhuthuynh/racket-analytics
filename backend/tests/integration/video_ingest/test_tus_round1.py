"""Review round 1 regressions for the tus core (R1-01, R1-03, R1-04, R1-05, SEC-R1-02).

Real Postgres 16 and the real S3-compatible store (SeaweedFS); the app runs over httpx
ASGITransport. The object-store spy only records calls and delegates to the real store.
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import pytest
from sqlalchemy import text

from racket.platform.app import create_app
from racket.platform.db import get_session
from racket.platform.settings import Settings
from racket.platform.storage import ObjectStore
from racket.video_ingest.repository import UploadRepository
from tests.support import tus
from tests.support.api import ApiDriver, async_client, lifespan, sign_in
from tests.support.flows import create_match
from tests.support.written_keys import WrittenKeys

MIB = 1024 * 1024


class SpyStore:
    """Delegates to the real store and records the name of every method called."""

    def __init__(self, real: ObjectStore) -> None:
        self.real = real
        self.calls: list[str] = []

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self.real, name)
        if not callable(attr):
            return attr

        def record(*args: Any, **kwargs: Any) -> Any:
            self.calls.append(name)
            return attr(*args, **kwargs)

        return record


@pytest.fixture
def spy() -> SpyStore:
    return SpyStore(ObjectStore.from_settings())


@pytest.fixture
async def ivy(db_session: Any, spy: SpyStore) -> AsyncIterator[httpx.AsyncClient]:
    settings = dataclasses.replace(
        Settings.from_env(), upload_max_bytes=64 * MIB, upload_max_chunk_bytes=8 * MIB
    )
    application = create_app(settings)
    application.dependency_overrides[get_session] = lambda: db_session
    application.state.object_store = lambda: spy
    async with lifespan(application), async_client(application) as client:
        await sign_in(client, "ivy")
        yield client


def _count(db_session: Any, sql: str, **params: Any) -> int:
    return int(db_session.execute(text(sql), params).scalar_one())


# ---------------------------------------------------------------- R1-01
async def test_an_empty_patch_then_data_stores_each_byte_exactly_once(
    ivy: httpx.AsyncClient, spy: SpyStore, written_keys: WrittenKeys
) -> None:
    data = tus.video_bytes(6 * MIB, random=True)  # TCR row 16
    upload = await tus.start(ivy, await create_match(ivy, "Empty first"), len(data))

    empty = await tus.patch(ivy, upload, 0, b"")
    first = await tus.patch(ivy, upload, 0, data[: 2 * MIB])
    rest = await tus.patch(ivy, upload, 2 * MIB, data[2 * MIB :])

    assert (empty.status_code, empty.headers["Upload-Offset"]) == (204, "0")
    assert (first.status_code, first.headers["Upload-Offset"]) == (204, str(2 * MIB))
    assert (rest.status_code, rest.headers["Upload-Offset"]) == (204, str(len(data)))
    new_keys = written_keys.stored()
    assert len(new_keys) == 1, new_keys
    stored = spy.real.get_bytes(new_keys.pop())
    assert len(stored) == len(data)
    assert hashlib.sha256(stored).hexdigest() == hashlib.sha256(data).hexdigest()


async def test_an_empty_patch_while_receiving_writes_nothing(
    ivy: httpx.AsyncClient, spy: SpyStore
) -> None:
    # TCR row 16: the offset-0 chunk must hold the 12-byte content-check window, so the
    # upload is 24 bytes and the first chunk 12 (was 10 and 4); still receiving afterwards.
    data = tus.video_bytes(24)
    upload = await tus.start(ivy, await create_match(ivy, "Empty no-op"), len(data))
    assert (await tus.patch(ivy, upload, 0, data[:12])).status_code == 204
    spy.calls.clear()

    response = await tus.patch(ivy, upload, 12, b"")

    assert (response.status_code, response.headers["Upload-Offset"]) == (204, "12")
    assert spy.calls == []
    assert await tus.offset(ivy, upload) == 12


# ---------------------------------------------------------------- R1-04 / SEC-R1-02
@pytest.mark.parametrize("body", [b"", b"x"], ids=["empty", "one-byte"])
async def test_patch_on_a_completed_upload_is_409_and_touches_nothing(
    ivy: httpx.AsyncClient, spy: SpyStore, db_session: Any, body: bytes
) -> None:
    match_id = await create_match(ivy, "Done")
    data = tus.video_bytes(12)  # TCR row 16: 4 bytes can never pass the content check
    upload = await tus.start(ivy, match_id, len(data))
    assert (await tus.patch(ivy, upload, 0, data)).status_code == 204
    spy.calls.clear()

    first = await tus.patch(ivy, upload, len(data), body)
    again = await tus.patch(ivy, upload, len(data), body)

    for response in (first, again):
        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == "conflict"
    assert spy.calls == []  # no UploadPart / CompleteMultipartUpload on a finished upload
    assert await tus.offset(ivy, upload) == len(data)
    assert _count(db_session, "SELECT count(*) FROM media_assets WHERE match_id = :m",
                  m=match_id) == 1  # fmt: skip
    assert _count(db_session, "SELECT count(*) FROM jobs WHERE match_id = :m", m=match_id) == 1


# ---------------------------------------------------------------- R1-03
async def test_creation_that_loses_the_race_is_409_and_aborts_its_multipart(
    ivy: httpx.AsyncClient, spy: SpyStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both requests passed the existence check; the unique constraint decides."""
    match_id = await create_match(ivy, "Race")
    assert (await tus.create(ivy, match_id, 10)).status_code == 201
    monkeypatch.setattr(UploadRepository, "exists_for_match", lambda self, match_id: False)
    spy.calls.clear()

    loser = await tus.create(ivy, match_id, 10)

    assert loser.status_code == 409, loser.text
    assert loser.json()["error"]["code"] == "conflict"
    assert spy.calls == ["create_multipart", "abort_multipart"]
    assert (await ivy.get(f"/matches/{match_id}")).status_code == 200  # session still usable


@pytest.fixture
def committed_driver(committed_db: Any) -> Iterator[ApiDriver]:
    driver = ApiDriver(create_app())
    yield driver
    driver.close()


def test_concurrent_creations_for_one_match_are_201_and_409(
    monkeypatch: pytest.MonkeyPatch, committed_db: Any
) -> None:
    # TCR row 13: the race leaves 5 receiving uploads; the per-account quota (T-UV-7, its own
    # tests) is moved out of the way for this test only, before create_app() reads it.
    monkeypatch.setenv("UPLOAD_MAX_OPEN_SESSIONS", "10")
    monkeypatch.setenv("UPLOAD_CREATE_LIMIT_PER_HOUR", "20")
    committed_driver = ApiDriver(create_app())
    ivy = committed_driver.as_user("ivy")

    async def race() -> list[int]:
        match_id = await create_match(ivy, "Double click")
        responses = await asyncio.gather(*(tus.create(ivy, match_id, 10) for _ in range(2)))
        return sorted(r.status_code for r in responses)

    try:
        results = [committed_driver.run(race()) for _ in range(5)]
    finally:
        committed_driver.close()

    assert results == [[201, 409]] * 5


# ---------------------------------------------------------------- R1-05
def test_no_transaction_stays_open_while_a_patch_body_streams(
    committed_driver: ApiDriver, committed_db: Any
) -> None:
    ivy = committed_driver.as_user("ivy")
    match_id = committed_driver.run(create_match(ivy, "Slow"))
    upload = committed_driver.run(tus.start(ivy, match_id, 8))
    seen: list[int] = []

    def idle_in_transaction() -> int:
        with committed_db.connect() as conn:
            return int(
                conn.execute(
                    text(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
                        " AND pid <> pg_backend_pid() AND state LIKE 'idle in transaction%'"
                    )
                ).scalar_one()
            )

    async def slow_body() -> AsyncIterator[bytes]:
        yield tus.VIDEO_HEADER[:4]  # TCR row 16: bytes 4-7 are "ftyp", length still 8
        seen.append(idle_in_transaction())  # the app is now waiting for the rest of the body
        yield tus.VIDEO_HEADER[4:8]

    response = committed_driver.run(
        ivy.patch(
            upload.url,
            content=slow_body(),
            headers={
                "Tus-Resumable": "1.0.0",
                "Upload-Offset": "0",
                "Content-Type": tus.OCTET,
                "Content-Length": "8",
            },
        )
    )

    assert response.status_code == 204, response.text
    assert seen == [0]
