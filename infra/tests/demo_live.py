"""Shared helpers for the MVP-03 demo tests (scripts/demo/seed_demo.py).

``run_demo`` runs the real script as `make demo` does. ``live_stack`` names a running Compose
stack from ``RA_DEMO_BASE_URL`` (e.g. https://localhost:3000) and ``RA_DEMO_CACERT`` (the
web-tls root certificate, ADR 0029); tests that need one skip without it, and fail when it is
set but unreachable. ``StubApi`` is a loopback HTTP server that records every request, for the
refusal cases that must send nothing (or nothing that creates data).
"""

from __future__ import annotations

import http.server
import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import pytest
from conftest import REPO_ROOT, SCRIPTS_DIR

SEED = SCRIPTS_DIR / "demo" / "seed_demo.py"
STATS_LINK = re.compile(r"/matches/([A-Za-z0-9_-]+)/stats\b")


def _load(name: str) -> Any:
    if name in sys.modules:
        return sys.modules[name]
    measure = SCRIPTS_DIR / "measure"
    if str(measure) not in sys.path:
        sys.path.insert(0, str(measure))  # livehttp imports measurelib by name
    spec = importlib.util.spec_from_file_location(name, measure / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_demo(*args: str, timeout: float = 300) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("APP_ENV", "DEV_IDENTITY"))}
    return subprocess.run(
        [sys.executable, str(SEED), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        timeout=timeout,
        check=False,
    )


def match_id_in(output: str) -> str | None:
    found = STATS_LINK.search(output)
    return found.group(1) if found else None


@dataclass(frozen=True)
class LiveStack:
    base_url: str
    cacert: str | None

    def demo_args(self) -> list[str]:
        args = ["--base-url", self.base_url]
        return [*args, "--cacert", self.cacert] if self.cacert else args

    def client(self, username: str = "ivy") -> Any:
        """A client of the stack's public API, signed in as a dev user."""
        livehttp = _load("livehttp")
        ctx = livehttp.ssl_context(self.cacert, False)
        c = livehttp.Client(f"{self.base_url}/api", self.base_url, ctx)
        r = c.request("POST", "/dev/sign-in", json_body={"username": username})
        assert r.status == 204, f"dev sign-in as {username}: {r.status}"
        return c


def live_stack() -> LiveStack:
    base = os.environ.get("RA_DEMO_BASE_URL", "").rstrip("/")
    if not base:
        pytest.skip("needs a running dev stack: set RA_DEMO_BASE_URL (and RA_DEMO_CACERT)")
    return LiveStack(base, os.environ.get("RA_DEMO_CACERT") or None)


@dataclass
class StubApi:
    """Answers 404 to everything and records each request line (method, path)."""

    requests: list[tuple[str, str]] = field(default_factory=list)
    url: str = ""


@contextmanager
def stub_api() -> Iterator[StubApi]:
    stub = StubApi()

    class Handler(http.server.BaseHTTPRequestHandler):
        def _answer(self) -> None:
            stub.requests.append((self.command, self.path))
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            body = json.dumps({"error": {"code": "not_found"}}).encode()
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = do_PATCH = do_HEAD = do_DELETE = _answer

        def log_message(self, *_: object) -> None:
            return

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    stub.url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield stub
    finally:
        server.shutdown()
        server.server_close()
