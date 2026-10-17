"""Steps for tests/features/feature_flags.feature (ST-067; api-sprint-04 §1 rule 3, §11).
The app factory reads ``Settings`` from the environment; ``/config/public`` needs no session."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import contract
from tests.support.api import async_client

scenarios("feature_flags.feature")

FEATURES = ("age_gate", "retention_setting", "training_consent", "quotas")


@given("no feature flag is configured")
def no_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("COACHING_WEAKNESS_UNIT", *(f"FEATURE_{f.upper()}" for f in FEATURES)):
        monkeypatch.delenv(name, raising=False)


@given(parsers.parse('the weakness unit is configured as "{unit}"'))
def weakness_unit(monkeypatch: pytest.MonkeyPatch, unit: str) -> None:
    monkeypatch.setenv("COACHING_WEAKNESS_UNIT", unit)


@given(parsers.re(r'(?P<name>FEATURE_[A-Z_]+) is "(?P<value>[^"]*)"'))
def flag_value(monkeypatch: pytest.MonkeyPatch, name: str, value: str) -> None:
    monkeypatch.setenv(name, value)


@when("the API starts", target_fixture="startup_error")
def api_starts() -> BaseException | None:
    try:
        contract.APP_FACTORY.load()()
    except contract.CONFIGURATION_ERROR.load() as exc:
        return exc
    return None


@when("a visitor without a session reads the public configuration", target_fixture="public")
def read_public_config() -> dict[str, Any]:
    async def get() -> Any:
        async with async_client(contract.APP_FACTORY.load()()) as client:
            return await client.get("/config/public")

    response = asyncio.run(get())
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


@then("it refuses to start and names the setting COACHING_WEAKNESS_UNIT")
def refused(startup_error: BaseException | None) -> None:
    assert startup_error is not None, "the API started with an unknown weakness unit"
    assert "COACHING_WEAKNESS_UNIT" in str(startup_error)


@then(parsers.parse('the features on are "{names}"'))
def features_on(public: dict[str, Any], names: str) -> None:
    on = set(filter(None, names.split(",")))
    assert public["features"] == {f: f in on for f in FEATURES}


@then(parsers.parse('the weakness unit is "{unit}"'))
def unit_is(public: dict[str, Any], unit: str) -> None:
    assert public["coaching"] == {"weakness_unit": unit}
