"""Sprint 3 settings: a deployed process refuses the dev email key (SEC-RV3-02; T-ML-7;
ADR 0025). The env.example key ``dev-only-email-key-not-a-secret-0000`` is 36 characters, so the
length rule alone let it through in staging and prod. Negative cases first."""

from __future__ import annotations

import pytest

from racket.platform.settings import DEV_EMAIL_KEY, ConfigurationError, Settings

pytestmark = pytest.mark.unit

DEPLOYED = {
    "DATABASE_URL": "postgresql://racket:pg-pass-123@db:5432/racket",
    "S3_BUCKET_MEDIA": "racket-media",
    "ALLOWED_ORIGINS": "https://app.racket.test",
    "PUBLIC_WEB_ORIGIN": "https://app.racket.test",
}
DEV_KEYS = [
    "dev-only-email-key-not-a-secret-0000",  # infra/env.example
    DEV_EMAIL_KEY + "-padded-to-be-long-enough",
    "x" * 20 + "DEV-ONLY" + "y" * 20,
]


@pytest.mark.parametrize("app_env", ["staging", "prod"])
@pytest.mark.parametrize("key", DEV_KEYS)
def test_a_dev_email_key_is_refused_when_deployed(app_env: str, key: str) -> None:
    with pytest.raises(ConfigurationError, match="AUTH_EMAIL_KEY") as caught:
        Settings.from_env({**DEPLOYED, "APP_ENV": app_env, "AUTH_EMAIL_KEY": key})
    assert key not in str(caught.value)  # the secret is never echoed


@pytest.mark.parametrize("app_env", ["dev", "test"])
def test_the_dev_key_is_fine_in_dev_and_test(app_env: str) -> None:
    s = Settings.from_env({**DEPLOYED, "APP_ENV": app_env, "AUTH_EMAIL_KEY": DEV_KEYS[0]})
    assert s.auth_email_key == DEV_KEYS[0]


def test_positive_control_a_real_key_is_accepted_in_prod() -> None:
    key = "q7N2v9Lr4TzX8pWc1HsK6dYb3MfJ0aGe"
    assert (
        Settings.from_env({**DEPLOYED, "APP_ENV": "prod", "AUTH_EMAIL_KEY": key}).auth_email_key
        == key
    )
