"""SEC-R2-01 / SEC-R2-02 regressions through the real routes.

Real Postgres 16 and the real S3-compatible store; the app runs over httpx ASGITransport.
A malformed integer header is a contract 4xx with the tus and security headers, the object
store is not called, and no ``http.error`` (500) line is logged.
"""

from __future__ import annotations

import dataclasses
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from racket.platform.app import create_app
from racket.platform.db import get_session
from racket.platform.settings import Settings
from racket.platform.storage import ObjectStore
from tests.support import tus
from tests.support.api import async_client, lifespan, sign_in
from tests.support.flows import create_match

MIB = 1024 * 1024
OVERLONG = b"9" * 5000
SUPERSCRIPT_TWO = b"\xb2"  # latin-1 '²': str.isdigit() is True, int() raises


class SpyStore:
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


def _assert_contract_error(response: httpx.Response, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code
    assert response.headers["Tus-Resumable"] == "1.0.0"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def _no_500_logged(caplog: pytest.LogCaptureFixture) -> None:
    assert [r for r in caplog.records if r.levelno >= logging.ERROR] == []


@pytest.mark.parametrize("raw", [OVERLONG, SUPERSCRIPT_TWO], ids=["5000-digits", "byte-0xB2"])
async def test_malformed_upload_offset_is_400_and_touches_nothing(
    ivy: httpx.AsyncClient, spy: SpyStore, caplog: pytest.LogCaptureFixture, raw: bytes
) -> None:
    upload = await tus.start(ivy, await create_match(ivy, "Offset fuzz"), 10)
    spy.calls.clear()
    caplog.set_level(logging.INFO)

    response = await ivy.patch(
        upload.url,
        content=b"x",
        headers=[
            (b"Tus-Resumable", b"1.0.0"),
            (b"Upload-Offset", raw),
            (b"Content-Type", tus.OCTET.encode()),
        ],
    )

    _assert_contract_error(response, 400, "bad_request")
    assert spy.calls == []
    _no_500_logged(caplog)
    assert await tus.offset(ivy, upload) == 0


@pytest.mark.parametrize(
    ("raw", "status", "code"),
    [
        (SUPERSCRIPT_TWO, 400, "bad_request"),
        ("١٢".encode(), 400, "bad_request"),  # UTF-8 bytes of Arabic-Indic 12
        (OVERLONG, 413, "payload_too_large"),
    ],
    ids=["byte-0xB2", "arabic-indic-utf8", "5000-digits"],
)
async def test_malformed_upload_length_is_a_contract_error_and_creates_nothing(
    ivy: httpx.AsyncClient,
    spy: SpyStore,
    caplog: pytest.LogCaptureFixture,
    raw: bytes,
    status: int,
    code: str,
) -> None:
    match_id = await create_match(ivy, "Length fuzz")
    spy.calls.clear()
    caplog.set_level(logging.INFO)

    response = await ivy.post(
        f"/matches/{match_id}/uploads",
        headers=[(b"Tus-Resumable", b"1.0.0"), (b"Upload-Length", raw)],
    )

    _assert_contract_error(response, status, code)
    assert spy.calls == []  # refused before create_multipart
    _no_500_logged(caplog)
    assert (await tus.create(ivy, match_id, 10)).status_code == 201  # the match is still free


async def test_tus_error_responses_carry_tus_resumable_even_before_sign_in(
    db_session: Any,
) -> None:
    """api-sprint-00 §6: every tus response carries Tus-Resumable, so errors do too."""
    application = create_app()
    application.dependency_overrides[get_session] = lambda: db_session
    async with lifespan(application), async_client(application) as anonymous:
        unauthenticated = await anonymous.patch(
            "/uploads/00000000-0000-0000-0000-000000000000",
            content=b"x",
            headers={"Tus-Resumable": "1.0.0", "Upload-Offset": "0", "Content-Type": tus.OCTET},
        )
        await sign_in(anonymous, "ivy")
        missing = await anonymous.head(
            "/uploads/00000000-0000-0000-0000-000000000000", headers={"Tus-Resumable": "1.0.0"}
        )

    assert (unauthenticated.status_code, missing.status_code) == (401, 404)
    for response in (unauthenticated, missing):
        assert response.headers["Tus-Resumable"] == "1.0.0"
        assert response.headers["Cache-Control"] == "no-store"
