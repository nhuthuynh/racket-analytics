"""ST-075a (NFR-069.1; T5-OB-1): the SLI attributes are a closed allowlist, and the worker
installs the OTLP metric exporter from ``OTEL_EXPORTER_OTLP_METRICS_ENDPOINT`` as the API does.

The rejection ``reason`` is the only attribute whose value comes from a caller as a string; it
is kept only when it is one of the api-sprint-01 §5.2 rejection codes, else ``_OTHER``.
"""

from __future__ import annotations

from typing import Any

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader

import racket.worker.__main__ as worker_entry
from racket.platform import slis
from racket.platform.slis import SLIRecorder, UploadEvent
from racket.video_ingest.domain.policy import Rejection
from racket.worker.runner import ShutdownState


def _reasons(reader: InMemoryMetricReader) -> list[Any]:
    data = reader.get_metrics_data()
    assert data is not None
    return [
        point.attributes.get("reason")
        for rm in data.resource_metrics
        for sm in rm.scope_metrics
        for metric in sm.metrics
        for point in metric.data.data_points  # type: ignore[union-attr]
    ]


@pytest.fixture
def recorder_and_reader() -> tuple[SLIRecorder, InMemoryMetricReader]:
    reader = InMemoryMetricReader()
    return SLIRecorder(MeterProvider(metric_readers=[reader])), reader


# ---------------------------------------------------------------- negative cases first
@pytest.mark.parametrize(
    "planted",
    ["ivy.player@example.com", "carlos", "https://s3/x?X-Amz-Signature=abc", "", "NOT_A_VIDEO"],
)
def test_a_reason_outside_the_rejection_codes_is_recorded_as_other(
    recorder_and_reader: tuple[SLIRecorder, InMemoryMetricReader], planted: str
) -> None:
    recorder, reader = recorder_and_reader

    recorder.upload_event(UploadEvent.REJECTED, reason=planted)

    assert _reasons(reader) == ["_OTHER"]


@pytest.mark.parametrize("code", sorted(r.value for r in Rejection))
def test_every_rejection_code_is_recorded_as_is(
    recorder_and_reader: tuple[SLIRecorder, InMemoryMetricReader], code: str
) -> None:
    recorder, reader = recorder_and_reader

    recorder.upload_event(UploadEvent.REJECTED, reason=code)

    assert _reasons(reader) == [code]


def test_the_allowlist_mirrors_the_upload_context_rejection_codes() -> None:
    # platform must not import video_ingest (DDD); this test keeps the two sets equal.
    assert {r.value for r in Rejection} == slis.REJECTION_REASONS


# ---------------------------------------------------------------- worker export wiring
class _OneLoop:
    def __init__(self, settings: Any, stages: Any, worker_id: str) -> None:
        self.worker_id = worker_id
        self.shutdown = ShutdownState()

    def run_one(self) -> bool:
        self.shutdown.stop = True
        return True


@pytest.mark.parametrize(
    ("endpoint", "expected"),
    [(None, None), ("http://otel:4318/v1/metrics", "http://otel:4318/v1/metrics")],
)
def test_the_worker_configures_the_metric_exporter_from_the_standard_variable(
    monkeypatch: pytest.MonkeyPatch, endpoint: str | None, expected: str | None
) -> None:
    calls: list[tuple[str, str | None]] = []
    for key in ("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", "OTEL_EXPORTER_OTLP_ENDPOINT"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@127.0.0.1:5432/db")
    monkeypatch.setenv("S3_BUCKET_MEDIA", "media")
    monkeypatch.setenv("WORKER_HEARTBEAT_FILE", "/dev/null")
    if endpoint:
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", endpoint)
    monkeypatch.setattr(worker_entry, "Runner", _OneLoop)
    monkeypatch.setattr(worker_entry, "ffprobe_version", lambda: "stub")
    monkeypatch.setattr(worker_entry.signal, "signal", lambda *a: None)  # keep pytest's handlers
    monkeypatch.setattr(worker_entry, "configure_tracing", lambda *a: None)
    # main() shuts down the global tracer provider on exit; keep the session's in-memory one.
    monkeypatch.setattr(worker_entry.trace, "get_tracer_provider", lambda: object())
    monkeypatch.setattr(
        worker_entry, "configure_metrics", lambda *a: calls.append(a), raising=False
    )

    assert worker_entry.main() == 0
    assert calls == [("racket-worker", expected)]
