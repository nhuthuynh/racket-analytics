"""IT-05-06 (ST-078d; NFR-067.1; G05-06): every authenticated GET route sends
``Cache-Control: no-store``, on its success and on its error answers.

The route list is the app's own GET inventory (``bola.all_routes``), so a new GET route is
covered the day it is served; a route is public only if ``no_store.PUBLIC_GETS`` names it with
a reason. Positive controls (testing-strategy rule 8): the owner's call reaches the handler (not
401, 404 or 405), every listed route refuses an anonymous caller with 401, and every public
route answers without a session.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
import sqlalchemy as sa

from tests.regression.bola import all_routes
from tests.support.age_gate import AGE_CONFIRMATION
from tests.support.api import async_client, lifespan, sign_in
from tests.support.no_store import (
    PUBLIC_GETS,
    QUERY,
    authenticated_gets,
    cache_control,
    fill,
    seed_resources,
    without_no_store,
)
from tests.support.stats import LABELLER_ADMIN


@pytest.fixture(autouse=True)
def _all_flags_on(flags_on: tuple[str, ...]) -> tuple[str, ...]:
    """Every R1 flag on before ``app`` is built, so flag-gated GET routes are live (autouse
    fixtures are set up first)."""
    return flags_on


@pytest.fixture
async def ivy(app: Any, db_session: Any) -> AsyncIterator[httpx.AsyncClient]:
    """Ivy holding the labeller role (for the /label routes), signed in, age confirmed. The
    grant runs on its own connection, so it goes before any request writes on the rolled-back
    session: a row that session locks would block it."""
    async with lifespan(app), async_client(app) as client:  # lifespan seeds the dev users
        ivy_id = db_session.execute(
            sa.text("SELECT id FROM accounts WHERE username = 'ivy'")
        ).scalar_one()
        assert LABELLER_ADMIN.load()(["grant-labeller", "--account", str(ivy_id)]) == 0
        await sign_in(client, "ivy")
        confirmed = await client.post(AGE_CONFIRMATION, json={"is_adult": True})  # flag on
        assert confirmed.status_code < 300, confirmed.text
        yield client


@pytest.fixture
async def resources(ivy: httpx.AsyncClient) -> dict[str, str]:
    return await seed_resources(ivy, "IT-05-06 no-store")


async def test_it_05_06_every_authenticated_get_sends_no_store(
    app: Any, ivy: httpx.AsyncClient, resources: dict[str, str]
) -> None:
    routes = authenticated_gets(app)
    assert len(routes) >= 15, routes  # the inventory is not empty (positive control)
    answers = {}
    for template in routes:
        response = await ivy.get(fill(template, resources), params=QUERY.get(template))
        assert response.status_code not in (401, 404, 405), (template, response.status_code)
        answers[template] = response
    assert without_no_store(answers) == []


async def test_it_05_06_authenticated_get_errors_send_no_store(
    app: Any, ivy: httpx.AsyncClient, resources: dict[str, str]
) -> None:
    """A missing resource (404) on every id route: the error answer is not cached either."""
    answers = {}
    for template in (t for t in authenticated_gets(app) if "{match_id}" in t):
        url = template.format(match_id=uuid.uuid4(), rally_id=uuid.uuid4(), metric_id="AN-01")
        response = await ivy.get(url, params=QUERY.get(template))
        assert response.status_code == 404, (template, response.status_code)
        answers[template] = response
    assert without_no_store(answers) == []


async def test_it_05_06_listed_routes_are_the_authenticated_ones(
    app: Any, ivy: httpx.AsyncClient, resources: dict[str, str]
) -> None:
    """Negative of the classification: each authenticated route refuses an anonymous caller, and
    each public route is served and answers one."""
    served = {path for method, path in all_routes(app) if method == "GET"}
    assert set(PUBLIC_GETS) - served == set()  # no stale public entry
    async with async_client(app) as anonymous:
        for template in authenticated_gets(app):
            response = await anonymous.get(fill(template, resources), params=QUERY.get(template))
            assert response.status_code == 401, (template, response.status_code)
            assert cache_control(response.headers) == ["no-store"], template
        for path in PUBLIC_GETS:
            response = await anonymous.get(path)
            assert response.status_code == 200, (path, response.status_code)
