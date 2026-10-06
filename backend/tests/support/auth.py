"""Magic-link helpers for Sprint 1 tests (ST-013; api-sprint-01 §2)."""

from __future__ import annotations

import uuid

import httpx

from tests.support import contract, mailpit
from tests.support.api import BASE_URL, ApiDriver


def unique_email(name: str = "ivy") -> str:
    """A fresh address per test, so rate-limit windows never collide between tests."""
    return f"{name}+{uuid.uuid4().hex[:12]}@example.com"


def new_client(api: ApiDriver) -> httpx.AsyncClient:
    """A browser without a session (the caller closes it with ``api.run(client.aclose())``)."""
    transport = httpx.ASGITransport(app=api.app, raise_app_exceptions=False)
    return httpx.AsyncClient(transport=transport, base_url=BASE_URL)


def request_link(api: ApiDriver, client: httpx.AsyncClient, email: str) -> httpx.Response:
    return api.run(client.post(contract.AUTH_LINKS, json={"email": email}))


def deliver_mail() -> None:
    """The link is sent by a queued job (api-sprint-01 §2.1); run the worker until idle."""
    contract.WORKER_RUN_UNTIL_IDLE.load()()


def link_token(api: ApiDriver, email: str, nth_message: int = 1) -> str:
    bodies = mailpit.wait_for_messages(email, count=nth_message)
    assert len(bodies) >= nth_message, f"{len(bodies)} sign-in emails arrived for the address"
    return mailpit.token_from(bodies[0])


def exchange(api: ApiDriver, client: httpx.AsyncClient, token: str) -> httpx.Response:
    return api.run(client.post(contract.AUTH_EXCHANGE, json={"token": token}))
