"""Reusable user flows for scenarios and integration tests."""

from __future__ import annotations

import httpx

from tests.support import contract, tus
from tests.support.paths import SYNTHETIC_CLIP


async def create_match(client: httpx.AsyncClient, title: str = "Skeleton test") -> str:
    response = await client.post(contract.MATCHES, json={"title": title, "format": "doubles"})
    assert response.status_code == 201, (
        f"create match failed: {response.status_code} {response.text[:200]}"
    )
    return str(response.json()["id"])


async def upload_fixture(client: httpx.AsyncClient, match_id: str, chunks: int = 3) -> tus.Upload:
    data = SYNTHETIC_CLIP.read_bytes()
    upload = await tus.start(client, match_id, len(data))
    await tus.send_all(client, upload, data, chunks=chunks)
    return upload


def percent(n: int, of: int) -> int:
    """``n`` percent of ``of`` (for slicing payloads)."""
    return of * n // 100


def percent_of(n: int, of: int) -> int:
    """What percent ``n`` is of ``of``, to the nearest whole percent (TCR row 15).

    Nearest, not floor: a slice of ``percent(40, of)`` bytes is 39.99..% of ``of``.
    """
    return (n * 200 + of) // (2 * of)
