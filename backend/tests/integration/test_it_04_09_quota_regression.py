"""IT-04-09 quota regression suite (ST-072a; FR-160; NFR-023: 0 accepted requests beyond a limit).
Bursts of 50 parallel requests for one account through the in-process ASGI client (one DB
transaction each, as IT-02-11); a resumed upload counts once; flag off keeps today's limits."""

from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any

import httpx
import pytest
import sqlalchemy as sa

from tests.support import contract, tus
from tests.support.api import ApiDriver
from tests.support.flows import create_match

BURST = 50
LENGTH = 102_400


def _codes(responses: list[httpx.Response]) -> Counter[tuple[int, str | None]]:
    return Counter(
        (r.status_code, r.json()["error"]["code"] if r.status_code >= 400 else None)
        for r in responses
    )


def _count(engine: Any, sql: str) -> int:
    with engine.connect() as conn:
        return int(conn.execute(sa.text(sql)).scalar_one())


def _match_burst(api: ApiDriver) -> list[httpx.Response]:
    ivy = api.as_user("ivy")

    async def burst() -> list[httpx.Response]:
        body = {"title": "Burst", "format": "doubles"}
        posts = (ivy.post(contract.MATCHES, json=body) for _ in range(BURST))
        return list(await asyncio.gather(*posts))

    return api.run(burst())


@pytest.fixture
def env(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """``FEATURE_QUOTAS`` on unless a test's ``env`` parameter says otherwise."""
    for name, value in {"FEATURE_QUOTAS": "true", **getattr(request, "param", {})}.items():
        monkeypatch.setenv(name, str(value))


def test_it_04_09_a_burst_of_50_match_creations_accepts_exactly_10(
    env: None, api: ApiDriver, committed_db: Any
) -> None:
    responses = _match_burst(api)
    assert _codes(responses) == {(201, None): 10, (429, "rate_limited"): 40}
    assert all(r.json()["error"]["retry_at"] for r in responses if r.status_code == 429)
    assert _count(committed_db, "SELECT count(*) FROM matches") == 10


def test_it_04_09_invalid_bodies_spend_no_slot_and_the_limit_is_per_account(
    env: None, api: ApiDriver, committed_db: Any
) -> None:
    for _ in range(12):
        assert api.request("ivy", "POST", contract.MATCHES, json={"format": "x"}).status_code == 422
    assert _codes(_match_burst(api))[(201, None)] == 10
    assert api.run(create_match(api.as_user("carlos"), "Carlos's own"))


OUT_OF_THE_WAY = {"MATCH_CREATIONS_PER_HOUR": 1000, "UPLOAD_MAX_OPEN_SESSIONS": 1000,
                  "UPLOAD_CREATE_LIMIT_PER_HOUR": 1000}  # fmt: skip


@pytest.mark.parametrize("env", [{"STORAGE_QUOTA_BYTES": 10 * LENGTH, **OUT_OF_THE_WAY}],
                         indirect=True)  # fmt: skip
def test_it_04_09_a_burst_of_50_uploads_never_passes_the_storage_quota(
    env: None, api: ApiDriver, committed_db: Any
) -> None:
    ivy = api.as_user("ivy")
    match_ids = [api.run(create_match(ivy, f"Q {i}")) for i in range(BURST)]

    async def burst() -> list[httpx.Response]:
        return list(await asyncio.gather(*(tus.create(ivy, m, LENGTH) for m in match_ids)))

    responses = api.run(burst())
    assert _codes(responses) == {(201, None): 10, (429, "storage_quota_exceeded"): 40}
    declared = _count(committed_db, "SELECT coalesce(sum(length), 0) FROM upload_sessions")
    assert declared == 10 * LENGTH
    refused = next(r.json()["error"] for r in responses if r.status_code == 429)
    assert refused["quota"]["limit_bytes"] == 10 * LENGTH
    assert refused["quota"]["requested_bytes"] == LENGTH


@pytest.mark.parametrize("env", [{"STORAGE_QUOTA_BYTES": LENGTH + 1}], indirect=True)
def test_it_04_09_a_resumed_upload_is_counted_once(
    env: None, api: ApiDriver, committed_db: Any
) -> None:
    ivy = api.as_user("ivy")
    upload = api.run(tus.start(ivy, api.run(create_match(ivy, "Resumed")), LENGTH))
    data = tus.video_bytes(LENGTH)
    assert api.run(tus.patch(ivy, upload, 0, data[: LENGTH // 2])).status_code == 204
    assert api.run(tus.patch(ivy, upload, LENGTH // 2, data[LENGTH // 2 :])).status_code == 204
    assert api.run(tus.create(ivy, api.run(create_match(ivy, "Fits")), 1)).status_code == 201
    over = api.run(tus.create(ivy, api.run(create_match(ivy, "Over")), 1))
    assert over.json()["error"]["quota"] == {
        "used_bytes": LENGTH + 1, "limit_bytes": LENGTH + 1, "requested_bytes": 1
    }  # fmt: skip


@pytest.mark.parametrize("env", [{"FEATURE_QUOTAS": "false", "STORAGE_QUOTA_BYTES": 1}],
                         indirect=True)  # fmt: skip
def test_it_04_09_flag_off_keeps_todays_limits(
    env: None, api: ApiDriver, committed_db: Any
) -> None:
    responses = _match_burst(api)
    assert _codes(responses) == {(201, None): BURST}
    first = responses[0].json()["id"]
    assert api.run(tus.create(api.as_user("ivy"), first, LENGTH)).status_code == 201
