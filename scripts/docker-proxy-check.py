#!/usr/bin/env python3
"""Check the Docker daemon's HTTPS proxy before a Compose build; bridge it when stale (FIX-04-1a).

The shared dockerd keeps the proxy it was started with; when the session's agent proxy moves,
BuildKit fails with "proxyconnect ... connection refused" (SRE-V04R1-01). Restarting dockerd
would stop other agents' stacks, so --bridge starts a loopback forwarder on the stale port that
relays to the session proxy (traffic stays on it). Usage: [--bridge] [--daemon-proxy URL]
[--session-proxy URL]; defaults `docker info`, $HTTPS_PROXY. Exit 0 ok/none/bridged, 4 stale,
2 usage or docker error. Stop a bridge with `kill <bridge pid>`.
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

LOOPBACK = {"127.0.0.1", "localhost", "::1"}
State = Enum("State", ["OK", "NO_PROXY", "STALE"])


@dataclass(frozen=True)
class Verdict:
    state: State
    message: str


def parse_proxy(url: str) -> tuple[str, int]:
    """`http://host:port[/]` -> (host, port); anything else is a ValueError."""
    parts = urlsplit(url)
    try:
        host, port = parts.hostname, parts.port
    except ValueError:
        host = port = None
    if not parts.scheme or not host or port is None:
        raise ValueError(f"malformed proxy URL: {url!r}")
    return host, port


def listens(host: str, port: int, timeout: float = 2.0) -> bool:
    with contextlib.suppress(OSError), socket.create_connection((host, port), timeout=timeout):
        return True
    return False


def diagnose(daemon: str, session: str, probe: Callable[[str, int], bool]) -> Verdict:
    if not daemon:
        return Verdict(State.NO_PROXY, "ok: no daemon proxy is set")
    if probe(*parse_proxy(daemon)):
        return Verdict(State.OK, f"ok: daemon proxy {daemon} listens")
    return Verdict(
        State.STALE,
        f"stale: daemon proxy {daemon} does not listen (session proxy: {session or 'unset'}); "
        "Compose builds will fail with 'proxyconnect ... connection refused'.\nFix without "
        "stopping other stacks: re-run with --bridge. Or, only when no other agent's containers "
        "run, restart dockerd with the session's HTTPS_PROXY.",
    )


def bridge_target(daemon: str, session: str) -> tuple[tuple[str, int], tuple[str, int]]:
    listen = parse_proxy(daemon)
    if listen[0] not in LOOPBACK:
        raise ValueError(f"bridge only binds a loopback daemon proxy, not {listen[0]}")
    return listen, parse_proxy(session)


def _pipe(src: socket.socket, dst: socket.socket) -> None:
    with contextlib.suppress(OSError):
        while data := src.recv(65536):
            dst.sendall(data)
    with contextlib.suppress(OSError):
        dst.shutdown(socket.SHUT_WR)  # pass the half-close on


def _relay(client: socket.socket, target: tuple[str, int]) -> None:
    with client, contextlib.suppress(OSError), socket.create_connection(target) as upstream:
        back = threading.Thread(target=_pipe, args=(upstream, client), daemon=True)
        back.start()
        _pipe(client, upstream)
        back.join()


def serve_bridge(listen: tuple[str, int], target: tuple[str, int]) -> None:
    family = socket.AF_INET6 if ":" in listen[0] else socket.AF_INET
    srv = socket.create_server(listen, family=family, backlog=64)
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=_relay, args=(conn, target), daemon=True).start()


def start_bridge(daemon: str, session: str) -> int:
    (lh, lp), (th, tp) = bridge_target(daemon, session)
    cmd = [sys.executable, "-I", os.path.abspath(__file__), "--serve-bridge", f"{lh}:{lp}"]
    proc = subprocess.Popen(  # noqa: S603 - our own script, fixed arguments
        [*cmd, f"{th}:{tp}"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True,
    )  # fmt: skip
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and proc.poll() is None:
        if listens(lh, lp, timeout=0.5):
            return proc.pid
        time.sleep(0.05)
    proc.kill()
    raise OSError(f"bridge did not start listening on {lh}:{lp}")


def _docker_proxy() -> str:
    cmd = ["docker", "info", "--format", "{{.HTTPSProxy}}"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=30)  # noqa: S603
    if res.returncode != 0:
        raise OSError(f"docker info failed: {res.stderr.strip()}")
    return res.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--daemon-proxy", help="default: docker info's HTTPS proxy")
    ap.add_argument("--session-proxy", help="default: $HTTPS_PROXY or $https_proxy")
    ap.add_argument("--bridge", action="store_true", help="forward a stale port to the session")
    ap.add_argument("--serve-bridge", nargs=2, help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if args.serve_bridge:
        serve_bridge(*[(h, int(p)) for h, _, p in (a.rpartition(":") for a in args.serve_bridge)])
    env_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    session = env_proxy if args.session_proxy is None else args.session_proxy
    try:
        daemon = _docker_proxy() if args.daemon_proxy is None else args.daemon_proxy
        print(f"daemon proxy: {daemon or '(none)'}\nsession proxy: {session or '(none)'}")
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
    try:  # bridge: 0 bridged, 4 not bridged, 2 bad URL
        if not session or not listens(*parse_proxy(session)):
            raise OSError(f"stale, not bridged: session proxy does not listen ({session})")
        pid = start_bridge(daemon, session)
    except (ValueError, OSError) as exc:
        print(f"docker-proxy-check: {exc}", file=sys.stderr)
        return 2 if isinstance(exc, ValueError) else 4
    print(f"bridge pid: {pid}\nok: bridged {daemon} -> session proxy {session} (kill {pid})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
