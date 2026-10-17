"""IT-04-17 (ST-067; api-sprint-04 §1 rule 3): ``GET /config/public`` tells the web, without a
session, which R1 features are on and the weakness unit, and nothing else (no limits, no
secrets). Every flag is off unless its ``FEATURE_*`` variable is on (ADR 0051 rule 4).
Negative cases first; positive control: each flag switched on is reported on, alone."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AsyncExitStack
from typing import Any

import httpx
import pytest

from tests.support import contract
from tests.support.api import async_client, lifespan

URL = "/config/public"
FLAGS = {
    f"FEATURE_{f.upper()}": f
    for f in ("age_gate", "retention_setting", "training_consent", "quotas")
}
ALL_OFF = dict.fromkeys(FLAGS.values(), False)
Opener = Callable[[], Awaitable[httpx.AsyncClient]]


@pytest.fixture
async def anonymous(monkeypatch: pytest.MonkeyPatch, db_session: Any) -> AsyncIterator[Opener]:
    """Opens a client on an app built from the environment *at call time*, after the test has
    set its flags; the app runs its lifespan on the real database."""
    for name in (*FLAGS, "COACHING_WEAKNESS_UNIT"):
        monkeypatch.delenv(name, raising=False)
    async with AsyncExitStack() as stack:

        async def open_client() -> httpx.AsyncClient:
            app = contract.APP_FACTORY.load()()
            app.dependency_overrides[contract.DB_SESSION_DEPENDENCY.load()] = lambda: db_session
            await stack.enter_async_context(lifespan(app))
            return await stack.enter_async_context(async_client(app))

        yield open_client


async def test_it_04_17_no_limits_secrets_writes_or_caching(anonymous: Opener) -> None:
    client = await anonymous()

    response = await client.get(URL)

    assert response.status_code == 200, response.text
    assert set(response.json()) == {"features", "coaching"}
    for leaked in ("bytes", "hour", "age_minimum", "days", "key", "secret", "url", "password"):
        assert leaked not in response.text.lower(), leaked
    assert "no-store" in response.headers.get("cache-control", "")
    assert (await client.post(URL, json={"features": {"quotas": True}})).status_code == 405
    assert (await client.get(URL)).json()["features"] == ALL_OFF


async def test_it_04_17_flags_are_off_by_default(anonymous: Opener) -> None:
    response = await (await anonymous()).get(URL)

    assert response.status_code == 200, response.text
    assert response.json() == {
        "features": ALL_OFF,
        "coaching": {"weakness_unit": "rallies_lost_per_game"},
    }


@pytest.mark.parametrize("variable", sorted(FLAGS))
async def test_it_04_17_a_flag_switched_on_is_reported_alone(
    anonymous: Opener, monkeypatch: pytest.MonkeyPatch, variable: str
) -> None:
    monkeypatch.setenv(variable, "true")

    response = await (await anonymous()).get(URL)

    assert response.json()["features"] == {**ALL_OFF, FLAGS[variable]: True}
