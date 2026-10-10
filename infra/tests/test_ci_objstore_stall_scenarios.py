"""Binds the configuration scenarios of tests/features/ci_objstore_stall.feature
(CI-OBJSTORE-STALL; NFR-073, NFR-074) to the real infra/compose.yaml."""

from __future__ import annotations

from typing import Any

import pytest
import yaml
from pytest_bdd import given, parsers, scenario, then
from store_netns import LOOPBACK_MSS, default_rmem, loopback_segments
from test_compose import COMPOSE

pytestmark = pytest.mark.unit
FEATURE = "ci_objstore_stall.feature"


@scenario(FEATURE, "The runner's 128 KiB default receive buffer is too small for loopback segments")
def test_runner_default_is_too_small() -> None:
    pass


@scenario(FEATURE, "The Compose store's network namespace holds at least 16 loopback segments")
def test_compose_store_holds_sixteen_segments() -> None:
    pass


@given(
    parsers.parse("a store network namespace whose default TCP receive buffer is {size:d} bytes"),
    target_fixture="rmem",
)
def runner_rmem(size: int) -> int:
    return size


@then(parsers.parse("that buffer holds fewer than {count:d} loopback segments of {mss:d} bytes"))
def fewer_segments(rmem: int, count: int, mss: int) -> None:
    assert mss == LOOPBACK_MSS
    assert loopback_segments(rmem) < count


@given("the Compose object store service", target_fixture="store")
def store_service() -> dict[str, Any]:
    return yaml.safe_load(COMPOSE.read_text())["services"]["objectstore"]


@then(
    parsers.parse(
        "its default TCP receive buffer holds at least {count:d} loopback segments of {mss:d} bytes"
    )
)
def enough_segments(store: dict[str, Any], count: int, mss: int) -> None:
    assert mss == LOOPBACK_MSS
    sysctls = store.get("sysctls") or {}
    assert "net.ipv4.tcp_rmem" in sysctls, sysctls
    assert loopback_segments(default_rmem(str(sysctls["net.ipv4.tcp_rmem"]))) >= count


@then("the buffer is set as a namespaced sysctl of the store, with no added capability")
def no_capability(store: dict[str, Any]) -> None:
    assert isinstance(store.get("sysctls"), dict), "a mapping of namespaced net.* sysctls"
    assert all(k.startswith("net.") for k in store["sysctls"]), store["sysctls"]
    assert not store.get("cap_add"), store.get("cap_add")
    assert not store.get("privileged"), "the store never runs privileged"
