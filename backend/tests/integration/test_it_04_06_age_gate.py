"""IT-04-06 (ST-068a; FR-003; OQ-05 accepted, ADR 0023; api-sprint-04 §4; SEC-4 T4-AG-1/2/5).

API <-> DB, real Postgres. With ``FEATURE_AGE_GATE`` on, a new address that signs in holds a
pending sign-in, not an account: ``false`` leaves 0 new account rows and ends the sign-in (403
``under_age``); every route that needs a session answers 403 ``age_confirmation_required`` until
``true``; only ``age_confirmed_at`` is stored. With the flag off nothing changes and the route is
404. Negative cases first; the positive controls follow.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from typing import Any

import httpx
import pytest

from tests.regression import bola
from tests.support import contract
from tests.support.age_gate import (
    AGE_CONFIRMATION,
    accounts_for,
    age_like_columns,
    pending_count,
    seed_link,
)
from tests.support.api import async_client, lifespan, sign_in

Opener = Callable[[bool], Awaitable[tuple[Any, httpx.AsyncClient]]]
# api-sprint-04 §4: the only routes a pending sign-in may use besides the anonymous ones.
ALLOWED = {("POST", AGE_CONFIRMATION), ("POST", contract.AUTH_SIGN_OUT)}


@pytest.fixture
async def open_app(monkeypatch: pytest.MonkeyPatch, db_session: Any) -> AsyncIterator[Opener]:
    """An app built with the age gate on or off, on the rolled-back session."""
    async with AsyncExitStack() as stack:

        async def opener(gate: bool) -> tuple[Any, httpx.AsyncClient]:
            monkeypatch.setenv("FEATURE_AGE_GATE", "true" if gate else "false")
            app = contract.APP_FACTORY.load()()
            app.dependency_overrides[contract.DB_SESSION_DEPENDENCY.load()] = lambda: db_session
            await stack.enter_async_context(lifespan(app))
            return app, await stack.enter_async_context(async_client(app))

        yield opener


async def _signs_in(client: httpx.AsyncClient, db_session: Any, email: str) -> httpx.Response:
    response = await client.post(contract.AUTH_EXCHANGE, json={"token": seed_link(db_session, email)})
    assert response.status_code == 200, response.text
    return response


def _code(response: httpx.Response) -> str:
    return str(response.json()["error"]["code"])


# ------------------------------------------------------------------ negative cases first
async def test_it_04_06_under_age_answer_leaves_no_account_and_ends_the_sign_in(
    open_app: Opener, db_session: Any
) -> None:
    _, client = await open_app(True)
    before = len(accounts_for(db_session))

    exchanged = await _signs_in(client, db_session, "minor@example.com")
    answered = await client.post(AGE_CONFIRMATION, json={"is_adult": False})

    assert exchanged.json()["account"] is None
    assert answered.status_code == 403, answered.text
    assert _code(answered) == "under_age"
    assert "18 or over" in answered.json()["error"]["message"]
    assert "max-age=0" in answered.headers.get("set-cookie", "").lower()
    assert len(accounts_for(db_session)) == before  # T4-AG-1: 0 account rows
    assert pending_count(db_session) == 0
    assert (await client.get(contract.ME)).status_code == 401


async def test_it_04_06_pending_sign_in_is_refused_on_every_route_that_needs_a_session(
    open_app: Opener, db_session: Any
) -> None:
    """T4-AG-2, deny by default: every route an anonymous caller gets 401 on answers 403
    ``age_confirmation_required`` to a pending sign-in, so a new route is gated without edits."""
    app, client = await open_app(True)
    await _signs_in(client, db_session, "pending@example.com")
    anonymous = httpx.AsyncClient(transport=client._transport, base_url=str(client.base_url))
    headers = {"Tus-Resumable": contract.TUS_VERSION}
    gated = []

    for method, template in sorted(bola.all_routes(app) - ALLOWED):
        if method in bola.IGNORED_METHODS:
            continue
        url = bola.PATH_PARAM.sub(str(uuid.uuid4()), template)
        if (await anonymous.request(method, url, headers=headers)).status_code != 401:
            continue  # a route without a session requirement (health, config, auth)
        refused = await client.request(method, url, headers=headers)
        assert refused.status_code == 403, f"{method} {template}: {refused.status_code}"
        assert _code(refused) == "age_confirmation_required", f"{method} {template}"
        gated.append((method, template))

    assert ("GET", contract.ME) in gated and len(gated) >= 20, gated
    await anonymous.aclose()


async def test_it_04_06_existing_unconfirmed_account_is_gated_and_kept_without_typed_confirm(
    open_app: Opener,
) -> None:
    _, client = await open_app(True)
    await sign_in(client, "ivy")

    gated = await client.get(contract.ME)
    unconfirmed = await client.post(AGE_CONFIRMATION, json={"is_adult": False})

    assert gated.status_code == 403 and _code(gated) == "age_confirmation_required"
    assert unconfirmed.status_code == 422, unconfirmed.text
    assert unconfirmed.json()["error"]["fields"] == [
        {"field": "confirm", "code": "confirmation_required"}
    ]
    assert _code(await client.get(contract.ME)) == "age_confirmation_required"


@pytest.mark.parametrize(
    ("body", "field", "code"),
    [
        ({}, "is_adult", "required"),
        ({"is_adult": "yes"}, "is_adult", "invalid"),
        ({"is_adult": True, "birth_date": "2010-01-01"}, None, "unknown_field"),
    ],
)
async def test_it_04_06_answer_body_is_closed(
    open_app: Opener, db_session: Any, body: dict[str, Any], field: str | None, code: str
) -> None:
    _, client = await open_app(True)
    await _signs_in(client, db_session, f"shape-{uuid.uuid4().hex[:8]}@example.com")

    response = await client.post(AGE_CONFIRMATION, json=body)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["fields"] == [{"field": field, "code": code}]
    assert pending_count(db_session) == 1


async def test_it_04_06_no_session_is_401_and_flag_off_is_404(open_app: Opener) -> None:
    _, gated = await open_app(True)
    _, plain = await open_app(False)

    assert (await gated.post(AGE_CONFIRMATION, json={"is_adult": True})).status_code == 401
    await sign_in(plain, "ivy")
    assert (await plain.post(AGE_CONFIRMATION, json={"is_adult": True})).status_code == 404


# ------------------------------------------------------------------ positive controls
async def test_it_04_06_adult_answer_creates_the_account_with_only_a_timestamp(
    open_app: Opener, db_session: Any
) -> None:
    _, client = await open_app(True)
    email = "adult@example.com"
    await _signs_in(client, db_session, email)

    answered = await client.post(AGE_CONFIRMATION, json={"is_adult": True})

    assert answered.status_code == 200, answered.text
    assert set(answered.json()) == {"id", "display_name", "age_confirmed_at"}
    [row] = accounts_for(db_session, email)
    assert str(row.id) == answered.json()["id"] and row.age_confirmed_at is not None
    assert pending_count(db_session) == 0
    assert age_like_columns(db_session) == {"accounts.age_confirmed_at"}
    me = await client.get(contract.ME)
    assert me.status_code == 200 and me.json()["id"] == str(row.id)


async def test_it_04_06_existing_account_deleted_only_with_typed_confirm(
    open_app: Opener,
) -> None:
    """T4-AG-5: ``false`` on an existing account follows the ``DELETE /me`` path."""
    _, client = await open_app(True)
    await sign_in(client, "carlos")

    answered = await client.post(AGE_CONFIRMATION, json={"is_adult": False, "confirm": "delete"})

    assert answered.status_code == 403 and _code(answered) == "under_age"
    assert (await client.get(contract.ME)).status_code == 401


async def test_it_04_06_flag_off_signs_in_as_today(open_app: Opener, db_session: Any) -> None:
    _, client = await open_app(False)
    email = "today@example.com"

    exchanged = await _signs_in(client, db_session, email)

    assert exchanged.json()["new_account"] is True and exchanged.json()["account"] is not None
    [row] = accounts_for(db_session, email)
    assert row.age_confirmed_at is None
    me = await client.get(contract.ME)
    assert me.status_code == 200 and set(me.json()) == {"id", "display_name"}
