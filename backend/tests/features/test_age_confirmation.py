"""Steps for tests/features/age_confirmation.feature (ST-068a; FR-003; api-sprint-04 §4).
The app is built with ``FEATURE_AGE_GATE`` from the scenario, on the rolled-back session."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import auth, contract
from tests.support.age_gate import AGE_CONFIRMATION, accounts_for, pending_count, seed_link
from tests.support.api import ApiDriver

scenarios("age_confirmation.feature")

EMAIL = "applicant@example.com"


@pytest.fixture
def drivers() -> Iterator[list[ApiDriver]]:
    built: list[ApiDriver] = []
    yield built
    for driver in built:
        driver.close()


@given(parsers.re(r"the age gate is (?P<state>on|off)"), target_fixture="api")
def age_gate(
    state: str, monkeypatch: pytest.MonkeyPatch, db_session: Any, drivers: list[ApiDriver]
) -> ApiDriver:
    monkeypatch.setenv("FEATURE_AGE_GATE", "true" if state == "on" else "false")
    app = contract.APP_FACTORY.load()()
    app.dependency_overrides[contract.DB_SESSION_DEPENDENCY.load()] = lambda: db_session
    drivers.append(ApiDriver(app))
    return drivers[-1]


@given("a new address has signed in with a link", target_fixture="client")
def signed_in(api: ApiDriver, db_session: Any) -> httpx.AsyncClient:
    client = auth.new_client(api)
    response = auth.exchange(api, client, seed_link(db_session, EMAIL))
    assert response.status_code == 200, response.text
    return client


@given(parsers.parse('the applicant\'s account answers "{code}"'))
def account_answers(api: ApiDriver, client: httpx.AsyncClient, code: str) -> None:
    response = api.run(client.get(contract.ME))
    assert response.status_code == 403 and response.json()["error"]["code"] == code


@when(parsers.re(r"the applicant answers that they are (?P<answer>not )?an adult"),
      target_fixture="answered")  # fmt: skip
def answers(api: ApiDriver, client: httpx.AsyncClient, answer: str | None) -> httpx.Response:
    return api.run(client.post(AGE_CONFIRMATION, json={"is_adult": answer is None}))


@then(parsers.parse('the answer is refused as "{code}"'))
def refused(answered: httpx.Response, code: str) -> None:
    assert answered.status_code == 403, answered.text
    assert answered.json()["error"]["code"] == code


@then("no account exists for the address")
def no_account(db_session: Any) -> None:
    assert accounts_for(db_session, EMAIL) == []
    assert pending_count(db_session) == 0


@then("the sign-in has ended")
def ended(api: ApiDriver, client: httpx.AsyncClient) -> None:
    assert api.run(client.get(contract.ME)).status_code == 401


@then(parsers.re(r"the address has an account (?P<kind>with|without) a confirmation time"))
def has_account(db_session: Any, kind: str) -> None:
    [row] = accounts_for(db_session, EMAIL)
    assert (row.age_confirmed_at is not None) is (kind == "with")


@then("the applicant can see their account")
def can_see(api: ApiDriver, client: httpx.AsyncClient, db_session: Any) -> None:
    response = api.run(client.get(contract.ME))
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(accounts_for(db_session, EMAIL)[0].id)


@then("the age question is not found")
def not_found(api: ApiDriver, client: httpx.AsyncClient) -> None:
    response = api.run(client.post(AGE_CONFIRMATION, json={"is_adult": True}))
    assert response.status_code == 404
