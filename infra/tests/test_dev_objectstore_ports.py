"""CI-OBJSTORE-PORT-RACE: scripts/dev-objectstore.sh allocates distinct ports in one call and
retries a start that died of a port collision ("address already in use") with fresh ports,
up to 3 times; every other startup failure still fails closed at once.

Root cause (main 0415be6, run 40874800467): free_port() was called once per port, closing
each socket before the next call, so two flags could get the same port and a parallel weed
could take one before this weed bound it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from objstore_ports_fixtures import SCRIPT, FakeStore, allocate, fake_store

ALL_PORT_FLAGS = 8  # master, volume, filer, s3; each with its gRPC port


@pytest.fixture
def store(tmp_path: Path) -> Iterator[FakeStore]:
    s = fake_store(tmp_path)
    yield s
    s.run("stop", timeout=60)


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
@pytest.mark.parametrize("count", ["0", "-3", "abc", ""])
def test_allocator_refuses_a_count_that_is_not_a_positive_integer(count: str) -> None:
    res = allocate(count)
    assert res.returncode == 2, (res.stdout, res.stderr)
    assert res.stdout == ""


@pytest.mark.unit
def test_a_failure_that_is_not_a_port_collision_is_not_retried(store: FakeStore) -> None:
    store.mode = "fail"
    res = store.run("start")
    assert res.returncode != 0
    assert "weed exited during startup" in res.stderr
    assert "invalid -dir" in res.stderr  # the weed log tail is still shown
    assert "retry" not in res.stderr
    assert len(store.calls()) == 1
    assert "export S3_ENDPOINT_URL" not in res.stdout


@pytest.mark.unit
def test_a_collision_that_persists_fails_after_three_retries(store: FakeStore) -> None:
    store.mode = "collide:99"
    res = store.run("start")
    assert res.returncode != 0
    assert "weed exited during startup" in res.stderr
    assert "address already in use" in res.stderr
    for n in (1, 2, 3):
        assert f"port collision, retry {n}/3 with fresh ports" in res.stderr
    assert "retry 4/3" not in res.stderr
    assert len(store.calls()) == 4


# ---------------------------------------------------------------- positive cases
@pytest.mark.unit
def test_one_allocation_never_repeats_a_port() -> None:
    for _ in range(60):
        res = allocate(str(ALL_PORT_FLAGS))
        assert res.returncode == 0, res.stderr
        ports = [int(p) for p in res.stdout.split()]
        assert len(ports) == ALL_PORT_FLAGS
        assert len(set(ports)) == ALL_PORT_FLAGS, ports
        assert all(1024 <= p <= 65535 for p in ports)


@pytest.mark.unit
def test_a_large_allocation_is_still_distinct() -> None:
    res = allocate("256")
    assert res.returncode == 0, res.stderr
    ports = res.stdout.split()
    assert len(ports) == 256
    assert len(set(ports)) == 256


@pytest.mark.unit
def test_a_collision_is_retried_with_fresh_ports(store: FakeStore) -> None:
    store.mode = "collide:1"
    res = store.run("start")
    assert res.returncode == 0, res.stderr
    assert "port collision, retry 1/3 with fresh ports" in res.stderr
    assert "retry 2/3" not in res.stderr
    first, second = store.calls()
    assert first != second
    assert f"export S3_ENDPOINT_URL=http://127.0.0.1:{second['s3.port']}" in res.stdout
    assert store.run("status").returncode == 0


@pytest.mark.unit
def test_start_gives_weed_eight_distinct_ports(store: FakeStore) -> None:
    res = store.run("start")
    assert res.returncode == 0, res.stderr
    (call,) = store.calls()
    assert len(call) == ALL_PORT_FLAGS, call
    assert len(set(call.values())) == ALL_PORT_FLAGS, call


# ---------------------------------------------------------------- real SeaweedFS
def real_weed(tmp_path: Path) -> str:
    found = os.environ.get("WEED_BIN") or shutil.which("weed")
    if found:
        return found
    cached = REPO_ROOT / ".local" / "bin" / "weed-3.97"
    if not cached.exists():  # let the script download it (sha256-pinned), as the parity test does
        env = {**os.environ, "RA_DEV_STATE": str(tmp_path / "provision")}
        for cmd in ("start", "stop"):
            subprocess.run(
                ["bash", str(SCRIPT), cmd], capture_output=True, env=env, timeout=300, check=False
            )
    assert cached.exists(), "no SeaweedFS binary (set WEED_BIN or allow the pinned download)"
    return str(cached)


HOLDER_WRAPPER = textwrap.dedent(
    """\
    #!/usr/bin/env bash
    # First start only: occupy the filer port (as a parallel weed would), then run real weed.
    set -euo pipefail
    if [[ ! -e "$WRAP_DIR/held" ]]; then
      touch "$WRAP_DIR/held"
      port=""
      for a in "$@"; do [[ "$a" == -filer.port=* ]] && port="${a#-filer.port=}"; done
      "$WRAP_PY" -c '
    import socket, sys, time
    s = socket.socket(); s.bind(("127.0.0.1", int(sys.argv[1]))); s.listen()
    open(sys.argv[2], "w").write("bound")
    time.sleep(600)' "$port" "$WRAP_DIR/bound" &
      echo $! > "$WRAP_DIR/holder.pid"
      for _ in $(seq 1 100); do [[ -e "$WRAP_DIR/bound" ]] && break; sleep 0.05; done
    fi
    exec "$REAL_WEED" "$@"
    """
)


@pytest.mark.integration
def test_real_weed_survives_a_port_taken_by_another_process(tmp_path: Path) -> None:
    wrap_dir = tmp_path / "wrap"
    wrap_dir.mkdir()
    wrapper = wrap_dir / "weed"
    wrapper.write_text(HOLDER_WRAPPER)
    wrapper.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("S3_", "RA_"))}
    env.update(
        WEED_BIN=str(wrapper),
        REAL_WEED=real_weed(tmp_path),
        WRAP_DIR=str(wrap_dir),
        WRAP_PY=sys.executable,
        RA_DEV_STATE=str(tmp_path / "state"),
    )
    try:
        res = subprocess.run(
            ["bash", str(SCRIPT), "start"],
            capture_output=True,
            text=True,
            env=env,
            timeout=240,
            check=False,
        )
        assert (wrap_dir / "bound").exists(), "the holder never took the filer port"
        assert res.returncode == 0, res.stderr
        assert "address already in use" in res.stderr  # real SeaweedFS log line was seen
        assert "port collision, retry 1/3 with fresh ports" in res.stderr
        assert "export S3_ENDPOINT_URL=http://127.0.0.1:" in res.stdout
    finally:
        subprocess.run(["bash", str(SCRIPT), "stop"], env=env, timeout=60, check=False)
        pid_file = wrap_dir / "holder.pid"
        if pid_file.exists():
            subprocess.run(["kill", pid_file.read_text().strip()], check=False)
