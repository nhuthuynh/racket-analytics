"""Binds tests/features/docker_daemon_proxy.feature (FIX-04-1a): scripts/docker-proxy-check.py
run as a process, with a real TCP echo server as the session proxy and real closed ports."""

from __future__ import annotations

import contextlib
import os
import signal
import socket
import threading
from collections.abc import Iterator

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from test_docker_proxy_check import run_check

pytestmark = [pytest.mark.scenario, pytest.mark.integration]
scenarios("docker_daemon_proxy.feature")


def closed_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _echo(conn: socket.socket) -> None:
    with conn:
        while data := conn.recv(4096):
            conn.sendall(data)


@pytest.fixture
def ctx() -> Iterator[dict]:
    srv = socket.create_server(("127.0.0.1", 0))

    def serve() -> None:  # the fake session proxy: echoes every connection
        with contextlib.suppress(OSError):
            while True:
                threading.Thread(target=_echo, args=(srv.accept()[0],), daemon=True).start()

    threading.Thread(target=serve, daemon=True).start()
    with srv:
        c: dict = {"echo": srv.getsockname()[1]}
        yield c
    for line in c["result"].stdout.splitlines() if "result" in c else []:
        if line.startswith("bridge pid:"):
            with contextlib.suppress(ProcessLookupError):
                os.kill(int(line.split(":", 1)[1]), signal.SIGTERM)


@given("a session proxy that listens")
def session_listens(ctx: dict) -> None:
    ctx["session"] = f"http://127.0.0.1:{ctx['echo']}"


@given("a session proxy on a port where nothing listens")
def session_closed(ctx: dict) -> None:
    ctx["session"] = f"http://127.0.0.1:{closed_port()}"


@given("a daemon proxy on a port where nothing listens")
def daemon_closed(ctx: dict) -> None:
    ctx["port"] = closed_port()
    ctx["daemon"] = f"http://127.0.0.1:{ctx['port']}"


def _run(ctx: dict, *extra: str):
    return run_check("--daemon-proxy", ctx["daemon"], "--session-proxy", ctx["session"], *extra)


@when("the daemon proxy check runs")
def run_plain(ctx: dict) -> None:
    ctx["result"] = _run(ctx)


@when("the daemon proxy check runs with --bridge")
def run_bridge(ctx: dict) -> None:
    ctx["result"] = _run(ctx, "--bridge")


@then(parsers.parse('the check exits {code:d} with "{text}"'))
def exits(ctx: dict, code: int, text: str) -> None:
    res = ctx["result"]
    assert (res.returncode, text in res.stdout + res.stderr) == (code, True), res


@then(parsers.parse('the output names both proxy addresses and "{remedy}"'))
def names_both(ctx: dict, remedy: str) -> None:
    out = ctx["result"].stderr
    assert [ctx["daemon"] in out, ctx["session"] in out, remedy in out] == [True] * 3, out


@then(parsers.parse("{n:d} bytes sent to the daemon proxy port come back from the session proxy"))
def bytes_come_back(ctx: dict, n: int) -> None:
    with socket.create_connection(("127.0.0.1", ctx["port"]), timeout=5) as c:
        c.sendall(b"x" * n)
        c.shutdown(socket.SHUT_WR)
        got = b"".join(iter(lambda: c.recv(4096), b""))
    assert got == b"x" * n


@then(parsers.parse('a second check without --bridge exits {code:d} with "{text}"'))
def second_check(ctx: dict, code: int, text: str) -> None:
    res = _run(ctx)
    assert (res.returncode, text in res.stdout) == (code, True), res
