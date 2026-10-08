"""Arrange for the per-account command-rate tests (IT-02-13; CI-IT0213-HANG).

A game start needs a match whose video is received. The rate tests only need that state:
they measure the rate limiter, not the upload path (IT-00-06, IT-01-06 and the upload
features do that).
"""

from __future__ import annotations

import httpx

from tests.support import scorebook as sb
from tests.support.api import ApiDriver


async def receive_minimal_video(client: httpx.AsyncClient, match_id: str) -> None:
    """The match's video is received, through the real tus API."""
    await sb.receive_video(client, match_id)


def matches_with_video(
    api: ApiDriver, client: httpx.AsyncClient, prefix: str, count: int
) -> list[str]:
    """``count`` new matches of ``client``'s user, each with its video received."""
    match_ids = [api.run(sb.create_doubles(client, f"{prefix}.{i}")) for i in range(count)]
    for match_id in match_ids:
        api.run(receive_minimal_video(client, match_id))
    return match_ids
