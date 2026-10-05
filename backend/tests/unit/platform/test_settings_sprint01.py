"""Sprint 1 settings (api-sprint-01 §8; ADR 0025; T-ML-7). Negative cases first."""

from __future__ import annotations

import pytest

from racket.platform.settings import ConfigurationError, MissingSettingError, Settings

BASE = {
    "APP_ENV": "dev",
    "DATABASE_URL": "postgresql://racket:pg-pass-123@db:5432/racket",
    "S3_BUCKET_MEDIA": "racket-media",
}
PROD = {
    **BASE,
    "APP_ENV": "prod",
    "ALLOWED_ORIGINS": "https://app.racket.test",
    "PUBLIC_WEB_ORIGIN": "https://app.racket.test",
    "AUTH_EMAIL_KEY": "k" * 32,
}


@pytest.mark.parametrize("name", ["PUBLIC_WEB_ORIGIN", "AUTH_EMAIL_KEY"])
@pytest.mark.parametrize("app_env", ["staging", "prod"])
def test_link_origin_and_email_key_are_required_outside_dev_and_test(
    name: str, app_env: str
) -> None:
    environ = {k: v for k, v in PROD.items() if k != name} | {"APP_ENV": app_env}
    with pytest.raises(MissingSettingError, match=name):
        Settings.from_env(environ)


@pytest.mark.parametrize("origin", ["app.racket.test", "ftp://app.racket.test", "https://"])
def test_a_link_origin_that_is_not_an_http_origin_is_refused(origin: str) -> None:
    with pytest.raises(ConfigurationError, match="PUBLIC_WEB_ORIGIN"):
        Settings.from_env({**PROD, "PUBLIC_WEB_ORIGIN": origin})


def test_a_short_email_key_is_refused_in_prod() -> None:
    with pytest.raises(ConfigurationError, match="AUTH_EMAIL_KEY"):
        Settings.from_env({**PROD, "AUTH_EMAIL_KEY": "short"})


@pytest.mark.parametrize("hops", ["-1", "x"])
def test_bad_proxy_hops_are_refused(hops: str) -> None:
    with pytest.raises(ConfigurationError, match="TRUSTED_PROXY_HOPS"):
        Settings.from_env({**BASE, "TRUSTED_PROXY_HOPS": hops})


def test_defaults_follow_the_contract() -> None:
    s = Settings.from_env(BASE)
    assert s.public_web_origin == "http://localhost:3000"
    assert s.magic_link_ttl_seconds == 900
    assert (s.session_absolute_seconds, s.session_idle_seconds, s.session_max_per_account) == (
        2_592_000,
        604_800,
        10,
    )
    assert (s.auth_link_limit_per_email, s.auth_link_limit_per_ip,
            s.auth_exchange_limit_per_ip, s.auth_window_seconds) == (5, 20, 30, 600)  # fmt: skip
    assert s.trusted_proxy_hops == 0
    assert s.mail_smtp_url == "smtp://mailpit:1025"
    assert s.mail_from == "no-reply@localhost"
    assert s.upload_max_duration_ms == 9_000_000
    assert s.upload_max_frame_pixels == 8_294_400
    assert (s.upload_client_chunk_min_bytes, s.upload_client_chunk_max_bytes) == (
        5_242_880,
        8_388_608,
    )
    assert (s.upload_expiry_seconds, s.upload_expiry_max_seconds) == (86_400, 259_200)
    assert (s.upload_max_open_sessions, s.upload_max_open_bytes,
            s.upload_create_limit_per_hour) == (3, 30_000_000_000, 10)  # fmt: skip
    assert s.worker_stages == ()


def test_values_are_read_and_secrets_redacted() -> None:
    s = Settings.from_env({**PROD, "MAGIC_LINK_TTL_SECONDS": "2", "TRUSTED_PROXY_HOPS": "1",
                           "WORKER_STAGES": "probe, send_sign_in_link"})  # fmt: skip
    assert (s.magic_link_ttl_seconds, s.trusted_proxy_hops) == (2, 1)
    assert s.worker_stages == ("probe", "send_sign_in_link")
    assert s.redacted()["AUTH_EMAIL_KEY"] == "***"
    assert "k" * 32 not in repr(s)


def test_the_test_env_mail_server_is_local() -> None:
    assert Settings.from_env({**BASE, "APP_ENV": "test"}).mail_smtp_url == "smtp://127.0.0.1:1025"
