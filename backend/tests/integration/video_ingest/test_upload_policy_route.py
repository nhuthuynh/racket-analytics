"""``GET /upload-policy`` (ST-017/ST-018; api-sprint-01 §6.1): caps and chunk bounds come from
configuration; signed-in users only."""

from __future__ import annotations

import httpx

from tests.support.api import sign_in


async def test_anonymous_gets_401(api_client: httpx.AsyncClient) -> None:
    assert (await api_client.get("/upload-policy")).status_code == 401


async def test_the_policy_reflects_the_configuration(api_client: httpx.AsyncClient) -> None:
    await sign_in(api_client, "ivy")
    response = await api_client.get("/upload-policy")
    assert response.status_code == 200
    assert response.json() == {
        "max_bytes": 10_000_000_000,
        "max_duration_ms": 9_000_000,
        "containers": ["mp4", "mov"],
        "video_codecs": ["h264", "hevc"],
        "chunk_min_bytes": 5_242_880,
        "chunk_max_bytes": 8_388_608,
        "checksum_algorithms": ["sha256", "sha1"],
        "expires_after_s": 86_400,
    }
    assert "Tus-Resumable" not in response.headers
