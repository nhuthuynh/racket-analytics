"""Fixtures for FIX-04-1a: a fake "session proxy" (a TCP echo server) and closed ports."""

from __future__ import annotations

import contextlib
import os
import signal
import socket
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from conftest import SCRIPTS_DIR

TOOL = SCRIPTS_DIR / "docker-proxy-check.py"


def closed_port() -> int:
    """A loopback port where nothing listens (bound, then released)."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextmanager
def echo_server() -> Iterator[int]:
    """A TCP server that echoes each connection's bytes, standing in for the agent proxy."""
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)

    def serve() -> None:
        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                return
            with conn:
                while data := conn.recv(4096):
                    conn.sendall(data)

    threading.Thread(target=serve, daemon=True).start()
    try:
        yield srv.getsockname()[1]
    finally:
        srv.close()


def run_check(*args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if "proxy" not in k.lower()}
    return subprocess.run(
        [sys.executable, "-I", str(TOOL), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        check=False,
    )


def bridge_pid(stdout: str) -> int | None:
    for line in stdout.splitlines():
        if line.startswith("bridge pid:"):
            return int(line.split(":", 1)[1])
    return None


def stop_bridge(stdout: str) -> None:
    pid = bridge_pid(stdout)
    if pid:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGTERM)


def roundtrip(port: int, payload: bytes = b"CONNECT x:443 HTTP/1.1\r\n\r\n") -> bytes:
    with socket.create_connection(("127.0.0.1", port), timeout=5) as c:
        c.sendall(payload)
        c.shutdown(socket.SHUT_WR)
        out = b""
        while chunk := c.recv(4096):
            out += chunk
        return out
