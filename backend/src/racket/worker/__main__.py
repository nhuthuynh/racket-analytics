"""``python -m racket.worker``: the worker process (ST-007; docs/process/ci-cd.md contracts).

Touches the heartbeat file on every poll loop; on SIGTERM it returns the in-flight job to the
queue and exits 0 within the 10 s budget (NFR-046b; Compose ``stop_grace_period: 12s``).
"""

from __future__ import annotations

import contextlib
import logging
import os
import signal
import sys
import time
from pathlib import Path
from types import FrameType

from opentelemetry import trace

from racket.analysis_jobs.stage import ShutdownRequested
from racket.platform.logs import configure_logging
from racket.platform.settings import ConfigurationError, Settings
from racket.platform.tracing import configure_tracing
from racket.video_ingest.probe import ffprobe_version
from racket.worker.runner import Runner, new_worker_id
from racket.worker.stages import STAGES

log = logging.getLogger("racket.worker")


def main() -> int:
    try:
        settings = Settings.from_env()
    except ConfigurationError as exc:
        print(f"worker refused to start: {exc}", file=sys.stderr)
        return 2
    configure_logging(settings.log_level)
    configure_tracing("racket-worker", settings.otel_exporter_otlp_endpoint)
    runner = Runner(settings, STAGES, worker_id=new_worker_id())
    heartbeat = Path(os.environ.get("WORKER_HEARTBEAT_FILE", "/tmp/worker-heartbeat"))  # noqa: S108

    def on_sigterm(signum: int, frame: FrameType | None) -> None:
        runner.shutdown.stop = True
        if runner.shutdown.in_stage:
            raise ShutdownRequested

    signal.signal(signal.SIGTERM, on_sigterm)
    signal.signal(signal.SIGINT, on_sigterm)
    log.info(
        "worker started",
        extra={"event": "worker.start", "worker_id": runner.worker_id,
               "stages": sorted(STAGES), "ffprobe": ffprobe_version(),
               "settings": settings.redacted()},
    )  # fmt: skip
    try:
        while not runner.shutdown.stop:
            with contextlib.suppress(OSError):
                heartbeat.touch()
            if not runner.run_one():
                deadline = time.monotonic() + settings.worker_poll_seconds
                while not runner.shutdown.stop and time.monotonic() < deadline:
                    time.sleep(0.05)
    except ShutdownRequested:
        pass
    log.info("worker stopped", extra={"event": "worker.stop", "worker_id": runner.worker_id})
    provider = trace.get_tracer_provider()
    shutdown = getattr(provider, "shutdown", None)
    if callable(shutdown):
        shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
