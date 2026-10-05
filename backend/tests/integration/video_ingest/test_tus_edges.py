"""tus core edge cases beyond the QA suites (ST-008; ADR 0011 "Confirmation"; api-sprint-00 §6).

Real Postgres and the real S3-compatible store; the app runs over httpx ASGITransport.
"""

from __future__ import annotations

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
from tests.support import tus
from tests.support.api import async_client, lifespan, sign_in
from tests.support.flows import create_match

MIB = 1024 * 1024


def _app(db_session: Any, **overrides: Any) -> Any:
    settings = dataclasses.replace(Settings.from_env(), **overrides)
    application = create_app(settings)
    application.dependency_overrides[get_session] = lambda: db_session
    return application


@pytest.fixture
async def ivy(db_session: Any) -> AsyncIterator[httpx.AsyncClient]:
    application = _app(db_session, upload_max_bytes=64 * MIB, upload_max_chunk_bytes=8 * MIB)
    async with lifespan(application), async_client(application) as client:
        await sign_in(client, "ivy")
        yield client


async def _create(client: httpx.AsyncClient, match_id: str, **headers: str) -> httpx.Response:
    return await client.post(f"/matches/{match_id}/uploads", headers=headers)


# ---------------------------------------------------------------- creation
async def test_discovery_lists_version_extension_and_max_size(ivy: httpx.AsyncClient) -> None:
    response = await ivy.options("/uploads")

    assert response.status_code == 204
    assert response.headers["Tus-Version"] == "1.0.0"
    assert response.headers["Tus-Extension"] == "creation,checksum,expiration"  # TCR row 12
    assert response.headers["Tus-Checksum-Algorithm"] == "sha256,sha1"
    assert response.headers["Tus-Max-Size"] == str(64 * MIB)


@pytest.mark.parametrize(
    ("headers", "status"),
    [
        ({"Upload-Length": "10"}, 412),  # no Tus-Resumable
        ({"Tus-Resumable": "0.2.2", "Upload-Length": "10"}, 412),
        ({"Tus-Resumable": "1.0.0"}, 400),  # no Upload-Length
        ({"Tus-Resumable": "1.0.0", "Upload-Length": "0"}, 400),
        ({"Tus-Resumable": "1.0.0", "Upload-Length": "-5"}, 400),
        ({"Tus-Resumable": "1.0.0", "Upload-Length": "ten"}, 400),
        ({"Tus-Resumable": "1.0.0", "Upload-Length": str(64 * MIB + 1)}, 413),
        ({"Tus-Resumable": "1.0.0", "Upload-Length": "10", "Upload-Metadata": "a b c"}, 400),
        ({"Tus-Resumable": "1.0.0", "Upload-Length": "10", "Upload-Metadata": "k !!"}, 400),
        ({"Tus-Resumable": "1.0.0", "Upload-Length": "10", "Upload-Metadata": "k" * 1025}, 400),
    ],
)
async def test_bad_creation_headers_are_refused(
    ivy: httpx.AsyncClient, headers: dict[str, str], status: int
) -> None:
    match_id = await create_match(ivy, "Creation edges")

    response = await _create(ivy, match_id, **headers)

    assert response.status_code == status
    match = (await ivy.get(f"/matches/{match_id}")).json()
    assert match["status"] == "awaiting_upload"


async def test_second_upload_for_a_match_is_a_conflict(ivy: httpx.AsyncClient) -> None:
    match_id = await create_match(ivy, "One upload")
    first = await tus.create(ivy, match_id, 10)

    second = await tus.create(ivy, match_id, 10)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"


async def test_creation_marks_the_match_uploading(ivy: httpx.AsyncClient) -> None:
    match_id = await create_match(ivy, "Uploading")

    await tus.start(ivy, match_id, 10)

    assert (await ivy.get(f"/matches/{match_id}")).json()["status"] == "uploading"


