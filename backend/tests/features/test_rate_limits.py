"""Steps for tests/features/rate_limits.feature (ST-072a; FR-160; api-sprint-04 §7)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
import sqlalchemy as sa
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import contract, tus
from tests.support.api import ApiDriver
from tests.support.flows import create_match

scenarios("rate_limits.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


def _flags(monkeypatch: pytest.MonkeyPatch, on: bool, quota: int | None = None) -> None:
    monkeypatch.setenv("FEATURE_QUOTAS", "true" if on else "false")
    if quota is not None:
        monkeypatch.setenv("STORAGE_QUOTA_BYTES", str(quota))


@given("quotas are on")
def quotas_on(monkeypatch: pytest.MonkeyPatch) -> None:
    _flags(monkeypatch, True)


@given(parsers.parse("quotas are {state} with a storage quota of {quota:d} bytes"))
def quotas_with(monkeypatch: pytest.MonkeyPatch, state: str, quota: int) -> None:
    _flags(monkeypatch, state == "on", quota)


@pytest.fixture
def driver(ctx: dict[str, Any], api: ApiDriver) -> ApiDriver:
    ctx["api"] = api
    return api


@given(parsers.parse("Ivy has created {n:d} matches in the last hour"))
def created(driver: ApiDriver, n: int) -> None:
    ivy = driver.as_user("ivy")
    for i in range(n):
        driver.run(create_match(ivy, f"Hour {i}"))


@given(parsers.parse("Ivy has an unfinished upload of {length:d} bytes"))
def unfinished(driver: ApiDriver, length: int) -> None:
    ivy = driver.as_user("ivy")
    driver.run(tus.start(ivy, driver.run(create_match(ivy, "Open")), length))


@when("Ivy creates another match")
def create_another(ctx: dict[str, Any], driver: ApiDriver) -> None:
    body = {"title": "One more", "format": "doubles"}
    ctx["response"] = driver.request("ivy", "POST", contract.MATCHES, json=body)


@when(parsers.parse("Ivy starts an upload of {length:d} bytes on another match"))
def start_upload(ctx: dict[str, Any], driver: ApiDriver, length: int) -> None:
    ivy = driver.as_user("ivy")
    ctx["match_id"] = driver.run(create_match(ivy, "Another"))
    ctx["response"] = driver.run(tus.create(ivy, ctx["match_id"], length))


def _error(response: httpx.Response, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status, response.text[:300]
    error: dict[str, Any] = response.json()["error"]
    assert error["code"] == code, error
    return error


@then("it is refused as rate limited with a time within the hour")
def rate_limited(ctx: dict[str, Any]) -> None:
    error = _error(ctx["response"], 429, "rate_limited")
    retry_at = datetime.fromisoformat(error["retry_at"].replace("Z", "+00:00"))
    now = datetime.now(UTC)
    assert now < retry_at <= now + timedelta(hours=1), error
    assert int(ctx["response"].headers["Retry-After"]) >= 1


@then(parsers.parse("Ivy still has {n:d} matches"))
def still_has(ctx: dict[str, Any], n: int) -> None:
    listed = ctx["api"].request("ivy", "GET", contract.MATCHES)
    assert len(listed.json()["items"]) == n


@then(parsers.parse("it is refused as over the storage quota with {used:d} used of {limit:d}"))
def over_quota(ctx: dict[str, Any], used: int, limit: int) -> None:
    error = _error(ctx["response"], 429, "storage_quota_exceeded")
    assert error["retry_at"] is None
    assert error["quota"] == {"used_bytes": used, "limit_bytes": limit, "requested_bytes": 50000}
    assert set(error) == {"code", "message", "support_ref", "retry_at", "quota"}


@then("nothing is stored for that match")
def nothing_stored(ctx: dict[str, Any], committed_db: Any) -> None:
    with committed_db.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT count(*) FROM upload_sessions WHERE match_id = :m"),
            {"m": ctx["match_id"]},
        ).scalar_one()
    assert rows == 0
    match = ctx["api"].request("ivy", "GET", f"{contract.MATCHES}/{ctx['match_id']}").json()
    assert (match["upload"], match["rejection"], match["status"]) == (None, None, "awaiting_upload")


@then("the match is created")
def match_created(ctx: dict[str, Any]) -> None:
    assert ctx["response"].status_code == 201, ctx["response"].text[:300]


@then(parsers.parse("an upload of {length:d} bytes on it is accepted"))
def upload_accepted(ctx: dict[str, Any], length: int) -> None:
    ivy = ctx["api"].as_user("ivy")
    response = ctx["api"].run(tus.create(ivy, ctx["response"].json()["id"], length))
    assert response.status_code == 201, response.text[:300]
