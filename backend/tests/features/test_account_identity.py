"""API binding of tests/features/account_identity.feature (ST-013b; ADR 0032). Needs Mailpit
(``MAILPIT_API_URL``; skip locally, fail in CI). The full red set is IT-02-12."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import auth, contract, mailpit
from tests.support.api import ApiDriver

pytestmark = pytest.mark.slow

scenarios("account_identity.feature")

KEY_1 = "account-identity-key-one-00000000000000"
KEY_2 = "account-identity-key-two-00000000000000"


@pytest.fixture
def ctx(monkeypatch: pytest.MonkeyPatch, committed_db: Any) -> Iterator[dict[str, Any]]:
    monkeypatch.setenv("PUBLIC_WEB_ORIGIN", "https://app.racket.test")
    monkeypatch.setenv("AUTH_EMAIL_KEY", KEY_1)
    state: dict[str, Any] = {"drivers": [], "monkeypatch": monkeypatch}
    yield state
    for driver in state["drivers"]:
        driver.close()


def _driver(ctx: dict[str, Any]) -> ApiDriver:
    driver = ApiDriver(contract.APP_FACTORY.load()())
    ctx["drivers"].append(driver)
    return driver


def _sign_in(api: ApiDriver, email: str) -> tuple[Any, str]:
    client = auth.new_client(api)
    sent_before = len(mailpit.messages_to(email))
    assert auth.request_link(api, client, email).status_code == 202
    auth.deliver_mail()
    response = auth.exchange(api, client, auth.link_token(api, email, sent_before + 1))
    assert response.status_code == 200, response.text
    return client, str(response.json()["account"]["id"])


@given(parsers.parse("Ivy has an account with {n:d} matches"))
def account_with_matches(ctx: dict[str, Any], n: int) -> None:
    api = _driver(ctx)
    ctx["email"] = auth.unique_email()
    client, ctx["account"] = _sign_in(api, ctx["email"])
    for i in range(n):
        body = {"title": f"Match {i + 1}", "format": "singles"}
        assert api.run(client.post(contract.MATCHES, json=body)).status_code == 201
    api.run(client.aclose())


@when("the service rotates its sign-in key")
def rotates(ctx: dict[str, Any]) -> None:
    ctx["monkeypatch"].setenv("AUTH_EMAIL_KEY", KEY_2)


@when("Ivy signs in with the same address")
def signs_in_again(ctx: dict[str, Any]) -> None:
    api = _driver(ctx)
    ctx["client"], ctx["again"] = _sign_in(api, ctx["email"])
    ctx["api"] = api


@then(parsers.parse("she sees her {n:d} matches"))
def sees_matches(ctx: dict[str, Any], n: int) -> None:
    api = ctx["api"]
    items = api.run(ctx["client"].get(contract.MATCHES)).json()["items"]
    api.run(ctx["client"].aclose())
    assert ctx["again"] == ctx["account"]
    assert len(items) == n


@given("two different addresses produce the same key")
def same_key(ctx: dict[str, Any]) -> None:
    import racket.players.service as service

    ctx["monkeypatch"].setattr(service, "email_key", lambda secret, email: "fedcba9876543210")


@when("both sign in")
def both_sign_in(ctx: dict[str, Any]) -> None:
    api = _driver(ctx)
    ctx["accounts"] = []
    for name in ("ivy", "carlos"):
        client, account = _sign_in(api, auth.unique_email(name))
        api.run(client.aclose())
        ctx["accounts"].append(account)


@then("each gets an account of its own")
def own_accounts(ctx: dict[str, Any]) -> None:
    assert len(set(ctx["accounts"])) == 2
