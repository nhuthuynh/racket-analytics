"""Service-level indicators as OpenTelemetry metrics (ST-024; AQS/OPS-07; api-sprint-01 §10).

Instruments (names confirmed by SRE, docs/ops/sli-metrics.md):

* ``http.server.request.duration`` (histogram, s; OTel HTTP semantic conventions) with
  ``http.request.method`` and ``http.response.status_code``, recorded for every response by
  ``HttpMetricsMiddleware``. **Availability (NFR-041)** = non-5xx / all, 429 excluded.
* ``racket.upload.sessions`` (counter) with ``event`` = created | completed | expired |
  rejected | cancelled, and ``reason`` (a rejection code) on ``rejected`` only. The upload
  context calls ``SLIRecorder.upload_event`` (ST-017/ST-018). **Upload completion (NFR-042)** =
  completed / (created - rejected - cancelled).

No user, match, path or file data goes into attributes (NFR-069). Metrics go to the global
meter provider: a no-op until ``configure_metrics`` installs the OTLP exporter
(``OTEL_EXPORTER_OTLP_METRICS_ENDPOINT``). Alerts come in Sprint 5.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable, Sequence
from enum import StrEnum
from typing import Any

from opentelemetry import metrics
from opentelemetry.metrics import MeterProvider

log = logging.getLogger(__name__)

METER_NAME = "racket"
HTTP_DURATION_INSTRUMENT = "http.server.request.duration"
UPLOAD_SESSIONS_INSTRUMENT = "racket.upload.sessions"
RATE_LIMITED = 429
_KNOWN_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})


class UploadEvent(StrEnum):
    CREATED = "created"
    COMPLETED = "completed"
    EXPIRED = "expired"
    REJECTED = "rejected"
    CANCELLED = "cancelled"  # ships with DELETE (Sprint 2)


def _check_status(status: int) -> int:
    if not 100 <= status <= 599:
        raise ValueError(f"not an HTTP status: {status}")
    return status


def availability(status_codes: Iterable[int]) -> float | None:
    """non-5xx / all, with 429 out of both; ``None`` when nothing is in the base."""
    good = bad = 0
    for status in map(_check_status, status_codes):
        if status == RATE_LIMITED:
            continue
        if status >= 500:
            bad += 1
        else:
            good += 1
    total = good + bad
    return None if total == 0 else good / total


def upload_completion(lifecycles: Iterable[Sequence[str]]) -> tuple[int, int]:
    """(good, base) over per-upload event sequences such as ("created", "completed").

    good = uploads with ``completed``; base = created uploads, minus those rejected by
    validation or cancelled by the user. Expired or still-open uploads stay in the base.
    """
    good = base = 0
    for events in lifecycles:
        kinds = {UploadEvent(_check_event(e)) for e in events}
        if UploadEvent.CREATED not in kinds:
            continue
        if kinds & {UploadEvent.REJECTED, UploadEvent.CANCELLED}:
            continue
        base += 1
        good += UploadEvent.COMPLETED in kinds
    return good, base


def _check_event(event: str) -> str:
    if event not in UploadEvent.__members__.values():
        raise ValueError(f"unknown upload event: {event!r}")
    return event


class SLIRecorder:
    def __init__(self, meter_provider: MeterProvider | None = None) -> None:
        meter = (meter_provider or metrics.get_meter_provider()).get_meter(METER_NAME)
        self._duration = meter.create_histogram(
            HTTP_DURATION_INSTRUMENT, unit="s", description="Duration of HTTP server requests"
        )
        self._uploads = meter.create_counter(
            UPLOAD_SESSIONS_INSTRUMENT,
            unit="{event}",
            description="Upload session lifecycle events (NFR-042 upload completion SLI)",
        )

    def http_response(self, method: str, status: int, seconds: float) -> None:
        method = method.upper()
        self._duration.record(
            max(seconds, 0.0),
            {
                "http.request.method": method if method in _KNOWN_METHODS else "_OTHER",
                "http.response.status_code": _check_status(status),
            },
        )

    def upload_event(self, event: UploadEvent, reason: str | None = None) -> None:
        event = UploadEvent(event)
        if reason is not None and event is not UploadEvent.REJECTED:
            raise ValueError("a reason is only recorded on rejected uploads")
        attrs = {"event": event.value}
        if reason is not None:
            attrs["reason"] = reason
        self._uploads.add(1, attrs)


class HttpMetricsMiddleware:
    """Records every HTTP response; an exception before any response is recorded as 500."""

    def __init__(self, app: Any, recorder: SLIRecorder | None = None) -> None:
        self.app = app
        self.recorder = recorder or SLIRecorder()

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        method = str(scope.get("method", "GET"))
        started = time.monotonic()
        status: int | None = None

        async def send_and_capture(message: Any) -> None:
            nonlocal status
            if message["type"] == "http.response.start" and status is None:
                status = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_and_capture)
        except BaseException:
            self._record(method, status or 500, started)
            raise
        self._record(method, status or 500, started)

    def _record(self, method: str, status: int, started: float) -> None:
        try:
            self.recorder.http_response(method, status, time.monotonic() - started)
        except Exception:  # noqa: BLE001 - telemetry must never break a response
            log.warning("metrics.record_failed", extra={"event": "metrics.record_failed"})


def configure_metrics(service_name: str, otlp_metrics_endpoint: str | None) -> None:
    """Install an OTLP/HTTP metric exporter once; never replace an existing SDK provider."""
    if not otlp_metrics_endpoint:
        return
    from opentelemetry.sdk.metrics import MeterProvider as SdkMeterProvider

    if isinstance(metrics.get_meter_provider(), SdkMeterProvider):
        return
    try:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
    except ImportError:
        log.warning("metrics.exporter_unavailable", extra={"event": "metrics.exporter_unavailable"})
        return
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource

    reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=otlp_metrics_endpoint))
    metrics.set_meter_provider(
        SdkMeterProvider(
            resource=Resource.create({"service.name": service_name}), metric_readers=[reader]
        )
    )
