"""Minimal tus 1.0.0 client for tests (AQS/STACK-06). Core protocol only: creation, HEAD, PATCH."""

from __future__ import annotations

import base64
from dataclasses import dataclass

import httpx

from tests.support import contract

OCTET = "application/offset+octet-stream"


def _headers(**extra: str) -> dict[str, str]:
    return {"Tus-Resumable": contract.TUS_VERSION, **extra}


def metadata(**pairs: str) -> str:
    return ",".join(f"{k} {base64.b64encode(v.encode()).decode()}" for k, v in pairs.items())


@dataclass
class Upload:
    url: str
    length: int


async def create(
    client: httpx.AsyncClient, match_id: str, length: int, filename: str = "clip.mp4"
) -> httpx.Response:
    return await client.post(
        contract.UPLOAD_CREATE.format(match_id=match_id),
        headers=_headers(
            **{"Upload-Length": str(length), "Upload-Metadata": metadata(filename=filename)}
        ),
    )


async def start(
    client: httpx.AsyncClient, match_id: str, length: int, filename: str = "clip.mp4"
) -> Upload:
    response = await create(client, match_id, length, filename)
    assert response.status_code == 201, (
        f"tus creation failed: {response.status_code} {response.text[:200]}"
    )
    # Location may be absolute or relative; the ASGI client resolves both against its base URL.
    return Upload(url=response.headers["Location"], length=length)


async def head(client: httpx.AsyncClient, upload: Upload) -> httpx.Response:
    return await client.head(upload.url, headers=_headers())


async def offset(client: httpx.AsyncClient, upload: Upload) -> int:
    response = await head(client, upload)
    assert response.status_code in (200, 204), f"HEAD failed: {response.status_code}"
    return int(response.headers["Upload-Offset"])


async def patch(client: httpx.AsyncClient, upload: Upload, at: int, chunk: bytes) -> httpx.Response:
    return await client.patch(
        upload.url,
        content=chunk,
        headers=_headers(**{"Upload-Offset": str(at), "Content-Type": OCTET}),
    )


async def send_all(client: httpx.AsyncClient, upload: Upload, data: bytes, chunks: int = 3) -> None:
    """Send ``data`` from the server's current offset in ``chunks`` PATCH requests."""
    at = await offset(client, upload)
    size = max(1, -(-(len(data) - at) // chunks))
    while at < len(data):
        response = await patch(client, upload, at, data[at : at + size])
        assert response.status_code == 204, (
            f"PATCH at {at} failed: {response.status_code} {response.text[:200]}"
        )
        at = int(response.headers["Upload-Offset"])
