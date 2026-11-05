"""Loopback stubs for the ST-075c drill tests: an API that honours the ST-075d fault header
(500 to ``X-Racket-Fault: 5xx``, 200 otherwise) and a Prometheus ``/api/v1/alerts``.

``run_drill`` runs scripts/ops/inject_5xx.py as an operator would: a subprocess with arguments.
"""

from __future__ import annotations

import http.server
import json
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from conftest import SCRIPTS_DIR

INJECT = SCRIPTS_DIR / "ops" / "inject_5xx.py"


@dataclass
class Stub:
    url: str = ""
    honour_seam: bool = True  # False: an APP_ENV=dev stack, the header is ignored
    firing: list[str] = field(default_factory=list)  # alert names Prometheus reports firing
    faulted: int = 0  # requests that carried the fault header
    requests: int = 0
    paths: list[str] = field(default_factory=list)


@contextmanager
def stub_server(stub: Stub) -> Iterator[Stub]:
    lock = threading.Lock()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/api/v1/alerts":
                alerts = [{"labels": {"alertname": n}, "state": "firing"} for n in stub.firing]
                return self._send(200, {"status": "success", "data": {"alerts": alerts}})
            fault = self.headers.get("X-Racket-Fault") == "5xx"
            with lock:
                stub.requests += 1
                stub.faulted += fault
                stub.paths.append(self.path)
            self._send(500 if fault and stub.honour_seam else 200, {"status": "ok"})

        def _send(self, status: int, body: dict) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_: object) -> None:
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    stub.url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield stub
    finally:
        server.shutdown()
        server.server_close()


def run_drill(*args: str, report: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INJECT), *args, "--json", str(report)],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
