"""Arrange for the per-account command-rate tests (IT-02-13; CI-IT0213-HANG).

A game start needs a match whose video is received. The rate tests only need that state:
they measure the rate limiter, not the upload path (IT-00-06, IT-01-06 and the upload
features do that).
"""

from __future__ import annotations

import httpx

from tests.support import scorebook as sb
from tests.support import tus
from tests.support.api import ApiDriver

# The smallest upload the content check accepts with a whole ``ftyp`` header (TCR row 16).
MINIMAL_VIDEO = tus.video_bytes(64)


async def receive_minimal_video(client: httpx.AsyncClient, match_id: str) -> None:
    """The match's video is received, through the real tus API (create, HEAD, one PATCH).
    64 bytes instead of the 1.72 MB clip: the rate tests never probe the video."""
    upload = await tus.start(client, match_id, len(MINIMAL_VIDEO))
    await tus.send_all(client, upload, MINIMAL_VIDEO, chunks=1)
    status = (await client.get(f"/matches/{match_id}")).json()["status"]
    assert status == "video_received", status


def matches_with_video(
    api: ApiDriver, client: httpx.AsyncClient, prefix: str, count: int
) -> list[str]:
    """``count`` new matches of ``client``'s user, each with its video received."""
    match_ids = [api.run(sb.create_doubles(client, f"{prefix}.{i}")) for i in range(count)]
    for match_id in match_ids:
        api.run(receive_minimal_video(client, match_id))
    return match_ids
