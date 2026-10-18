#!/usr/bin/env python3
"""Check the Docker daemon's HTTPS proxy before a Compose build; bridge it when stale (FIX-04-1a).

The shared dockerd keeps the HTTPS proxy it was started with. When the session's agent proxy
moves to another port, the daemon proxy no longer listens and every BuildKit pull fails with
"proxyconnect tcp: dial tcp 127.0.0.1:<old>: connect: connection refused" (SRE-V04R1-01).
Restarting the shared dockerd would stop other agents' stacks, so `--bridge` instead starts a
small loopback forwarder on the stale port that relays to the session proxy (traffic still goes
through the session proxy and its policy).

    python3 scripts/docker-proxy-check.py [--bridge] [--daemon-proxy URL] [--session-proxy URL]

Defaults: daemon proxy from `docker info --format '{{.HTTPSProxy}}'`, session proxy from
HTTPS_PROXY / https_proxy. Exit 0 ok (listens, none, or bridged), 4 stale, 2 usage or docker
error. Stop a bridge with `kill <bridge pid>`.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlsplit

Probe = Callable[[str, int], bool]
LOOPBACK = {"127.0.0.1", "localhost", "::1"}


class State(Enum):
    OK = "ok"
    NO_PROXY = "no-proxy"
    STALE = "stale"


@dataclass(frozen=True)
class Verdict:
    state: State
    message: str


def parse_proxy(url: str) -> tuple[str, int]:
    """`http://host:port[/]` -> (host, port); anything else is a ValueError."""
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise ValueError(f"malformed proxy URL: {url!r}") from exc
    if not parts.scheme or not parts.hostname or port is None:
        raise ValueError(f"malformed proxy URL: {url!r}")
    return parts.hostname, port


def listens(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def diagnose(daemon: str, session: str, probe: Probe) -> Verdict:
    if not daemon:
        return Verdict(State.NO_PROXY, "ok: no daemon proxy is set")
    if probe(*parse_proxy(daemon)):
        return Verdict(State.OK, f"ok: daemon proxy {daemon} listens")
    return Verdict(
        State.STALE,
        f"stale: daemon proxy {daemon} does not listen (session proxy: {session or 'unset'}); "
        "Compose builds will fail with 'proxyconnect ... connection refused'.\n"
        "Fix without stopping other stacks: re-run with --bridge. Or, only when no other "
        "agent's containers run, restart dockerd with the session's HTTPS_PROXY.",
    )


def bridge_target(daemon: str, session: str) -> tuple[tuple[str, int], tuple[str, int]]:
    listen = parse_proxy(daemon)
    if listen[0] not in LOOPBACK:
        raise ValueError(f"bridge only binds a loopback daemon proxy, not {listen[0]}")
    return listen, parse_proxy(session)


# ---------------------------------------------------------------- the bridge (forwarder)
def _pipe(src: socket.socket, dst: socket.socket) -> None:
    try:
        while data := src.recv(65536):
            dst.sendall(data)
    except OSError:
        pass
    finally:
        with contextlib.suppress(OSError):
            dst.shutdown(socket.SHUT_WR)


def _relay(client: socket.socket, target: tuple[str, int]) -> None:
    with client:
        try:
            upstream = socket.create_connection(target, timeout=10)
        except OSError:
            return
        upstream.settimeout(None)
        with upstream:
            back = threading.Thread(target=_pipe, args=(upstream, client), daemon=True)
            back.start()
            _pipe(client, upstream)
            back.join()


def serve_bridge(listen: tuple[str, int], target: tuple[str, int]) -> None:
    srv = socket.socket(socket.AF_INET6 if ":" in listen[0] else socket.AF_INET)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(listen)
    srv.listen(64)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=_relay, args=(conn, target), daemon=True).start()


def start_bridge(daemon: str, session: str) -> int:
    (lh, lp), (th, tp) = bridge_target(daemon, session)
    cmd = [sys.executable, "-I", os.path.abspath(__file__), "--serve-bridge"]
    cmd += [f"{lh}:{lp}", f"{th}:{tp}"]
    proc = subprocess.Popen(  # noqa: S603 - our own script, fixed arguments
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if listens(lh, lp, timeout=0.5):
            return proc.pid
        if proc.poll() is not None:
            break
        time.sleep(0.05)
    proc.kill()
    raise OSError(f"bridge did not start listening on {lh}:{lp}")


# ---------------------------------------------------------------- CLI
def daemon_proxy_from_docker() -> str:
    res = subprocess.run(
        ["docker", "info", "--format", "{{.HTTPSProxy}}"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if res.returncode != 0:
        raise OSError(f"docker info failed: {res.stderr.strip()}")
    return res.stdout.strip()


def _hostport(value: str) -> tuple[str, int]:
    host, _, port = value.rpartition(":")
    return host, int(port)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--daemon-proxy", help="default: docker info's HTTPS proxy")
    ap.add_argument("--session-proxy", help="default: $HTTPS_PROXY or $https_proxy")
    ap.add_argument("--bridge", action="store_true", help="forward a stale port to the session")
    ap.add_argument("--serve-bridge", nargs=2, metavar=("LISTEN", "TARGET"), help=argparse.SUPPRESS)
    args = ap.parse_args(argv)

    if args.serve_bridge:
        serve_bridge(_hostport(args.serve_bridge[0]), _hostport(args.serve_bridge[1]))
        return 0

    session = args.session_proxy
    if session is None:
        session = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    try:
        daemon = args.daemon_proxy if args.daemon_proxy is not None else daemon_proxy_from_docker()
        print(f"daemon proxy: {daemon or '(none)'}")
        print(f"session proxy: {session or '(none)'}")
        verdict = diagnose(daemon, session, listens)
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"docker-proxy-check: {exc}", file=sys.stderr)
        return 2

    if verdict.state is not State.STALE:
        print(verdict.message)
        return 0
    if not args.bridge:
        print(verdict.message, file=sys.stderr)
        return 4
    return _bridge(daemon, session)


def _bridge(daemon: str, session: str) -> int:
    """Start the forwarder for a stale daemon proxy: 0 bridged, 4 not bridged, 2 bad URL."""
    try:
        if not session or not listens(*parse_proxy(session)):
            why = f"session proxy does not listen ({session or 'unset'})"
            print(f"stale, not bridged: {why}", file=sys.stderr)
            return 4
        pid = start_bridge(daemon, session)
    except ValueError as exc:
        print(f"docker-proxy-check: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"docker-proxy-check: {exc}", file=sys.stderr)
        return 4
    print(f"bridge pid: {pid}")
    print(f"ok: bridged daemon proxy {daemon} -> session proxy {session} (stop: kill {pid})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
