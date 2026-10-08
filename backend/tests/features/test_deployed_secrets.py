"""Steps for tests/features/deployed_secrets.feature (SEC-RV3-02; T-ML-7; NFR-056).

"When the API starts" calls the app factory, which reads Settings from the environment and must
refuse to build an app on a dev-only AUTH_EMAIL_KEY in staging and prod.
"""

from __future__ import annotations

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import contract

scenarios("deployed_secrets.feature")

ENV_EXAMPLE_KEY = "dev-only-email-key-not-a-secret-0000"  # infra/env.example, 36 characters
REAL_KEY = "".join(chr(ord("a") + (i * 7) % 26) for i in range(40))  # made up, not dev-only
DEPLOYED = {
    "DEV_IDENTITY_ENABLED": "false",
    "S3_BUCKET_MEDIA": "racket-media",
    "ALLOWED_ORIGINS": "https://app.racket.test",
    "PUBLIC_WEB_ORIGIN": "https://app.racket.test",
}


def _deploy(monkeypatch: pytest.MonkeyPatch, app_env: str, key: str) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://racket:unused@127.0.0.1:9/racket")
    for name, value in DEPLOYED.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("AUTH_EMAIL_KEY", key)


@given(
    parsers.parse(
        "the environment is {app_env} and the email key is the development placeholder "
        "from env.example"
    ),
    target_fixture="email_key",
)
def deployed_with_dev_key(monkeypatch: pytest.MonkeyPatch, app_env: str) -> str:
    _deploy(monkeypatch, app_env, ENV_EXAMPLE_KEY)
    return ENV_EXAMPLE_KEY


@given("the environment is prod and the email key is a real secret", target_fixture="email_key")
def prod_with_real_key(monkeypatch: pytest.MonkeyPatch) -> str:
    _deploy(monkeypatch, "prod", REAL_KEY)
    return REAL_KEY


@when("the API starts", target_fixture="startup_error")
def api_starts() -> BaseException | None:
    configuration_error = contract.CONFIGURATION_ERROR.load()
    try:
        contract.APP_FACTORY.load()()
    except configuration_error as exc:
        error: BaseException = exc
        return error
    return None


@then("it refuses to start and says the email key is a development placeholder")
def refuses_dev_key(startup_error: BaseException | None) -> None:
    assert startup_error is not None, "the API started on the dev-only AUTH_EMAIL_KEY"
    message = str(startup_error)
    assert "AUTH_EMAIL_KEY" in message, message
    assert "dev placeholder" in message, message


@then("the message does not show the key")
def key_not_echoed(startup_error: BaseException | None, email_key: str) -> None:
    assert email_key not in str(startup_error)


@then("it starts")
def it_starts(startup_error: BaseException | None) -> None:
    assert startup_error is None, str(startup_error)
