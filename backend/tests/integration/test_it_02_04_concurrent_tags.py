"""IT-02-04 (ST-027; match-aggregate I1, optimistic version): two devices tag the same match at
the same moment with the same ``If-Match`` version. Exactly one tag is saved; the other gets
409 ``stale_match`` and nothing of it is written; a retry with the new version is saved.

The requests run in parallel through the in-process ASGI client (each on its own threadpool
thread, session and transaction), repeated 5 times.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
import sqlalchemy as sa

from tests.support import scorebook as sb
from tests.support.api import ApiDriver

TAG = {"winning_side": "A", "ending": "winner", "responsible_player": None, "fault_kind": None}


def _rallies(engine: Any, match_id: str) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(
                sa.text("SELECT count(*) FROM match_rallies WHERE match_id = :m"), {"m": match_id}
            ).scalar_one()
        )


@pytest.mark.parametrize("attempt", range(5))
def test_it_02_04_two_tags_with_the_same_version_save_exactly_one(
    api: ApiDriver, committed_db: Any, attempt: int
) -> None:
    phone, laptop = (
        api.as_user("ivy"),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
            base_url="http://testserver",
            cookies=api.as_user("ivy").cookies,
        ),
    )
    match_id = api.run(sb.create_doubles(phone, f"IT-02-04 {attempt}"))
    api.run(sb.receive_video(phone, match_id))
    api.run(sb.start_game(phone, match_id))
    version = api.run(sb.version_of(phone, match_id))

    async def both() -> list[httpx.Response]:
        one = {**TAG, "start_ms": 0, "end_ms": 1_000}
        two = {**TAG, "start_ms": 2_000, "end_ms": 3_000}
        return list(
            await asyncio.gather(
                sb.command(phone, "tag", version=version, body=one, match_id=match_id),
                sb.command(laptop, "tag", version=version, body=two, match_id=match_id),
            )
        )

    try:
        responses = api.run(both())
        codes = sorted(r.status_code for r in responses)
        assert codes == [201, 409], [(r.status_code, r.text[:200]) for r in responses]
        stale = next(r for r in responses if r.status_code == 409)
        assert stale.json()["error"]["code"] == sb.tagcontract.STALE
        assert _rallies(committed_db, match_id) == 1

        # The device that lost reloads and retries with the latest version: saved.
        latest = api.run(sb.version_of(laptop, match_id))
        retry = api.run(
            sb.command(laptop, "tag", version=latest,
                       body={**TAG, "start_ms": 4_000, "end_ms": 5_000}, match_id=match_id)
        )  # fmt: skip
        assert retry.status_code == 201, retry.text
        assert _rallies(committed_db, match_id) == 2
    finally:
        api.run(laptop.aclose())
