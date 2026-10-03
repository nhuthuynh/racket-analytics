"""Steps for tests/features/dev_environment.feature (ST-001 with ST-005/ST-006 settings;
NFR-080, NFR-081; AQS/OPS-01: config only from the environment).

"When the API starts" calls the app factory, which must read Settings from the environment
and refuse to build an app on bad configuration.
"""

from __future__ import annotations

import re

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.support import contract

pytestmark = pytest.mark.red_until(story="ST-005")

scenarios("dev_environment.feature")


@given("the database address is not set")
def no_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)


@given("the environment is production and the development sign-in is enabled")
def prod_with_dev_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv(contract.DEV_IDENTITY_ENV, "true")


@when("the API starts", target_fixture="startup_error")
def api_starts() -> BaseException | None:
    configuration_error = contract.CONFIGURATION_ERROR.load()
    try:
        # Loading is inside the try: a module that builds ``app = create_app()`` at import
        # time (uvicorn "module:app" style) refuses to start during the import itself.
        contract.APP_FACTORY.load()()
    except configuration_error as exc:
        error: BaseException = exc
        return error
    return None


@then("it refuses to start and names the missing setting")
def refuses_naming_setting(startup_error: BaseException | None) -> None:
    assert startup_error is not None, "the API started without DATABASE_URL"
    assert isinstance(startup_error, contract.MISSING_SETTING_ERROR.load())
    assert "DATABASE_URL" in str(startup_error)


@then("it refuses to start and says development sign-in is not allowed")
def refuses_dev_identity_in_prod(startup_error: BaseException | None) -> None:
    assert startup_error is not None, "the API started in prod with the dev identity provider"
    message = str(startup_error).lower()
    assert re.search(r"dev(elopment)?[ _-]?(sign[ -]?in|identit)", message), message
    assert "prod" in message
