"""API binding of tests/features/upload_quota.feature (C-02; NFR-023). The repeated parallel
cases and the other limits are IT-02-11."""

from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any

import httpx
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import tus
from tests.support.api import ApiDriver
from tests.support.flows import create_match

scenarios("upload_quota.feature")


@pytest.fixture
def ctx(api: ApiDriver, committed_db: Any) -> dict[str, Any]:
    return {"api": api}


@given(parsers.parse("Ivy may have {limit:d} unfinished uploads at once"))
def may_have(ctx: dict[str, Any], limit: int) -> None:
    settings = ctx["api"].app.state.settings
    assert settings.upload_max_open_sessions == limit


@when(parsers.parse("{n:d} uploads are started for her at the same moment"))
def started(ctx: dict[str, Any], n: int) -> None:
    api = ctx["api"]
    ivy = api.as_user("ivy")
    matches = [api.run(create_match(ivy, f"Quota {i}")) for i in range(n)]

    async def burst() -> list[httpx.Response]:
        return list(await asyncio.gather(*(tus.create(ivy, m, 102_400) for m in matches)))

    ctx["responses"] = api.run(burst())


@then(parsers.parse("exactly {n:d} are accepted"))
def accepted(ctx: dict[str, Any], n: int) -> None:
    assert sum(1 for r in ctx["responses"] if r.status_code == 201) == n


@then(parsers.parse("the other {n:d} are refused with a reason"))
def refused(ctx: dict[str, Any], n: int) -> None:
    refused = [r for r in ctx["responses"] if r.status_code != 201]
    assert len(refused) == n
    reasons = Counter((r.status_code, r.json()["error"]["code"]) for r in refused)
    assert reasons == {(429, "upload_quota_exceeded"): n}
