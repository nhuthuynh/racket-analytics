"""FIX-04-1a (G04-01; SRE-V04R1-01): scripts/docker-proxy-check.py. The shared dockerd keeps
the proxy it was started with; a moved session proxy breaks every Compose build (also Sprint 3,
SRE-PURGE-b). Unit: the diagnosis, probe injected. Integration: CLI, `make up`, the real daemon.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys

import pytest
from conftest import REPO_ROOT, SCRIPTS_DIR

TOOL = SCRIPTS_DIR / "docker-proxy-check.py"
D, S = "http://127.0.0.1:34223", "http://127.0.0.1:35001"


def run_check(*args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if "proxy" not in k.lower()}
    cmd = [sys.executable, "-I", str(TOOL), *args]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30, check=False)


@pytest.fixture(scope="module")
def dpc():
    spec = importlib.util.spec_from_file_location("docker_proxy_check", TOOL)
    assert spec is not None, TOOL
    assert spec.loader is not None, TOOL
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses look the module up by name
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- unit: negative cases first
@pytest.mark.unit
@pytest.mark.parametrize("session", [S, ""])
def test_a_daemon_proxy_that_does_not_listen_is_stale(dpc, session: str) -> None:
    v = dpc.diagnose(D, session, lambda h, p: p == 35001)
    assert v.state is dpc.State.STALE
    assert [D in v.message, (session or "unset") in v.message] == [True, True], v.message


@pytest.mark.unit
@pytest.mark.parametrize("url", ["127.0.0.1", "http://127.0.0.1", "http://:80", "http://h:x"])
def test_a_malformed_proxy_url_is_refused(dpc, url: str) -> None:
    with pytest.raises(ValueError, match="malformed proxy URL"):
        dpc.parse_proxy(url)


@pytest.mark.unit
def test_bridge_is_only_offered_for_a_loopback_daemon_proxy(dpc) -> None:
    with pytest.raises(ValueError, match="loopback"):
        dpc.bridge_target("http://10.1.2.3:3128", S)
    assert dpc.bridge_target(D + "/", S) == (("127.0.0.1", 34223), ("127.0.0.1", 35001))


@pytest.mark.unit
def test_a_listening_or_absent_daemon_proxy_is_ok(dpc) -> None:
    assert dpc.diagnose(D, S, lambda h, p: True).state is dpc.State.OK
    none = dpc.diagnose("", S, lambda h, p: False)
    assert (none.state, "no daemon proxy" in none.message) == (dpc.State.NO_PROXY, True)


# ---------------------------------------------------------------- integration
@pytest.mark.integration
def test_cli_malformed_url_exit_2() -> None:
    res = run_check("--daemon-proxy", "not-a-url", "--session-proxy", "")
    assert (res.returncode, "malformed proxy URL" in res.stderr) == (2, True), res


@pytest.mark.integration
def test_make_up_runs_the_check_before_compose() -> None:
    cmd = ["make", "-n", "up"]
    lines = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True).stdout.splitlines()
    check = next(i for i, ln in enumerate(lines) if "docker-proxy-check.py" in ln)
    compose = next(i for i, ln in enumerate(lines) if "up -d --build --wait" in ln)
    assert check < compose, lines


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("docker") is None, reason="no docker CLI on this host")
def test_default_discovery_reads_the_real_daemon_proxy() -> None:
    fmt = ["docker", "info", "--format", "{{.HTTPSProxy}}"]
    info = subprocess.run(fmt, capture_output=True, text=True, check=False)
    if info.returncode != 0:
        pytest.skip(f"docker daemon not reachable: {info.stderr.strip()}")
    res = run_check("--session-proxy", "")
    assert f"daemon proxy: {info.stdout.strip() or '(none)'}" in res.stdout, res
    assert res.returncode in (0, 4), res
