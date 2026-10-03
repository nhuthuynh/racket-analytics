"""Mandatory regression suite: BOLA matrix (IT-00-02; testing-strategy §5; NFR-051, FR-002;
AQS/SEC-09, AQS/SEC-03). Never deleted.

User B (Carlos) gets the same 404 as for a missing resource on every route that takes one of
user A's (Ivy's) resource IDs, and the endpoint inventory has no uncovered route.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from tests.regression.bola import MATRIX, Probe, uncovered_routes
from tests.support import contract, tus
from tests.support.api import async_client, lifespan, sign_in

pytestmark = pytest.mark.red_until(story="ST-006")


@pytest.fixture
async def users(app: Any) -> AsyncIterator[dict[str, httpx.AsyncClient]]:
    async with lifespan(app), async_client(app) as ivy, async_client(app) as carlos:
        await sign_in(ivy, "ivy")
        await sign_in(carlos, "carlos")
        yield {"ivy": ivy, "carlos": carlos}


@pytest.fixture
async def ivy_resources(users: dict[str, httpx.AsyncClient]) -> dict[str, str]:
    ivy = users["ivy"]
    created = await ivy.post(contract.MATCHES, json={"title": "BOLA target", "format": "doubles"})
    assert created.status_code == 201, created.text
    match_id = str(created.json()["id"])
    upload = await tus.start(ivy, match_id, length=1000)
    return {"match": match_id, "upload_url": upload.url}


def _url(probe: Probe, resources: dict[str, str], missing: bool) -> str:
    if probe.resource == "match":
        return probe.template.format(match_id=uuid.uuid4() if missing else resources["match"])
    url = resources["upload_url"]
    return url.rsplit("/", 1)[0] + f"/{uuid.uuid4().hex}" if missing else url


def _without_support_ref(response: httpx.Response) -> tuple[int, Any]:
    if not response.content:
        return response.status_code, b""
    body = response.json()
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        body["error"].pop("support_ref", None)
    return response.status_code, body


@pytest.mark.parametrize("probe", list(MATRIX.values()), ids=lambda p: f"{p.method} {p.template}")
async def test_other_user_gets_the_same_404_as_for_a_missing_resource(
    probe: Probe, users: dict[str, httpx.AsyncClient], ivy_resources: dict[str, str]
) -> None:
    carlos, ivy = users["carlos"], users["ivy"]

    owner = await ivy.request(probe.method, _url(probe, ivy_resources, False), **probe.kwargs())
    attacker = await carlos.request(
        probe.method, _url(probe, ivy_resources, False), **probe.kwargs()
    )
    missing = await carlos.request(probe.method, _url(probe, ivy_resources, True), **probe.kwargs())

    assert owner.status_code not in (404, 405), f"positive control failed: {owner.status_code}"
    assert attacker.status_code == 404
    assert _without_support_ref(attacker) == _without_support_ref(missing)


async def test_anonymous_caller_is_refused_on_every_id_route(
    users: dict[str, httpx.AsyncClient], ivy_resources: dict[str, str], app: Any
) -> None:
    async with async_client(app) as anonymous:
        for probe in MATRIX.values():
            response = await anonymous.request(
                probe.method, _url(probe, ivy_resources, False), **probe.kwargs()
            )
            assert response.status_code in (401, 404), f"{probe.method} {probe.template}"


def test_endpoint_inventory_has_no_route_missing_from_the_matrix(app: Any) -> None:
    assert uncovered_routes(app) == []


async def test_match_ids_are_random_uuid4(users: dict[str, httpx.AsyncClient]) -> None:
    ids = []
    for i in range(2):
        r = await users["ivy"].post(
            contract.MATCHES, json={"title": f"id {i}", "format": "singles"}
        )
        ids.append(uuid.UUID(r.json()["id"]))
    assert all(i.version == 4 for i in ids)
    assert ids[0] != ids[1]
