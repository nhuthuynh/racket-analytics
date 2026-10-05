"""IT-02-11 (QA-FUZZ, C-02; testing-strategy rule L11; NFR-023: 0 accepted requests beyond a limit).

Every limit gets a concurrency case: N requests for one owner are started together and the
limit holds exactly. The requests run in parallel through the in-process ASGI client (sync
routes run on the threadpool, each with its own database session and transaction), which is
how the C-02 race was reproduced (8 x 201 before the fix, review-rounds PE-R3R-01).

Cases:
* open-upload quota (3): 8 parallel creations on 8 matches -> exactly 3 x 201, 5 x 429
  ``upload_quota_exceeded``; the owner never has more than 3 open sessions;
* upload creation rate (10 per hour): 14 parallel creations with the quota out of the way ->
  exactly 10 x 201, 4 x 429 ``rate_limited``;
* sign-in links per address (5): 12 parallel link requests -> exactly 5 x 202, 7 x 429, and
  exactly 5 sign-in requests stored.

Positive control (rule 8): the same creations one by one give the same split, so a pass is not
just the limit answering every request.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any

import httpx
import pytest
import sqlalchemy as sa

from tests.support import tus
from tests.support.api import ApiDriver
from tests.support.flows import create_match

LENGTH = 102_400


def _open_uploads(engine: Any) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(
                sa.text("SELECT count(*) FROM upload_sessions WHERE status = 'receiving'")
            ).scalar_one()
        )


async def _create_all(client: httpx.AsyncClient, match_ids: list[str]) -> list[httpx.Response]:
    return list(await asyncio.gather(*(tus.create(client, m, LENGTH) for m in match_ids)))


def _codes(responses: list[httpx.Response]) -> Counter[tuple[int, str | None]]:
    out: Counter[tuple[int, str | None]] = Counter()
    for r in responses:
        code = r.json()["error"]["code"] if r.status_code >= 400 else None
        out[(r.status_code, code)] += 1
    return out


def _matches(api: ApiDriver, n: int) -> list[str]:
    ivy = api.as_user("ivy")
    return [api.run(create_match(ivy, f"IT-02-11 {i}")) for i in range(n)]


# ------------------------------------------------------------------ open-upload quota (C-02)
@pytest.mark.parametrize("attempt", range(5))
def test_it_02_11_parallel_upload_creations_never_pass_the_open_upload_quota(
    api: ApiDriver, committed_db: Any, attempt: int
) -> None:
    match_ids = _matches(api, 8)
    responses = api.run(_create_all(api.as_user("ivy"), match_ids))
    assert _codes(responses) == {(201, None): 3, (429, "upload_quota_exceeded"): 5}, [
        (r.status_code, r.text[:120]) for r in responses
    ]
    assert _open_uploads(committed_db) == 3


def test_it_02_11_positive_control_one_by_one_gives_the_same_split(
    api: ApiDriver, committed_db: Any
) -> None:
    ivy = api.as_user("ivy")
    responses = [api.run(tus.create(ivy, m, LENGTH)) for m in _matches(api, 8)]
    assert _codes(responses) == {(201, None): 3, (429, "upload_quota_exceeded"): 5}
    assert _open_uploads(committed_db) == 3


# ------------------------------------------------------------------ upload creation rate
@pytest.fixture
def quota_out_of_the_way(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UPLOAD_MAX_OPEN_SESSIONS", "1000")
    monkeypatch.setenv("UPLOAD_CREATE_LIMIT_PER_HOUR", "10")


def test_it_02_11_parallel_upload_creations_never_pass_the_creation_rate(
    quota_out_of_the_way: None, api: ApiDriver, committed_db: Any
) -> None:
    responses = api.run(_create_all(api.as_user("ivy"), _matches(api, 14)))
    assert _codes(responses) == {(201, None): 10, (429, "rate_limited"): 4}, [
        (r.status_code, r.text[:120]) for r in responses
    ]
    assert _open_uploads(committed_db) == 10


# ------------------------------------------------------------------ sign-in links per address
@pytest.fixture
def ip_limit_out_of_the_way(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_LINK_LIMIT_PER_IP", "1000")
    monkeypatch.setenv("AUTH_LINK_LIMIT_PER_EMAIL", "5")


def test_it_02_11_parallel_link_requests_never_pass_the_per_address_limit(
    ip_limit_out_of_the_way: None, api: ApiDriver, committed_db: Any
) -> None:
    anonymous = api.as_user("anonymous")
    body = {"email": "it-02-11@example.com"}

    async def burst() -> list[httpx.Response]:
        return list(
            await asyncio.gather(*(anonymous.post("/auth/links", json=body) for _ in range(12)))
        )

    responses = api.run(burst())
    assert _codes(responses) == {(202, None): 5, (429, "rate_limited"): 7}, [
        (r.status_code, r.text[:120]) for r in responses
    ]
    with committed_db.connect() as conn:
        stored = conn.execute(sa.text("SELECT count(*) FROM sign_in_requests")).scalar_one()
    assert stored == 5
