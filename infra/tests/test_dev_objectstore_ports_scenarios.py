"""Binds tests/features/dev_objectstore_ports.feature (CI-OBJSTORE-PORT-RACE).

The real scripts/dev-objectstore.sh, run as a developer runs it, against a stand-in weed
binary (objstore_ports_fixtures.FAKE_WEED) that collides on demand.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from objstore_ports_fixtures import FakeStore, fake_store
from pytest_bdd import given, parsers, scenarios, then, when

pytestmark = pytest.mark.integration
scenarios("dev_objectstore_ports.feature")


@dataclass
class Dev:
    store: FakeStore
    runs: list[subprocess.CompletedProcess[str]] = field(default_factory=list)

    @property
    def last(self) -> subprocess.CompletedProcess[str]:
        return self.runs[-1]


@pytest.fixture
def dev(tmp_path: Path) -> Iterator[Dev]:
    d = Dev(store=fake_store(tmp_path))
    yield d
    d.store.run("stop", timeout=60)


@given(parsers.parse('the object store binary fails at startup with "{message}"'))
def fails_at_startup(dev: Dev, message: str) -> None:
    assert message == "invalid -dir"  # the stand-in's non-bind failure
    dev.store.mode = "fail"


@given(
    parsers.parse('the object store binary hits "address already in use" on its first {n:d} start')
)
@given(
    parsers.parse('the object store binary hits "address already in use" on its first {n:d} starts')
)
def collides(dev: Dev, n: int) -> None:
    dev.store.mode = f"collide:{n}"


@given("the object store binary starts normally")
def starts_normally(dev: Dev) -> None:
    dev.store.mode = "ok"


@when("the developer starts the local object store")
def start(dev: Dev) -> None:
    dev.runs.append(dev.store.run("start"))


@then(parsers.parse('the start fails with "{message}"'))
def start_fails(dev: Dev, message: str) -> None:
    assert dev.last.returncode != 0
    assert message in dev.last.stderr
    assert "export S3_ENDPOINT_URL" not in dev.last.stdout


@then("the store starts and prints the S3 endpoint")
def store_starts(dev: Dev) -> None:
    assert dev.last.returncode == 0, dev.last.stderr
    s3_port = dev.store.calls()[-1]["s3.port"]
    assert f"export S3_ENDPOINT_URL=http://127.0.0.1:{s3_port}" in dev.last.stdout


@then(parsers.parse("the object store binary was started {n:d} time"))
@then(parsers.parse("the object store binary was started {n:d} times"))
def started_n_times(dev: Dev, n: int) -> None:
    assert len(dev.store.calls()) == n


@then("no retry was logged")
def no_retry(dev: Dev) -> None:
    assert "retry" not in dev.last.stderr


@then(parsers.parse('the log says "{text}"'))
def log_says(dev: Dev, text: str) -> None:
    assert text in dev.last.stderr


@then("the second start used different ports from the first")
def fresh_ports(dev: Dev) -> None:
    first, second = dev.store.calls()[:2]
    assert first != second


@then(parsers.parse("the {n:d} ports given to the object store binary are distinct"))
def distinct_ports(dev: Dev, n: int) -> None:
    (call,) = dev.store.calls()
    assert len(call) == n, call
    assert len(set(call.values())) == n, call
