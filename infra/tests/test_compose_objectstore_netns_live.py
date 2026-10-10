"""Binds the live scenario of tests/features/ci_objstore_stall.feature (CI-OBJSTORE-STALL):
the real Compose object store, in a project of its own on a free port, reports the receive
buffer it was given from inside its own network namespace, and stores the 1.72 MB clip.
Self-cleaning: ``down -v --remove-orphans`` at the end (ADR 0033 rule 3)."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import REPO_ROOT
from pytest_bdd import given, parsers, scenario, then
from store_netns import default_rmem, loopback_segments
from test_compose import ENV_EXAMPLE
from test_compose_worker_identity_live import Stack, free_port, parse_env

pytestmark = pytest.mark.integration
CLIP = REPO_ROOT / "fixtures" / "clips" / "synthetic-60s" / "clip.mp4"  # the CI incidents' clip


@scenario("ci_objstore_stall.feature", "A running store has the receive buffer it was given")
def test_running_store_has_its_receive_buffer() -> None:
    pass


@pytest.fixture(scope="module")
def store_stack(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Stack]:
    tmp: Path = tmp_path_factory.mktemp("objstore-netns")
    env = parse_env(ENV_EXAMPLE.read_text())
    env.update(
        S3_HOST_PORT=str(free_port()),
        DOCKERHUB_REGISTRY=os.environ.get(
            "DOCKERHUB_REGISTRY", env.get("DOCKERHUB_REGISTRY", "docker.io")
        ),
    )
    env_file = tmp / "objstore-netns.env"
    lines = [ln for ln in ENV_EXAMPLE.read_text().splitlines() if ln.split("=", 1)[0] not in env]
    env_file.write_text("\n".join(lines + [f"{k}={v}" for k, v in env.items()]) + "\n")
    st = Stack(f"racket-objnetns-{uuid.uuid4().hex[:8]}", env_file, env)
    try:
        up = st.compose("up", "-d", "--wait", "objectstore")
        assert up.returncode == 0, up.stderr
        init = st.compose("run", "--rm", "objectstore-init")
        assert init.returncode == 0, init.stderr
        yield st
    finally:
        st.compose("down", "-v", "--remove-orphans")


@given("a running Compose object store", target_fixture="stack")
def running_store(store_stack: Stack) -> Stack:
    return store_stack


@then(
    parsers.parse(
        "its network namespace reports a default TCP receive buffer of at least {count:d} "
        "loopback segments"
    )
)
def reports_rmem(stack: Stack, count: int) -> None:
    got = stack.compose("exec", "-T", "objectstore", "cat", "/proc/sys/net/ipv4/tcp_rmem")
    assert got.returncode == 0, got.stderr
    assert loopback_segments(default_rmem(got.stdout)) >= count, got.stdout


@then("it stores the 1.72 MB clip")
def stores_clip(stack: Stack) -> None:
    data = CLIP.read_bytes()
    assert len(data) == 1_724_207
    s3 = stack.s3(stack.env["S3_ACCESS_KEY_ID"], stack.env["S3_SECRET_ACCESS_KEY"])
    key = f"test-own/objstore-netns/{uuid.uuid4().hex}"
    s3.put_object(Bucket=stack.env["S3_BUCKET_MEDIA"], Key=key, Body=data)
    head = s3.head_object(Bucket=stack.env["S3_BUCKET_MEDIA"], Key=key)
    assert head["ContentLength"] == len(data)
    s3.delete_object(Bucket=stack.env["S3_BUCKET_MEDIA"], Key=key)
