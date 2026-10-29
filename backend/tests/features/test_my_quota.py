"""Steps for tests/features/my_quota.feature (QA-VERIFY04R3-04; FR-160; api-sprint-04 §7)."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import tus
from tests.support.api import ApiDriver
from tests.support.flows import create_match

scenarios("my_quota.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given(parsers.parse("quotas are on with a storage quota of {quota:d} bytes"))
def quotas_on(monkeypatch: pytest.MonkeyPatch, quota: int) -> None:
    monkeypatch.setenv("FEATURE_QUOTAS", "true")
    monkeypatch.setenv("STORAGE_QUOTA_BYTES", str(quota))


@given("quotas are off")
def quotas_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_QUOTAS", "false")


@given(parsers.parse("Ivy has an unfinished upload of {length:d} bytes"))
def unfinished(api: ApiDriver, length: int) -> None:
    ivy = api.as_user("ivy")
    api.run(tus.start(ivy, api.run(create_match(ivy, "Open")), length))


@when("Ivy asks for her quota")
def ask(ctx: dict[str, Any], api: ApiDriver) -> None:
    ctx["response"] = api.request("ivy", "GET", "/me/quota")


@then(parsers.parse("she has used {used:d} of {limit:d} bytes"))
def storage(ctx: dict[str, Any], used: int, limit: int) -> None:
    assert ctx["response"].status_code == 200, ctx["response"].text[:300]
    assert ctx["response"].json()["storage"] == {"used_bytes": used, "limit_bytes": limit}


@then(parsers.parse("she has used {used:d} of {limit:d} match creations this hour and need not wait"))
def creations(ctx: dict[str, Any], used: int, limit: int) -> None:
    assert ctx["response"].json()["match_creations"] == {
        "limit": limit, "window_s": 3600, "used": used, "next_slot_at": None
    }  # fmt: skip


@then("the quota is not found")
def not_found(ctx: dict[str, Any]) -> None:
    assert ctx["response"].status_code == 404, ctx["response"].text[:300]
    assert ctx["response"].json()["error"]["code"] == "not_found"
