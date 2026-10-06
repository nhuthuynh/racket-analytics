"""Process settings, read only from the environment (ST-005; AQS/OPS-01, NFR-081).

``Settings.from_env(environ)`` is a pure function of a mapping, so it is unit-testable. It
refuses to build on bad configuration: missing required variables are all named at once
(``MissingSettingError``), and unsafe combinations raise ``ConfigurationError``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from typing import Any
from urllib.parse import urlsplit, urlunsplit

APP_ENVS = ("dev", "test", "staging", "prod")
_TRUE = {"true", "1"}
_FALSE = {"false", "0"}
REDACTED = "***"
DEV_WEB_ORIGIN = "https://localhost:3000"  # C-25: the dev stack is https (ADR 0029)
DEV_EMAIL_KEY = "dev-only-email-key-not-a-secret"  # dev/test only; prod requires its own
EMAIL_KEY_MIN = 32
MEDIA_URL_TTL_MAX = 15 * 60  # NFR-055
_SECRETS = ("s3_secret_access_key", "s3_access_key_id", "auth_email_key")


class ConfigurationError(RuntimeError):
    """The process must not start with this configuration."""


class MissingSettingError(ConfigurationError):
    def __init__(self, names: list[str]) -> None:
        self.names = tuple(names)
        super().__init__(
            "missing required setting(s): " + ", ".join(self.names) + " (see infra/env.example)"
        )


def _redact_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.password is None:
        return url
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    netloc = f"{parts.username}:{REDACTED}@{host}" if parts.username else f"{REDACTED}@{host}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str = field(repr=False)
    s3_bucket_media: str
    s3_endpoint_url: str | None = None
    s3_access_key_id: str | None = field(default=None, repr=False)
    s3_secret_access_key: str | None = field(default=None, repr=False)
    s3_region: str = "us-east-1"
    dev_identity_enabled: bool = False
    log_level: str = "INFO"
    upload_max_bytes: int = 10_000_000_000
    upload_max_chunk_bytes: int = 64 * 1024 * 1024
    upload_part_min_bytes: int = 5 * 1024 * 1024
    api_public_path_prefix: str = ""
    allowed_origins: tuple[str, ...] = ()
    pipeline_version: str = "v0"
    fault_injection: str = ""
    worker_lease_seconds: int = 15
    worker_poll_seconds: float = 1.0
    otel_exporter_otlp_endpoint: str | None = None
    otel_exporter_otlp_metrics_endpoint: str | None = None  # SLI metrics (ST-024); off if unset
    # ---- Sprint 1 (api-sprint-01 §8)
    public_web_origin: str = DEV_WEB_ORIGIN
    mail_smtp_url: str = "smtp://mailpit:1025"
    mail_from: str = "no-reply@localhost"
    auth_email_key: str = field(default=DEV_EMAIL_KEY, repr=False)
    magic_link_ttl_seconds: int = 900
    session_absolute_seconds: int = 2_592_000
    session_idle_seconds: int = 604_800
    session_max_per_account: int = 10
    auth_link_limit_per_email: int = 5
    auth_link_limit_per_ip: int = 20
    auth_exchange_limit_per_ip: int = 30
    auth_window_seconds: int = 600
    trusted_proxy_hops: int = 0
    upload_max_duration_ms: int = 9_000_000
    upload_max_frame_pixels: int = 8_294_400
    upload_client_chunk_min_bytes: int = 5_242_880
    upload_client_chunk_max_bytes: int = 8_388_608
    upload_expiry_seconds: int = 86_400
    upload_expiry_max_seconds: int = 259_200
    upload_max_open_sessions: int = 3
    upload_max_open_bytes: int = 30_000_000_000
    upload_create_limit_per_hour: int = 10
    worker_stages: tuple[str, ...] = ()  # empty: every registered stage
    # ---- Sprint 2 (ST-037; NFR-055): rally video links
    media_url_ttl_seconds: int = 300
    s3_public_endpoint_url: str | None = None  # the origin the browser reaches the store at
    # ---- Sprint 2 (SEC-S2-R1-01): scorebook command rate per account and caps per match
    scorebook_command_limit_per_minute: int = 300
    scorebook_max_rallies: int = 500
    scorebook_max_changes: int = 2000

    # -------------------------------------------------------------- construction
    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        env = {k: v.strip() for k, v in (os.environ if environ is None else environ).items()}
        missing: list[str] = []

        def required(name: str) -> str:
            value = env.get(name, "")
            if not value:
                missing.append(name)
            return value

        def optional(name: str) -> str | None:
            return env.get(name) or None

        def integer(name: str, default: int, minimum: int = 1) -> int:
            raw = env.get(name, "")
            if not raw:
                return default
            try:
                value = int(raw)
            except ValueError:
                raise ConfigurationError(f"{name} must be an integer") from None
            if value < minimum:
                raise ConfigurationError(f"{name} must be at least {minimum}")
            return value

        def boolean(name: str, default: bool) -> bool:
            raw = env.get(name, "").lower()
            if not raw:
                return default
            if raw in _TRUE:
                return True
            if raw in _FALSE:
                return False
            raise ConfigurationError(f"{name} must be 'true' or 'false'")

        app_env = required("APP_ENV")
        # The unsafe combination is reported first, whatever else is missing.
        dev_identity = boolean("DEV_IDENTITY_ENABLED", default=app_env == "test")
        if dev_identity and app_env not in ("dev", "test"):  # C-19: staging too (SEC-R5-S1-04)
            raise ConfigurationError(
                "development sign-in (DEV_IDENTITY_ENABLED=true) is not allowed when "
                f"APP_ENV={app_env}"
            )
        database_url = required("DATABASE_URL")
        bucket = required("S3_BUCKET_MEDIA")
        origins = tuple(o.strip() for o in env.get("ALLOWED_ORIGINS", "").split(",") if o.strip())
        deployed = app_env in ("staging", "prod")
        if deployed and not origins:
            missing.append("ALLOWED_ORIGINS")
        # T-ML-7: the sign-in link base comes only from configuration; dev and test fall back
        # to the local web origin, deployed environments must set it (and the HMAC key).
        web_origin = required("PUBLIC_WEB_ORIGIN") if deployed else env.get("PUBLIC_WEB_ORIGIN")
        email_secret = required("AUTH_EMAIL_KEY") if deployed else env.get("AUTH_EMAIL_KEY")
        if missing:
            raise MissingSettingError(missing)
        if app_env not in APP_ENVS:
            raise ConfigurationError(f"APP_ENV must be one of {', '.join(APP_ENVS)}")
        web_origin = (web_origin or DEV_WEB_ORIGIN).rstrip("/")
        parts = urlsplit(web_origin)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ConfigurationError("PUBLIC_WEB_ORIGIN must be an http(s) origin")
        if deployed and parts.scheme != "https":
            # The link carries a sign-in token and the session cookie is Secure (ADR 0029).
            raise ConfigurationError("PUBLIC_WEB_ORIGIN must be https outside dev and test")
        if deployed and len(email_secret or "") < EMAIL_KEY_MIN:
            raise ConfigurationError(
                f"AUTH_EMAIL_KEY must have at least {EMAIL_KEY_MIN} characters"
            )
        stages = tuple(x.strip() for x in env.get("WORKER_STAGES", "").split(",") if x.strip())
        media_ttl = integer("MEDIA_URL_TTL_SECONDS", 300)
        if media_ttl > MEDIA_URL_TTL_MAX:
            raise ConfigurationError(f"MEDIA_URL_TTL_SECONDS must be at most {MEDIA_URL_TTL_MAX}")

        return cls(
            app_env=app_env,
            database_url=database_url,
            s3_bucket_media=bucket,
            s3_endpoint_url=optional("S3_ENDPOINT_URL"),
            s3_access_key_id=optional("S3_ACCESS_KEY_ID"),
            s3_secret_access_key=optional("S3_SECRET_ACCESS_KEY"),
            s3_region=env.get("S3_REGION") or "us-east-1",
            dev_identity_enabled=dev_identity,
            log_level=(env.get("LOG_LEVEL") or "INFO").upper(),
            upload_max_bytes=integer("UPLOAD_MAX_BYTES", 10_000_000_000),
            upload_max_chunk_bytes=integer("UPLOAD_MAX_CHUNK_BYTES", 64 * 1024 * 1024),
            upload_part_min_bytes=integer("UPLOAD_PART_MIN_BYTES", 5 * 1024 * 1024),
            api_public_path_prefix=(env.get("API_PUBLIC_PATH_PREFIX") or "").rstrip("/"),
            allowed_origins=origins,
            pipeline_version=env.get("PIPELINE_VERSION") or "v0",
            # Test-only seam (ADR 0012): never honoured outside APP_ENV=test.
            fault_injection=env.get("RACKET_FAULT_INJECTION", "") if app_env == "test" else "",
            worker_lease_seconds=integer("WORKER_LEASE_SECONDS", 15),
            worker_poll_seconds=integer("WORKER_POLL_MS", 1000) / 1000,
            otel_exporter_otlp_endpoint=optional("OTEL_EXPORTER_OTLP_ENDPOINT"),
            otel_exporter_otlp_metrics_endpoint=optional("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT"),
            public_web_origin=web_origin,
            mail_smtp_url=env.get("MAIL_SMTP_URL")
            or ("smtp://127.0.0.1:1025" if app_env == "test" else "smtp://mailpit:1025"),
            mail_from=env.get("MAIL_FROM") or "no-reply@localhost",
            auth_email_key=email_secret or DEV_EMAIL_KEY,
            magic_link_ttl_seconds=integer("MAGIC_LINK_TTL_SECONDS", 900),
            session_absolute_seconds=integer("SESSION_ABSOLUTE_SECONDS", 2_592_000),
            session_idle_seconds=integer("SESSION_IDLE_SECONDS", 604_800),
            session_max_per_account=integer("SESSION_MAX_PER_ACCOUNT", 10),
            auth_link_limit_per_email=integer("AUTH_LINK_LIMIT_PER_EMAIL", 5),
            auth_link_limit_per_ip=integer("AUTH_LINK_LIMIT_PER_IP", 20),
            auth_exchange_limit_per_ip=integer("AUTH_EXCHANGE_LIMIT_PER_IP", 30),
            auth_window_seconds=integer("AUTH_WINDOW_SECONDS", 600),
            trusted_proxy_hops=integer("TRUSTED_PROXY_HOPS", 0, minimum=0),
            upload_max_duration_ms=integer("UPLOAD_MAX_DURATION_MS", 9_000_000),
            upload_max_frame_pixels=integer("UPLOAD_MAX_FRAME_PIXELS", 8_294_400),
            upload_client_chunk_min_bytes=integer("UPLOAD_CLIENT_CHUNK_MIN_BYTES", 5_242_880),
            upload_client_chunk_max_bytes=integer("UPLOAD_CLIENT_CHUNK_MAX_BYTES", 8_388_608),
            upload_expiry_seconds=integer("UPLOAD_EXPIRY_SECONDS", 86_400),
            upload_expiry_max_seconds=integer("UPLOAD_EXPIRY_MAX_SECONDS", 259_200),
            upload_max_open_sessions=integer("UPLOAD_MAX_OPEN_SESSIONS", 3),
            upload_max_open_bytes=integer("UPLOAD_MAX_OPEN_BYTES", 30_000_000_000),
            upload_create_limit_per_hour=integer("UPLOAD_CREATE_LIMIT_PER_HOUR", 10),
            worker_stages=stages,
            media_url_ttl_seconds=media_ttl,
            s3_public_endpoint_url=(optional("S3_PUBLIC_ENDPOINT_URL") or "").rstrip("/") or None,
            scorebook_command_limit_per_minute=integer("SCOREBOOK_COMMAND_LIMIT_PER_MINUTE", 300),
            scorebook_max_rallies=integer("SCOREBOOK_MAX_RALLIES", 500),
            scorebook_max_changes=integer("SCOREBOOK_MAX_CHANGES", 2000),
        )

    # -------------------------------------------------------------- views
    def redacted(self) -> dict[str, Any]:
        """Every setting for the startup log line, with secrets masked [EP/ENG-20]."""
        view: dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if f.name == "database_url":
                value = _redact_url(value)
            elif f.name in _SECRETS and value:
                value = REDACTED
            view[f.name.upper()] = value
        return view

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def secure_cookies(self) -> bool:
        return self.app_env != "test"
