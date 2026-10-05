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
        if app_env == "prod" and dev_identity:
            raise ConfigurationError(
                "development sign-in (DEV_IDENTITY_ENABLED=true) is not allowed when APP_ENV=prod"
            )
        database_url = required("DATABASE_URL")
        bucket = required("S3_BUCKET_MEDIA")
        origins = tuple(o.strip() for o in env.get("ALLOWED_ORIGINS", "").split(",") if o.strip())
        if app_env in ("staging", "prod") and not origins:
            missing.append("ALLOWED_ORIGINS")
        if missing:
            raise MissingSettingError(missing)
        if app_env not in APP_ENVS:
            raise ConfigurationError(f"APP_ENV must be one of {', '.join(APP_ENVS)}")

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
        )

    # -------------------------------------------------------------- views
    def redacted(self) -> dict[str, Any]:
        """Every setting for the startup log line, with secrets masked [EP/ENG-20]."""
        view: dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if f.name == "database_url":
                value = _redact_url(value)
            elif f.name in ("s3_secret_access_key", "s3_access_key_id") and value:
                value = REDACTED
            view[f.name.upper()] = value
        return view

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def secure_cookies(self) -> bool:
        return self.app_env != "test"
