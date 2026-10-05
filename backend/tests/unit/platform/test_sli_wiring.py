"""ST-024: the API emits the availability SLI for every response, and the metric exporter is
configured from the standard OTel variable (AQS/OPS-07)."""

from __future__ import annotations

from racket.platform.app import create_app
from racket.platform.settings import Settings
from racket.platform.slis import HttpMetricsMiddleware

BASE = {
    "APP_ENV": "test",
    "DATABASE_URL": "postgresql://u:p@127.0.0.1:5432/db",
    "S3_BUCKET_MEDIA": "media",
}


def test_metrics_endpoint_is_off_unless_configured() -> None:
    assert Settings.from_env(BASE).otel_exporter_otlp_metrics_endpoint is None


def test_metrics_endpoint_is_read_from_the_standard_variable() -> None:
    env = {**BASE, "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT": "http://otel:4318/v1/metrics"}
    assert Settings.from_env(env).otel_exporter_otlp_metrics_endpoint == (
        "http://otel:4318/v1/metrics"
    )


def test_the_availability_middleware_is_the_outermost_layer() -> None:
    app = create_app(Settings.from_env(BASE))
    # Starlette lists user middleware outermost first; outermost sees error-mapped 5xx too.
    assert app.user_middleware[0].cls is HttpMetricsMiddleware
