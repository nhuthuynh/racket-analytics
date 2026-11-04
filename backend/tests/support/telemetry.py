"""Helpers for IT-05-01 (ST-075a; NFR-069.1; threat notes T5-OB-1, T5-OB-2).

* ``metric_lines`` flattens collected OpenTelemetry metrics into one text line per data point
  (instrument, resource and point attributes), so the NFR-069 log scanner
  (``tests.support.logscan.scan``) can read metric attributes exactly as it reads log lines.
* ``otlp_receiver`` is a real OTLP/HTTP endpoint on ``127.0.0.1`` that decodes every
  ``ExportMetricsServiceRequest`` it is sent. The API and the worker post to it as they would
  post to the collector of ST-075b.
* ``global_metric_reader`` installs one SDK meter provider with an in-memory reader as the
  process-wide provider (once per test session; the app only installs its own when none exists).
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from opentelemetry import metrics
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
    ExportMetricsServiceRequest,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader, MetricsData

from tests.support.paths import BACKEND


def _point_attributes(metric: Any) -> Iterator[dict[str, Any]]:
    for point in getattr(metric.data, "data_points", ()):
        yield dict(point.attributes or {})


def metric_lines(data: MetricsData | None) -> list[str]:
    """One ``instrument resource=... attrs=...`` line per data point (empty if no data)."""
    lines: list[str] = []
    for rm in data.resource_metrics if data else ():
        resource = " ".join(f"{k}={v}" for k, v in sorted(rm.resource.attributes.items()))
        for sm in rm.scope_metrics:
            for metric in sm.metrics:
                for attrs in _point_attributes(metric):
                    pairs = " ".join(f"{k}={v}" for k, v in sorted(attrs.items()))
                    lines.append(f"{metric.name} resource[{resource}] attrs[{pairs}]")
    return lines


_READER: InMemoryMetricReader | None = None


def global_metric_reader() -> InMemoryMetricReader:
    """The session's in-memory reader on the global meter provider (installed on first use)."""
    global _READER
    if _READER is None:
        reader = InMemoryMetricReader()
        metrics.set_meter_provider(MeterProvider(metric_readers=[reader]))
        if not isinstance(metrics.get_meter_provider(), MeterProvider):
            raise RuntimeError("another meter provider is already global; the scan would be blind")
        _READER = reader
    return _READER


# ----------------------------------------------------------------- OTLP/HTTP receiver
@dataclass
class Received:
    paths: list[str] = field(default_factory=list)
    services: set[str] = field(default_factory=set)
    instruments: dict[str, set[str]] = field(default_factory=dict)  # service -> names
    lines: list[str] = field(default_factory=list)


def _decode(body: bytes, into: Received) -> None:
    request = ExportMetricsServiceRequest()
    request.ParseFromString(body)
    for rm in request.resource_metrics:
        resource = {a.key: a.value.string_value for a in rm.resource.attributes}
        service = resource.get("service.name", "")
        into.services.add(service)
        for sm in rm.scope_metrics:
            for metric in sm.metrics:
                into.instruments.setdefault(service, set()).add(metric.name)
                kind = metric.WhichOneof("data")
                for point in getattr(metric, kind).data_points if kind else ():
                    pairs = " ".join(
                        f"{a.key}={a.value.string_value or a.value.int_value}"
                        for a in point.attributes
                    )
                    into.lines.append(f"{metric.name} service={service} attrs[{pairs}]")


@contextmanager
def otlp_receiver() -> Iterator[tuple[str, Received]]:
    """``(metrics endpoint URL, Received)``; the server stops when the block ends."""
    received = Received()
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - http.server API
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            with lock:
                received.paths.append(self.path)
                _decode(body, received)
            self.send_response(200)
            self.send_header("Content-Type", "application/x-protobuf")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *args: Any) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/v1/metrics", received
    finally:
        server.shutdown()
        server.server_close()


# ----------------------------------------------------------------- service processes
# Each script runs the real entry point in a fresh interpreter, so the service installs its own
# OTLP exporter from OTEL_EXPORTER_OTLP_METRICS_ENDPOINT and flushes it when the process exits.
API_SCRIPT = """
from fastapi.testclient import TestClient
from racket.platform.app import create_app
# No lifespan (no ``with``): the startup seeding is not this test's subject and needs a schema.
TestClient(create_app()).get("/st-075a-no-such-route")
"""

# The worker's main loop with one fake job: it records the probe's rejected-upload SLI (as
# ``ProbeStage._reject`` does) and asks the loop to stop, so no database job is needed.
WORKER_SCRIPT = """
import sys
import racket.worker.__main__ as entry
from racket.platform.slis import SLIRecorder, UploadEvent
from racket.worker.runner import ShutdownState

class OneJobRunner:
    def __init__(self, settings, stages, worker_id):
        self.worker_id = worker_id
        self.shutdown = ShutdownState()

    def run_one(self):
        SLIRecorder().upload_event(UploadEvent.REJECTED, reason="not_a_video")
        self.shutdown.stop = True
        return True

entry.Runner = OneJobRunner
sys.exit(entry.main())
"""


def run_service(script: str, endpoint: str, timeout: float = 60) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "APP_ENV": "test",
        "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT": endpoint,
        "OTEL_METRIC_EXPORT_INTERVAL": "200",
        "WORKER_HEARTBEAT_FILE": os.devnull,
    }
    env.pop("OTEL_EXPORTER_OTLP_ENDPOINT", None)  # traces are not this test's subject
    return subprocess.run(  # noqa: S603 - fixed interpreter and script
        [sys.executable, "-c", script],
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
