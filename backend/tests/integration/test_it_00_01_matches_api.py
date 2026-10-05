"""IT-00-01 (API <-> Postgres, ST-006): create, get and list a match; the list returns only
the caller's matches. Uses the rolled-back session via dependency_overrides (AQS/STACK-01)."""

from __future__ import annotations

from typing import Any

import httpx

from tests.support import contract
from tests.support.api import async_client, sign_in
from tests.support.builders import a_match


async def test_create_get_and_list(api_client: httpx.AsyncClient, app: Any) -> None:
    await sign_in(api_client, "ivy")
    payload = a_match().titled("IT-00-01").with_format("singles").as_create_payload()

    created = await api_client.post(contract.MATCHES, json=payload)
    assert created.status_code == 201, created.text
    match = created.json()
    assert match["title"] == "IT-00-01"
    assert match["format"] == "singles"
    assert match["status"] == "awaiting_upload"
    assert match["media"] is None

    fetched = await api_client.get(contract.MATCH.format(match_id=match["id"]))
    assert fetched.status_code == 200
    assert fetched.json() == match

    listing = await api_client.get(contract.MATCHES)
    items = listing.json()["items"] if isinstance(listing.json(), dict) else listing.json()
    assert [m["id"] for m in items] == [match["id"]]

    async with async_client(app) as carlos:
        await sign_in(carlos, "carlos")
        theirs = await carlos.get(contract.MATCHES)
        their_items = theirs.json()["items"] if isinstance(theirs.json(), dict) else theirs.json()
        assert their_items == []


async def test_response_is_an_allowlist_without_owner_internals(
    api_client: httpx.AsyncClient,
) -> None:
    await sign_in(api_client, "ivy")

    created = await api_client.post(contract.MATCHES, json=a_match().as_create_payload())

    keys = set(created.json())
    assert {"id", "title", "format", "status", "media"} <= keys
    assert keys <= {"id", "title", "format", "status", "media", "created_at", "updated_at"}, keys


async def test_unknown_request_field_is_rejected(api_client: httpx.AsyncClient) -> None:
    """NFR-052: unknown request fields are rejected (mass-assignment guard)."""
    await sign_in(api_client, "ivy")

    response = await api_client.post(
        contract.MATCHES, json={**a_match().as_create_payload(), "owner_id": "someone-else"}
    )

    assert response.status_code == 422


async def test_unauthenticated_create_is_refused(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post(contract.MATCHES, json=a_match().as_create_payload())

    assert response.status_code == 401
