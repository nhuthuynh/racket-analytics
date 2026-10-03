"""API test clients: httpx with ASGITransport, no network (ST-004; AQS/STACK-01).

* ``async_client(app)`` for async tests.
* ``ApiDriver`` is a synchronous facade over the same async client for pytest-bdd steps,
  which are plain functions. It runs the app's lifespan and keeps cookies per user, so two
  users (Ivy and Carlos) can act against one app in the same scenario.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Coroutine
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any, TypeVar

import httpx

from tests.support import contract

BASE_URL = "http://testserver"
T = TypeVar("T")


@asynccontextmanager
async def lifespan(app: Any) -> AsyncIterator[None]:
    ctx: AbstractAsyncContextManager[Any] = app.router.lifespan_context(app)
    async with ctx:
        yield


@asynccontextmanager
async def async_client(app: Any) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as client:
        yield client


async def sign_in(client: httpx.AsyncClient, username: str) -> httpx.Response:
    """Sign in through the dev identity provider (ST-006). Cookie stays on ``client``."""
    method, path = contract.DEV_SIGN_IN
    response = await client.request(method, path, json={"username": username})
    assert response.status_code in (200, 204), (
        f"dev sign-in as {username!r} failed: {response.status_code} {response.text[:200]}"
    )
    return response


class ApiDriver:
    """Synchronous driver for scenario steps. One instance per scenario."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self._runner = asyncio.Runner()
        self._lifespan = lifespan(app)
        self._runner.run(self._lifespan.__aenter__())
        self._clients: dict[str, httpx.AsyncClient] = {}

    def as_user(self, username: str) -> httpx.AsyncClient:
        if username not in self._clients:
            transport = httpx.ASGITransport(app=self.app, raise_app_exceptions=False)
            client = httpx.AsyncClient(transport=transport, base_url=BASE_URL)
            self._clients[username] = client
            if username != "anonymous":
                self._runner.run(sign_in(client, username))
        return self._clients[username]

    def run(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run an async helper (e.g. ``tests.support.tus``) on this driver's event loop."""
        return self._runner.run(coro)

    def request(self, username: str, method: str, url: str, **kwargs: Any) -> httpx.Response:
        return self._runner.run(self.as_user(username).request(method, url, **kwargs))

    def close(self) -> None:
        for client in self._clients.values():
            self._runner.run(client.aclose())
        try:
            self._runner.run(self._lifespan.__aexit__(None, None, None))
        finally:
            self._runner.close()
