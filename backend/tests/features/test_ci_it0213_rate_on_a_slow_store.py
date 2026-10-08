"""Binds tests/features/ci_it0213_rate_on_a_slow_store.feature (CI-IT0213-HANG; ST-027;
NFR-023; IT-02-13).

The API, Postgres and the object store are real; the store is reached through
``tests.support.slow_store`` at the write rate measured in scheduled run 37764445816. Each
setting is in the environment before the first step that builds the app (``api``).
"""

from __future__ import annotations

import asyncio
import os
import time
from collections import Counter
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import scorebook as sb
from tests.support.api import ApiDriver
from tests.support.rate_burst import matches_with_video
from tests.support.slow_store import CI_WRITE_RATE, slow_object_store

scenarios("ci_it0213_rate_on_a_slow_store.feature")


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@pytest.fixture
def slow_store(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    with slow_object_store(os.environ["S3_ENDPOINT_URL"], rate=CI_WRITE_RATE) as endpoint:
        monkeypatch.setenv("S3_ENDPOINT_URL", endpoint)
        yield


@given("the object store takes writes at only 64 KiB per second")
def store_is_slow(slow_store: None) -> None:
    pass


@given(parsers.parse("Ivy may send {limit:d} scorebook commands per minute"))
def command_limit(monkeypatch: pytest.MonkeyPatch, limit: int) -> None:
    monkeypatch.setenv("SCOREBOOK_COMMAND_LIMIT_PER_MINUTE", str(limit))
    monkeypatch.setenv("UPLOAD_CREATE_LIMIT_PER_HOUR", "1000")  # the uploads of the arrange
    monkeypatch.setenv("UPLOAD_MAX_OPEN_SESSIONS", "1000")


@given(parsers.parse("Ivy has {count:d} matches whose video has been received"))
def matches_ready(ctx: dict[str, Any], api: ApiDriver, committed_db: Any, count: int) -> None:
    ivy = api.as_user("ivy")
    started = time.monotonic()
    ctx["matches"] = matches_with_video(api, ivy, "CI-IT0213 scenario", count)
    ctx["arrange_s"] = time.monotonic() - started
    ctx["api"], ctx["ivy"] = api, ivy


@when(parsers.parse("Ivy starts a game on all {count:d} matches at the same moment"))
def burst(ctx: dict[str, Any], count: int) -> None:
    assert len(ctx["matches"]) == count
    body = {"first_serving_side": "A", "ends_switched": False}

    async def at_once() -> list[httpx.Response]:
        return list(
            await asyncio.gather(
                *(sb.command(ctx["ivy"], "start_game", version=0, body=body, match_id=m)
                  for m in ctx["matches"])
            )
        )  # fmt: skip

    ctx["responses"] = ctx["api"].run(at_once())


@then(
    parsers.parse("exactly {saved:d} games are started and {refused:d} are refused as rate limited")
)
def outcome(ctx: dict[str, Any], saved: int, refused: int) -> None:
    seen = Counter(
        (r.status_code, None if r.status_code < 400 else r.json()["error"]["code"])
        for r in ctx["responses"]
    )
    assert seen == {(201, None): saved, (429, "rate_limited"): refused}, seen


@then(parsers.parse("getting the {count:d} matches ready took less than {seconds:d} seconds"))
def arrange_time(ctx: dict[str, Any], count: int, seconds: int) -> None:
    assert len(ctx["matches"]) == count
    assert ctx["arrange_s"] < seconds, ctx["arrange_s"]
