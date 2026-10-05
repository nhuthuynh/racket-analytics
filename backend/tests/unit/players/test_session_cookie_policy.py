"""Session cookie attributes per APP_ENV (ADR 0029; api-sprint-00 §2; blockers.md 2026-10-05
"E2E WebKit cannot sign in over http://localhost").

ADR 0029 keeps production parity in dev and E2E: the stack is served over https, so the cookie
stays ``__Host-racket_session`` with ``Secure`` everywhere except the in-process ``test`` env.
There is deliberately no switch that drops ``Secure``. Negative cases first.
"""

from __future__ import annotations

import pytest
from starlette.responses import Response

from racket.platform.settings import ConfigurationError, Settings
from racket.players.api import cookie_name, set_session_cookie

BASE = {
    "DATABASE_URL": "postgresql://racket:pg-pass-123@db:5432/racket",
    "S3_BUCKET_MEDIA": "racket-media",
}
DEPLOYED = {
    **BASE,
    "ALLOWED_ORIGINS": "https://app.racket.test",
    "PUBLIC_WEB_ORIGIN": "https://app.racket.test",
    "AUTH_EMAIL_KEY": "k" * 32,
}


def settings_for(app_env: str, **extra: str) -> Settings:
    base = DEPLOYED if app_env in ("staging", "prod") else BASE
    return Settings.from_env({**base, "APP_ENV": app_env, **extra})


def set_cookie_header(settings: Settings) -> str:
    response = Response()
    set_session_cookie(response, settings, "opaque-token", 3600)
    return response.headers["set-cookie"]


# ---------------------------------------------------------------- negative cases first
@pytest.mark.parametrize("app_env", ["staging", "prod"])
def test_deployed_environments_refuse_a_plain_http_sign_in_origin(app_env: str) -> None:
    # The link carries a sign-in token and the session cookie is Secure-only: http would leak
    # the token in transit and the cookie would never come back.
    with pytest.raises(ConfigurationError, match="PUBLIC_WEB_ORIGIN must be https"):
        settings_for(app_env, PUBLIC_WEB_ORIGIN="http://app.racket.test")


@pytest.mark.parametrize("app_env", ["dev", "staging", "prod"])
@pytest.mark.parametrize(
    "knob",
    [
        {"SESSION_COOKIE_INSECURE": "true"},
        {"SESSION_COOKIE_SECURE": "false"},
        {"SECURE_COOKIES": "false"},
    ],
)
def test_no_setting_drops_secure_outside_test(app_env: str, knob: dict[str, str]) -> None:
    settings = settings_for(app_env, **knob)
    header = set_cookie_header(settings)
    assert header.startswith("__Host-racket_session=")
    assert "secure" in header.lower().split("; ")


def test_the_test_env_cookie_is_not_secure_and_not_host_prefixed() -> None:
    # In-process tests run over http://testserver; only they get the plain name.
    header = set_cookie_header(settings_for("test"))
    assert header.startswith("racket_session=")
    assert "secure" not in header.lower().split("; ")


# ---------------------------------------------------------------- positive cases
@pytest.mark.parametrize("app_env", ["dev", "staging", "prod"])
def test_outside_test_the_cookie_meets_the_host_prefix_rules(app_env: str) -> None:
    settings = settings_for(app_env)
    header = set_cookie_header(settings)
    attrs = [a.lower() for a in header.split("; ")]
    assert cookie_name(settings) == "__Host-racket_session"
    # __Host- requires Secure, Path=/ and no Domain (RFC 6265bis 4.1.3.2).
    assert "secure" in attrs
    assert "path=/" in attrs
    assert not any(a.startswith("domain=") for a in attrs)
    assert "httponly" in attrs
    assert "samesite=lax" in attrs


@pytest.mark.parametrize("app_env", ["dev", "test"])
def test_local_environments_accept_an_http_or_https_origin(app_env: str) -> None:
    # dev: https behind web-tls (Compose, ADR 0029) or http for the no-Docker recipe (Chromium).
    for origin in ("http://localhost:3000", "https://localhost:3000"):
        assert settings_for(app_env, PUBLIC_WEB_ORIGIN=origin).public_web_origin == origin
