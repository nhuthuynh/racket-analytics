"""Mandatory regression suite: upload resume, core (IT-00-07 and resume path; testing-strategy §5;
NFR-026; AQS/STACK-06 tus 1.0.0). Never deleted. Validation and checksum come in Sprint 1."""

from __future__ import annotations

import httpx
import pytest

from tests.support import tus
from tests.support.api import sign_in
from tests.support.flows import create_match

DATA = tus.video_bytes(102_400)  # 102,400 bytes, an MP4 header first (TCR row 16)


@pytest.fixture
async def ivy(api_client: httpx.AsyncClient) -> httpx.AsyncClient:
    await sign_in(api_client, "ivy")
    return api_client


@pytest.fixture
async def upload_at_40(ivy: httpx.AsyncClient) -> tus.Upload:
    match_id = await create_match(ivy, "Resume regression")
    upload = await tus.start(ivy, match_id, len(DATA))
    response = await tus.patch(ivy, upload, 0, DATA[: len(DATA) * 40 // 100])
    assert response.status_code == 204
    return upload


async def test_head_reports_offset_and_length(
    ivy: httpx.AsyncClient, upload_at_40: tus.Upload
) -> None:
    response = await tus.head(ivy, upload_at_40)

    assert int(response.headers["Upload-Offset"]) == len(DATA) * 40 // 100
    assert int(response.headers["Upload-Length"]) == len(DATA)
    assert response.headers.get("Cache-Control") == "no-store"


@pytest.mark.parametrize("percent", [0, 30, 41, 100])
async def test_patch_at_wrong_offset_is_409_and_upload_unchanged(
    ivy: httpx.AsyncClient, upload_at_40: tus.Upload, percent: int
) -> None:
    at = len(DATA) * percent // 100

    response = await tus.patch(ivy, upload_at_40, at, DATA[at : at + 1000] or b"x")

    assert response.status_code == 409
    assert await tus.offset(ivy, upload_at_40) == len(DATA) * 40 // 100


async def test_resume_from_reported_offset_completes(
    ivy: httpx.AsyncClient, upload_at_40: tus.Upload
) -> None:
    await tus.send_all(ivy, upload_at_40, DATA, chunks=2)

    assert await tus.offset(ivy, upload_at_40) == len(DATA)


async def test_patch_beyond_declared_length_is_rejected(
    ivy: httpx.AsyncClient, upload_at_40: tus.Upload
) -> None:
    at = len(DATA) * 40 // 100

    response = await tus.patch(ivy, upload_at_40, at, DATA[at:] + b"overflow")

    assert response.status_code in (400, 409, 413)
    assert await tus.offset(ivy, upload_at_40) == at


async def test_patch_without_tus_resumable_is_412(
    ivy: httpx.AsyncClient, upload_at_40: tus.Upload
) -> None:
    at = len(DATA) * 40 // 100
    response = await ivy.patch(
        upload_at_40.url,
        content=DATA[at : at + 10],
        headers={"Upload-Offset": str(at), "Content-Type": tus.OCTET},
    )

    assert response.status_code == 412


async def test_patch_with_wrong_content_type_is_415(
    ivy: httpx.AsyncClient, upload_at_40: tus.Upload
) -> None:
    at = len(DATA) * 40 // 100
    response = await ivy.patch(
        upload_at_40.url,
        content=DATA[at : at + 10],
        headers={
            "Tus-Resumable": "1.0.0",
            "Upload-Offset": str(at),
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 415
    assert await tus.offset(ivy, upload_at_40) == at
