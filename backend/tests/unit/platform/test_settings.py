"""Settings (ST-005; sprint-00 §5 TDD plan, in order; AQS/OPS-01 config only from env)."""

from __future__ import annotations

import pytest

from racket.platform.settings import ConfigurationError, MissingSettingError, Settings

BASE = {
    "APP_ENV": "dev",
    "DATABASE_URL": "postgresql://racket:pg-pass-123@db:5432/racket",
    "S3_ENDPOINT_URL": "http://objectstore:8333",
    "S3_ACCESS_KEY_ID": "AKIDEXAMPLE",
    "S3_SECRET_ACCESS_KEY": "s3-secret-value-456",
    "S3_BUCKET_MEDIA": "racket-media",
}


def env(**overrides: str | None) -> dict[str, str]:
    merged: dict[str, str | None] = {**BASE, **overrides}
    return {k: v for k, v in merged.items() if v is not None}


# 1. missing required variable -> startup error naming the variable
def test_missing_database_url_is_named() -> None:
    with pytest.raises(MissingSettingError, match="DATABASE_URL"):
        Settings.from_env(env(DATABASE_URL=None))


def test_every_missing_variable_is_named_at_once() -> None:
    with pytest.raises(MissingSettingError) as err:
        Settings.from_env(env(DATABASE_URL=None, S3_BUCKET_MEDIA=None, APP_ENV=None))

    assert {"DATABASE_URL", "S3_BUCKET_MEDIA", "APP_ENV"} <= set(err.value.names)


def test_blank_value_counts_as_missing() -> None:
    with pytest.raises(MissingSettingError, match="DATABASE_URL"):
        Settings.from_env(env(DATABASE_URL="  "))


def test_missing_setting_is_a_configuration_error() -> None:
    assert issubclass(MissingSettingError, ConfigurationError)


def test_unknown_app_env_is_refused() -> None:
    with pytest.raises(ConfigurationError, match="APP_ENV"):
        Settings.from_env(env(APP_ENV="production-ish"))


def test_non_integer_limit_is_refused_and_named() -> None:
    with pytest.raises(ConfigurationError, match="UPLOAD_MAX_BYTES"):
        Settings.from_env(env(UPLOAD_MAX_BYTES="ten gigabytes"))


# 2. APP_ENV=prod with the dev identity provider enabled -> startup error
def test_prod_with_dev_identity_is_refused() -> None:
    with pytest.raises(ConfigurationError) as err:
        Settings.from_env(
            env(APP_ENV="prod", DEV_IDENTITY_ENABLED="true", ALLOWED_ORIGINS="https://x")
        )

    message = str(err.value).lower()
    assert "development sign-in" in message
    assert "prod" in message


@pytest.mark.parametrize("app_env", ["staging", "prod"])
def test_allowed_origins_is_required_outside_dev_and_test(app_env: str) -> None:
    with pytest.raises(MissingSettingError, match="ALLOWED_ORIGINS"):
        Settings.from_env(env(APP_ENV=app_env))


def test_dev_identity_defaults_on_only_in_test() -> None:
    assert Settings.from_env(env(APP_ENV="test")).dev_identity_enabled is True
    assert Settings.from_env(env(APP_ENV="dev")).dev_identity_enabled is False
    assert Settings.from_env(env(APP_ENV="dev", DEV_IDENTITY_ENABLED="true")).dev_identity_enabled


def test_boolean_flag_rejects_garbage() -> None:
    with pytest.raises(ConfigurationError, match="DEV_IDENTITY_ENABLED"):
        Settings.from_env(env(DEV_IDENTITY_ENABLED="yes please"))


def test_fault_injection_is_dropped_outside_test() -> None:
    spec = "probe:fail_after_partial_write"

    assert Settings.from_env(env(APP_ENV="dev", RACKET_FAULT_INJECTION=spec)).fault_injection == ""
    assert Settings.from_env(env(APP_ENV="test", RACKET_FAULT_INJECTION=spec)).fault_injection == (
        spec
    )


def test_defaults_follow_the_api_contract() -> None:
    settings = Settings.from_env(env())

    assert settings.upload_max_bytes == 10_000_000_000
    assert settings.upload_max_chunk_bytes == 64 * 1024 * 1024
    assert settings.upload_part_min_bytes == 5 * 1024 * 1024
    assert settings.api_public_path_prefix == ""
    assert settings.allowed_origins == ()


# 3. secrets are redacted in the startup log line
def test_redacted_view_hides_every_secret() -> None:
    settings = Settings.from_env(env())

    text = repr(settings.redacted()) + repr(settings) + str(settings)

    assert "pg-pass-123" not in text
    assert "s3-secret-value-456" not in text
    assert "postgresql://racket:***@db:5432/racket" in repr(settings.redacted())
    assert settings.redacted()["S3_SECRET_ACCESS_KEY"] == "***"


def test_dev_identity_in_prod_is_reported_before_other_missing_settings() -> None:
    """The unsafe combination wins over a missing ALLOWED_ORIGINS, so the message is clear."""
    with pytest.raises(ConfigurationError, match="development sign-in"):
        Settings.from_env(env(APP_ENV="prod", DEV_IDENTITY_ENABLED="true"))
