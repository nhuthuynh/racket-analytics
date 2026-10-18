"""Binds tests/features/docker_daemon_proxy.feature (FIX-04-1a): scripts/docker-proxy-check.py
run as a process, with a real TCP echo server as the session proxy and real closed ports."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from docker_proxy_fixtures import closed_port, echo_server, roundtrip, run_check, stop_bridge
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

scenarios("docker_daemon_proxy.feature")


@pytest.fixture
def ctx() -> Iterator[dict]:
    c: dict = {}
    with echo_server() as port:
        c["echo"] = port
        yield c
    if "result" in c:
        stop_bridge(c["result"].stdout)


@given("a session proxy that listens")
def session_listens(ctx: dict) -> None:
    ctx["session"] = f"http://127.0.0.1:{ctx['echo']}"


@given("a session proxy on a port where nothing listens")
def session_closed(ctx: dict) -> None:
    ctx["session"] = f"http://127.0.0.1:{closed_port()}"


@given("a daemon proxy on a port where nothing listens")
def daemon_closed(ctx: dict) -> None:
    ctx["daemon_port"] = closed_port()
    ctx["daemon"] = f"http://127.0.0.1:{ctx['daemon_port']}"


@given("a daemon with no proxy")
def daemon_none(ctx: dict) -> None:
    ctx["daemon"] = ""


def _run(ctx: dict, *extra: str) -> None:
    args = ["--daemon-proxy", ctx["daemon"], "--session-proxy", ctx["session"], *extra]
    ctx["result"] = run_check(*args)


@when("the daemon proxy check runs")
def run_plain(ctx: dict) -> None:
    _run(ctx)


@when("the daemon proxy check runs with --bridge")
def run_bridge(ctx: dict) -> None:
    _run(ctx, "--bridge")


@then(parsers.parse('the check exits {code:d} with "{text}"'))
def exits(ctx: dict, code: int, text: str) -> None:
    res = ctx["result"]
    out = res.stdout + res.stderr
    assert (res.returncode, text in out) == (code, True), out


@then("the output names both proxy addresses")
def names_both(ctx: dict) -> None:
    out = ctx["result"].stdout + ctx["result"].stderr
    assert ctx["daemon"] in out, out
    assert ctx["session"] in out, out


@then("bytes sent to the daemon proxy port come back from the session proxy")
def bytes_come_back(ctx: dict) -> None:
    assert roundtrip(ctx["daemon_port"], b"hello-proxy") == b"hello-proxy"
