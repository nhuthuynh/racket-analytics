"""Steps for tests/features/no_store.feature (ST-078d; NFR-067.1; G05-06).

Scenario 1 runs a planted route behind ``EdgeMiddleware`` in process; scenario 2 runs every
authenticated GET route of a flag-on app on the committed database (``api``), as Ivy holding the
labeller role, so the flag-gated and /label routes reach their handlers too.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pytest_bdd import given, parsers, scenarios, then, when

from racket.platform.errors import ErrorMapper
from racket.platform.http import EdgeMiddleware
from tests.support import contract
from tests.support.age_gate import AGE_CONFIRMATION
from tests.support.api import ApiDriver, async_client
from tests.support.flags import set_flags
from tests.support.no_store import (
    QUERY,
    authenticated_gets,
    fill,
    seed_resources,
    without_no_store,
)
from tests.support.stats import LABELLER_ADMIN

scenarios("no_store.feature")


@pytest.fixture(autouse=True)
def _all_flags_on(monkeypatch: pytest.MonkeyPatch) -> tuple[str, ...]:
    """Every R1 flag on before the app is built (autouse fixtures are set up first)."""
    return set_flags(monkeypatch, on=True)


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given(parsers.parse('a route answers Ivy with "Cache-Control: {value}"'))
def planted_route(ctx: dict[str, Any], value: str) -> None:
    app = FastAPI()
    app.add_middleware(EdgeMiddleware, mapper=ErrorMapper())

    @app.get("/planted")
    def planted() -> JSONResponse:
        return JSONResponse({"ok": True}, headers={"Cache-Control": value})

    ctx["planted"] = app


@when("Ivy opens it through the API edge")
def open_planted(ctx: dict[str, Any], api: ApiDriver) -> None:
    async def get() -> httpx.Response:
        async with async_client(ctx["planted"]) as client:
            return await client.get("/planted")

    ctx["answers"] = {"/planted": api.run(get())}


@given("Ivy has a tagged match and a training plan")
def ivy_with_data(api: ApiDriver, ctx: dict[str, Any]) -> None:
    ivy = api.as_user("ivy")
    assert api.run(ivy.post(AGE_CONFIRMATION, json={"is_adult": True})).status_code < 300
    me = api.run(ivy.get(contract.ME))
    assert me.status_code == 200, me.text
    assert LABELLER_ADMIN.load()(["grant-labeller", "--account", str(me.json()["id"])]) == 0
    ctx["resources"] = api.run(seed_resources(ivy, "no_store.feature"))


@when("Ivy opens every authenticated GET route of the API")
def open_every_route(api: ApiDriver, ctx: dict[str, Any]) -> None:
    answers = {}
    for template in authenticated_gets(api.app):
        url = fill(template, ctx["resources"])
        response = api.request("ivy", "GET", url, params=QUERY.get(template))
        assert response.status_code not in (401, 404, 405), (template, response.status_code)
        answers[template] = response
    assert len(answers) >= 15, sorted(answers)
    ctx["answers"] = answers


@then('the answer says only "no-store"')
@then('every answer says only "no-store"')
def only_no_store(ctx: dict[str, Any]) -> None:
    assert without_no_store(ctx["answers"]) == []
