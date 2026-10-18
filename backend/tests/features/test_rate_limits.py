"""Steps for tests/features/rate_limits.feature (ST-072a; FR-160; api-sprint-04 §7)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

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


@given(parsers.re(r"quotas are on( with a storage quota of (?P<quota>\d+) bytes)?"))
def quotas_on(monkeypatch: pytest.MonkeyPatch, quota: str | None) -> None:
    monkeypatch.setenv("FEATURE_QUOTAS", "true")
    if quota:
        monkeypatch.setenv("STORAGE_QUOTA_BYTES", quota)


@given(parsers.parse("Ivy has created {n:d} matches in the last hour"))
def created(ctx: dict[str, Any], api: ApiDriver, n: int) -> None:
    ctx["api"] = api
    for i in range(n):
        api.run(create_match(api.as_user("ivy"), f"Hour {i}"))


@given(parsers.parse("Ivy has an unfinished upload of {length:d} bytes"))
def unfinished(ctx: dict[str, Any], api: ApiDriver, length: int) -> None:
    ctx["api"] = api
    ivy = api.as_user("ivy")
    api.run(tus.start(ivy, api.run(create_match(ivy, "Open")), length))


@when("Ivy creates another match")
def create_another(ctx: dict[str, Any]) -> None:
    body = {"title": "One more", "format": "doubles"}
    ctx["response"] = ctx["api"].request("ivy", "POST", contract.MATCHES, json=body)


@when(parsers.parse("Ivy starts an upload of {length:d} bytes on another match"))
def start_upload(ctx: dict[str, Any], length: int) -> None:
    api, ivy = ctx["api"], ctx["api"].as_user("ivy")
    ctx["match_id"] = api.run(create_match(ivy, "Another"))
    ctx["response"] = api.run(tus.create(ivy, ctx["match_id"], length))


def _error(ctx: dict[str, Any], code: str) -> dict[str, Any]:
    assert ctx["response"].status_code == 429, ctx["response"].text[:300]
    error: dict[str, Any] = ctx["response"].json()["error"]
    assert error["code"] == code, error
    return error


@then("it is refused as rate limited with a time within the hour")
def rate_limited(ctx: dict[str, Any]) -> None:
    error = _error(ctx, "rate_limited")
    retry_at = datetime.fromisoformat(error["retry_at"].replace("Z", "+00:00"))
    now = datetime.now(UTC)
    assert now < retry_at <= now + timedelta(hours=1), error
    assert int(ctx["response"].headers["Retry-After"]) >= 1


@then(parsers.parse("Ivy still has {n:d} matches"))
def still_has(ctx: dict[str, Any], n: int) -> None:
    assert len(ctx["api"].request("ivy", "GET", contract.MATCHES).json()["items"]) == n


@then(parsers.parse("it is refused as over the storage quota with {used:d} used of {limit:d}"))
def over_quota(ctx: dict[str, Any], used: int, limit: int) -> None:
    error = _error(ctx, "storage_quota_exceeded")
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