async def test_malformed_ids_look_like_missing_ones(ivy: httpx.AsyncClient) -> None:
    for url in ("/matches/not-a-uuid", "/uploads/not-a-uuid"):
        method = "GET" if url.startswith("/matches") else "HEAD"
        response = await ivy.request(method, url, headers={"Tus-Resumable": "1.0.0"})
        assert response.status_code == 404


# ---------------------------------------------------------------- PATCH
@pytest.mark.parametrize(
    ("offset", "status"), [("", 400), ("-1", 400), ("1e3", 400), ("0x10", 400)]
)
async def test_non_integer_offset_is_400(ivy: httpx.AsyncClient, offset: str, status: int) -> None:
    upload = await tus.start(ivy, await create_match(ivy, "Offsets"), 10)

    response = await ivy.patch(
        upload.url,
        content=b"x",
        headers={"Tus-Resumable": "1.0.0", "Upload-Offset": offset, "Content-Type": tus.OCTET},
    )

    assert response.status_code == status
    assert await tus.offset(ivy, upload) == 0


async def test_chunk_above_the_chunk_limit_is_413(ivy: httpx.AsyncClient) -> None:
    upload = await tus.start(ivy, await create_match(ivy, "Big chunk"), 9 * MIB)

    response = await tus.patch(ivy, upload, 0, b"x" * (8 * MIB + 1))

    assert response.status_code == 413
    assert await tus.offset(ivy, upload) == 0


async def test_head_and_patch_answer_with_tus_resumable(ivy: httpx.AsyncClient) -> None:
    data = tus.video_bytes(12)  # TCR row 16: 4 bytes can never pass the content check
    upload = await tus.start(ivy, await create_match(ivy, "Headers"), len(data))

    head = await tus.head(ivy, upload)
    patch = await tus.patch(ivy, upload, 0, data)

    assert head.headers["Tus-Resumable"] == "1.0.0"
    assert patch.headers["Tus-Resumable"] == "1.0.0"
    assert patch.headers["Upload-Offset"] == str(len(data))


async def test_mixed_staged_and_multipart_parts_store_identical_bytes(
    ivy: httpx.AsyncClient,
) -> None:
    """2 MiB chunks are staged until a >= 5 MiB part can be written; the last part is short."""
    data = tus.video_bytes(13 * MIB + 123, random=True)  # TCR row 16
    store = ObjectStore.from_settings()
    before = set(store.list_keys())
    upload = await tus.start(ivy, await create_match(ivy, "Parts"), len(data))

    at = 0
    while at < len(data):
        response = await tus.patch(ivy, upload, at, data[at : at + 2 * MIB])
        assert response.status_code == 204, response.text
        at = int(response.headers["Upload-Offset"])

    new_keys = set(store.list_keys()) - before
    assert len(new_keys) == 1, new_keys  # staging objects are gone; one original remains
    stored = store.get_bytes(new_keys.pop())
    assert hashlib.sha256(stored).digest() == hashlib.sha256(data).digest()


# ---------------------------------------------------------------- concurrency (ADR 0011 step 3)
@pytest.fixture
def committed_ivy(committed_db: Any) -> Iterator[tuple[Any, httpx.AsyncClient]]:
    from tests.support.api import ApiDriver

    driver = ApiDriver(create_app())
    yield driver, driver.as_user("ivy")
    driver.close()


def test_patch_while_another_patch_holds_the_row_is_409_and_unchanged(
    committed_ivy: tuple[Any, httpx.AsyncClient], committed_db: Any
) -> None:
    driver, ivy = committed_ivy
    upload = driver.run(tus.start(ivy, driver.run(create_match(ivy, "Concurrent")), 10))
    upload_id = upload.url.rsplit("/", 1)[1]

    with committed_db.connect() as other:
        other.execute(
            text("SELECT id FROM upload_sessions WHERE id = :id FOR UPDATE"), {"id": upload_id}
        )
        response = driver.run(tus.patch(ivy, upload, 0, b"0123456789"))
        other.rollback()

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "upload_offset_mismatch"
    assert driver.run(tus.offset(ivy, upload)) == 0
