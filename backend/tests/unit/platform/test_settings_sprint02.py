"""Sprint 2 carry-over settings rules (C-19, SEC-R5-S1-04).

The development sign-in may only be switched on in dev and test; staging refuses to start with
it, like prod (red first: staging started).
"""

from __future__ import annotations

import pytest

from racket.platform.settings import ConfigurationError, Settings

pytestmark = pytest.mark.unit

BASE = {"DATABASE_URL": "postgresql://u:p@h/d", "S3_BUCKET_MEDIA": "b"}
DEPLOYED = {"ALLOWED_ORIGINS": "https://x", "PUBLIC_WEB_ORIGIN": "https://x",
            "AUTH_EMAIL_KEY": "k" * 32}  # fmt: skip


@pytest.mark.parametrize("app_env", ["staging", "prod"])
def test_dev_identity_is_refused_outside_dev_and_test(app_env: str) -> None:
    with pytest.raises(ConfigurationError, match="DEV_IDENTITY_ENABLED"):
        Settings.from_env(BASE | DEPLOYED | {"APP_ENV": app_env, "DEV_IDENTITY_ENABLED": "true"})


@pytest.mark.parametrize("app_env", ["dev", "test"])
def test_dev_identity_may_be_on_in_dev_and_test(app_env: str) -> None:
    settings = Settings.from_env(BASE | {"APP_ENV": app_env, "DEV_IDENTITY_ENABLED": "true"})
    assert settings.dev_identity_enabled


def test_staging_starts_with_dev_identity_off() -> None:
    settings = Settings.from_env(BASE | DEPLOYED | {"APP_ENV": "staging"})
    assert not settings.dev_identity_enabled
