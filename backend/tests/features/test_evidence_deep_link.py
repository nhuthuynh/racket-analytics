"""API binding of tests/features/evidence_deep_link.feature (QA-ACC for ST-037; FR-027, NFR-055).

"The video plays from 0:56" is checked here as: the link's ``start_ms`` is the rally's start and
the link serves the video (206 to a Range request); the browser spec (E2E-02-04) checks the
playing video. "20 minutes ago" is played with a 2 s TTL (the TTL is configuration, NFR-055).
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import scorebook as sb
from tests.support.api import ApiDriver

scenarios("evidence_deep_link.feature")

TTL_S = 2


@pytest.fixture
def ctx(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setenv("MEDIA_URL_TTL_SECONDS", str(TTL_S))
    return {}


def _clock_ms(text: str) -> int:
    minutes, seconds = text.split(":")
    return (int(minutes) * 60 + int(seconds)) * 1000


def _link(ctx: dict[str, Any], number: int) -> dict[str, Any]:
    api = ctx["api"]
    row = sb.sheet_body(api, "ivy", ctx["match"])["rows"][number - 1]
    method, url = sb.path("media", match_id=ctx["match"], rally_id=row["rally_id"])
    response = api.request("ivy", method, url)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _fetch(url: str) -> int:
    with httpx.Client(timeout=10) as store:
        return store.get(url, headers={"Range": "bytes=0-15"}).status_code


@given(parsers.parse("Ivy's score sheet lists rally {number:d} starting at {clock}"))
def rally_at(ctx: dict[str, Any], api: ApiDriver, number: int, clock: str) -> None:
    ctx["api"] = api
    ctx["match"] = sb.ready_match(api, "ivy", "Deep link")
    sb.tag_before(api, "ivy", ctx["match"], number)
    start = _clock_ms(clock)
    body = {**sb._plain("A"), "start_ms": start, "end_ms": start + 4_000}
    assert sb.tag_one(api, "ivy", ctx["match"], body).status_code == 201
    ctx["number"], ctx["start"] = number, start


@given(parsers.parse("Ivy copied a video link from her score sheet {minutes:d} minutes ago"))
def copied_link(ctx: dict[str, Any], api: ApiDriver, minutes: int) -> None:
    rally_at(ctx, api, 12, "0:56")
    ctx["link"] = _link(ctx, 12)["url"]
    assert _fetch(ctx["link"]) == 206  # positive control: the copied link worked when copied
    time.sleep(TTL_S + 1.5)  # the link is older than its TTL, as 20 minutes are older than 15


@given(parsers.parse("Ivy has a video link for rally {number:d}"))
def has_link(ctx: dict[str, Any], api: ApiDriver, number: int) -> None:
    ctx["api"] = api
    ctx["match"] = sb.ready_tagged_match(api, "ivy", title="Changed link")
    ctx["link"] = _link(ctx, number)["url"]
    assert _fetch(ctx["link"]) == 206


@when(parsers.parse("she opens rally {number:d}'s video link"))
def opens_link(ctx: dict[str, Any], number: int) -> None:
    ctx["media"] = _link(ctx, number)


@when("the link is opened")
def link_opened(ctx: dict[str, Any]) -> None:
    ctx["status"] = _fetch(ctx["link"])


@when("the link is changed by hand")
def link_changed(ctx: dict[str, Any]) -> None:
    head, _, rest = ctx["link"].rpartition("X-Amz-Signature=")
    sig, sep, tail = rest.partition("&")
    changed = f"{head}X-Amz-Signature={sig[:-1]}{'0' if sig[-1] != '0' else '1'}{sep}{tail}"
    ctx["status"] = _fetch(changed)


@then(parsers.parse("the video plays from {clock}"))
def plays_from(ctx: dict[str, Any], clock: str) -> None:
    assert ctx["media"]["start_ms"] == _clock_ms(clock) == ctx["start"]
    assert _fetch(ctx["media"]["url"]) == 206


@then("the video does not play")
def does_not_play(ctx: dict[str, Any]) -> None:
    assert ctx["status"] == 403


@then(parsers.parse("reopening rally {number:d} from the score sheet still works"))
def reopening_works(ctx: dict[str, Any], number: int) -> None:
    assert _fetch(_link(ctx, number)["url"]) == 206
