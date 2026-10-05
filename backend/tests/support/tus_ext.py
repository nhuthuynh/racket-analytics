"""tus checksum and expiration extensions for Sprint 1 tests (ST-017; api-sprint-01 §6).

Builds on tests/support/tus.py (core). Kept separate so the Sprint 0 helpers stay unchanged.
"""

from __future__ import annotations

import base64
import hashlib

import httpx

from tests.support import contract, tus

HEAD_BYTES = 1024 * 1024  # head_sha256 covers min(1 MiB, length) bytes (§6.3)


def checksum(chunk: bytes, algorithm: str = "sha256") -> str:
    return f"{algorithm} {base64.b64encode(hashlib.new(algorithm, chunk).digest()).decode()}"


def head_sha256(data: bytes) -> str:
    return hashlib.sha256(data[:HEAD_BYTES]).hexdigest()


async def create(
    client: httpx.AsyncClient,
    match_id: str,
    data: bytes,
    *,
    filename: str = "Sat doubles.mp4",
    length: int | None = None,
    with_head: bool = True,
) -> httpx.Response:
    meta = {"filename": filename, "last_modified": "1759480000000"}
    if with_head:
        meta["head_sha256"] = head_sha256(data)
    return await client.post(
        contract.UPLOAD_CREATE.format(match_id=match_id),
        headers={
            "Tus-Resumable": contract.TUS_VERSION,
            "Upload-Length": str(len(data) if length is None else length),
            "Upload-Metadata": tus.metadata(**meta),
        },
    )


async def start(client: httpx.AsyncClient, match_id: str, data: bytes, **kw: object) -> tus.Upload:
    response = await create(client, match_id, data, **kw)  # type: ignore[arg-type]
    assert response.status_code == 201, f"creation: {response.status_code} {response.text[:200]}"
    return tus.Upload(url=response.headers["Location"], length=len(data))


async def patch(
    client: httpx.AsyncClient, upload: tus.Upload, at: int, chunk: bytes, digest: str | None = None
) -> httpx.Response:
    headers = {
        "Tus-Resumable": contract.TUS_VERSION,
        "Upload-Offset": str(at),
        "Content-Type": tus.OCTET,
        "Upload-Checksum": digest if digest is not None else checksum(chunk),
    }
    return await client.patch(upload.url, content=chunk, headers=headers)


def first_chunk_size(data: bytes) -> int:
    """At least the head range, so the server can check head_sha256 on the offset-0 chunk."""
    return min(len(data), max(HEAD_BYTES, len(data) * 2 // 3))
