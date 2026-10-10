"""Mandatory regression suite: BOLA matrix (IT-00-02; testing-strategy §5; NFR-051, FR-002;
AQS/SEC-09, AQS/SEC-03). Never deleted.

User B (Carlos) gets the same 404 as for a missing resource on every route that takes one of
user A's (Ivy's) resource IDs, and the endpoint inventory has no uncovered route.

The attacker calls first and the owner's positive control runs last, so a state-changing route
(``DELETE /matches/{match_id}``) is probed against the intact resource (ST-050a, TCR row
2026-10-09 in docs/sprints/03/decisions/ST-050a.md). For the Full Tag label routes both users
hold the labeller role, so the owner filter, not the role check, refuses Carlos (api-sprint-03
§5.1, SEC-S3-TM-08; ST-052c, TCR row in docs/sprints/03/decisions/ST-052c.md).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from tests.regression.bola import MATRIX, Probe, all_routes, id_routes, uncovered_routes
from tests.support import contract, scorebook, tus
from tests.support.api import async_client, lifespan, sign_in
from tests.support.stats import LABELLER_ADMIN


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
    # A second match with its video received, a game and one tagged rally, for the rally-id
    # routes (IT-02-05).
    tagged = await scorebook.create_doubles(ivy, "BOLA tagged")
    await scorebook.receive_video(ivy, tagged)
    await scorebook.start_game(ivy, tagged)
    tags = await scorebook.tag_all(ivy, tagged, list(scorebook.taglib.JOURNEY_TAGS[:1]))
    rally_id = str(tags[0].json()[scorebook.tagcontract.RALLY_ID_KEY])
    return {"match": match_id, "upload_url": upload.url, "tagged": tagged, "rally": rally_id}


async def _grant_labeller(client: httpx.AsyncClient) -> None:
    me = await client.get("/me")
    assert me.status_code == 200, me.text
    assert LABELLER_ADMIN.load()(["grant-labeller", "--account", str(me.json()["id"])]) == 0


def _url(probe: Probe, resources: dict[str, str], missing: bool) -> str:
    if probe.resource in ("match", "label"):
        return probe.template.format(match_id=uuid.uuid4() if missing else resources["match"])
    if probe.resource == "metric":
        return probe.template.format(
            match_id=uuid.uuid4() if missing else resources["match"], metric_id="AN-01"
        )
    if probe.resource == "rally":
        return probe.template.format(
            match_id=uuid.uuid4() if missing else resources["tagged"], rally_id=resources["rally"]
        )
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
    if probe.resource == "label":
        await _grant_labeller(ivy)
        await _grant_labeller(carlos)

    attacker = await carlos.request(
        probe.method, _url(probe, ivy_resources, False), **probe.kwargs()
    )
    missing = await carlos.request(probe.method, _url(probe, ivy_resources, True), **probe.kwargs())
    owner = await ivy.request(probe.method, _url(probe, ivy_resources, False), **probe.kwargs())

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


def test_endpoint_inventory_sees_every_route_of_the_app(app: Any) -> None:
    """Positive control for the inventory (BE-QA-01): it is not empty, it finds routes of
    included routers, and it finds every route the matrix probes, so a vacuous inventory can
    never pass the test above."""
    found = all_routes(app)
    assert ("POST", contract.MATCHES) in found
    assert ("GET", "/healthz") in found
    assert set(MATRIX) <= id_routes(app), sorted(set(MATRIX) - id_routes(app))


def test_a_route_without_a_probe_is_reported(app: Any) -> None:
    """Mutant check: dropping one probe from the matrix makes the inventory test fail."""
    dropped = ("GET", "/matches/{match_id}/score-sheet")
    matrix = {k: v for k, v in MATRIX.items() if k != dropped}
    assert uncovered_routes(app, matrix=matrix) == ["GET /matches/{match_id}/score-sheet"]


async def test_match_ids_are_random_uuid4(users: dict[str, httpx.AsyncClient]) -> None:
    ids = []
    for i in range(2):
        r = await users["ivy"].post(
            contract.MATCHES, json={"title": f"id {i}", "format": "singles"}
        )
        ids.append(uuid.UUID(r.json()["id"]))
    assert all(i.version == 4 for i in ids)
    assert ids[0] != ids[1]
