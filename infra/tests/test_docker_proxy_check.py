"""FIX-04-1a (G04-01; SRE-V04R1-01): scripts/docker-proxy-check.py.

The shared dockerd keeps the HTTPS proxy it was started with. The session's agent proxy moves
to a new port when the session restarts, so BuildKit then fails on every Compose build
("proxyconnect tcp: dial tcp 127.0.0.1:34223: connect: connection refused"), as in Sprint 3
(SRE-PURGE-b, C3-10, DR-02-FE) and VERIFY-04-r1. Unit: the diagnosis (pure, probe injected);
integration: the CLI, the bridge on real sockets, `make up` wiring and the real daemon.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys

import pytest
from conftest import REPO_ROOT
from docker_proxy_fixtures import (
    TOOL,
    bridge_pid,
    closed_port,
    echo_server,
    roundtrip,
    run_check,
    stop_bridge,
)


def _load():
    spec = importlib.util.spec_from_file_location("docker_proxy_check", TOOL)
    assert spec is not None, TOOL
    assert spec.loader is not None, TOOL
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses look the module up by name
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- unit: negative cases first
@pytest.mark.unit
def test_a_daemon_proxy_that_does_not_listen_is_stale() -> None:
    dpc = _load()
    v = dpc.diagnose("http://127.0.0.1:34223", "http://127.0.0.1:35001", lambda h, p: p == 35001)
    assert v.state is dpc.State.STALE
    assert "34223" in v.message
    assert "35001" in v.message


@pytest.mark.unit
def test_stale_even_when_the_session_proxy_is_unknown() -> None:
    dpc = _load()
    v = dpc.diagnose("http://127.0.0.1:34223", "", lambda h, p: False)
    assert v.state is dpc.State.STALE


@pytest.mark.unit
@pytest.mark.parametrize("url", ["127.0.0.1", "http://127.0.0.1", "http://:80", "http://h:x"])
def test_a_malformed_proxy_url_is_refused(url: str) -> None:
    dpc = _load()
    with pytest.raises(ValueError, match="malformed proxy URL"):
        dpc.parse_proxy(url)


@pytest.mark.unit
def test_a_listening_daemon_proxy_is_ok_even_if_it_differs_from_the_session_one() -> None:
    dpc = _load()
    v = dpc.diagnose("http://127.0.0.1:34223", "http://127.0.0.1:35001", lambda h, p: True)
    assert v.state is dpc.State.OK


@pytest.mark.unit
def test_no_daemon_proxy_is_ok_and_says_so() -> None:
    dpc = _load()
    v = dpc.diagnose("", "http://127.0.0.1:35001", lambda h, p: False)
    assert v.state is dpc.State.NO_PROXY
    assert "no daemon proxy" in v.message


@pytest.mark.unit
def test_parse_proxy_gives_host_and_port() -> None:
    dpc = _load()
    assert dpc.parse_proxy("http://127.0.0.1:34223") == ("127.0.0.1", 34223)
    assert dpc.parse_proxy("http://127.0.0.1:34223/") == ("127.0.0.1", 34223)


@pytest.mark.unit
def test_bridge_is_only_offered_for_a_loopback_daemon_proxy() -> None:
    dpc = _load()
    with pytest.raises(ValueError, match="loopback"):
        dpc.bridge_target("http://10.1.2.3:3128", "http://127.0.0.1:35001")
    assert dpc.bridge_target("http://127.0.0.1:34223", "http://127.0.0.1:35001") == (
        ("127.0.0.1", 34223),
        ("127.0.0.1", 35001),
    )


# ---------------------------------------------------------------- integration: CLI and sockets
@pytest.mark.integration
def test_cli_stale_exit_4_names_the_remedy() -> None:
    with echo_server() as live:
        res = run_check(
            "--daemon-proxy",
            f"http://127.0.0.1:{closed_port()}",
            "--session-proxy",
            f"http://127.0.0.1:{live}",
        )
    assert res.returncode == 4, res
    assert "--bridge" in res.stderr
    assert "dockerd" in res.stderr


@pytest.mark.integration
def test_cli_malformed_url_exit_2() -> None:
    res = run_check("--daemon-proxy", "not-a-url", "--session-proxy", "")
    assert res.returncode == 2, res
    assert "malformed proxy URL" in res.stderr, res.stderr


@pytest.mark.integration
def test_bridge_forwards_and_a_second_run_reports_ok() -> None:
    port = closed_port()
    with echo_server() as live:
        args = ("--daemon-proxy", f"http://127.0.0.1:{port}")
        args += ("--session-proxy", f"http://127.0.0.1:{live}")
        first = run_check(*args, "--bridge")
        try:
            assert first.returncode == 0, first
            assert bridge_pid(first.stdout), first.stdout
            assert roundtrip(port, b"x" * 70000) == b"x" * 70000
            again = run_check(*args)
            assert again.returncode == 0, again
            assert "listens" in again.stdout
        finally:
            stop_bridge(first.stdout)


@pytest.mark.integration
def test_make_up_runs_the_check_before_compose() -> None:
    res = subprocess.run(
        ["make", "-n", "up"], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    lines = res.stdout.splitlines()
    check = next(i for i, ln in enumerate(lines) if "docker-proxy-check.py" in ln)
    compose = next(i for i, ln in enumerate(lines) if "up -d --build --wait" in ln)
    assert check < compose, res.stdout


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("docker") is None, reason="no docker CLI on this host")
def test_default_discovery_reads_the_real_daemon_proxy() -> None:
    info = subprocess.run(
        ["docker", "info", "--format", "{{.HTTPSProxy}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if info.returncode != 0:
        pytest.skip(f"docker daemon not reachable: {info.stderr.strip()}")
    res = run_check("--session-proxy", "")
    expected = info.stdout.strip() or "(none)"
    assert f"daemon proxy: {expected}" in res.stdout, res.stdout + res.stderr
    assert res.returncode in (0, 4), res
