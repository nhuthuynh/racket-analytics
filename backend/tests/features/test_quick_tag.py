"""API binding of tests/features/quick_tag.feature (QA-ACC for ST-027; FR-050, NFR-060).

Binds the scenarios whose outcome the API decides; ``web/e2e/sprint-02/quick-tag.spec.ts``
binds every scenario with the on-screen copy and the video moment. Ivy is on side A (slot A1)
with Dana (A2); Carlos (B1) and Sam (B2) are side B.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest
from pytest_bdd import given, parsers, scenario, then, when

from tests.support import scorebook as sb
from tests.support.api import ApiDriver

FEATURE = "quick_tag.feature"
SLOTS = {"herself": "A1", "her own partner": "A2"}
SIDES = {"her side": "A", "the other side": "B"}


def _ending(words: str) -> str:
    return words.replace(" ", "_")


@pytest.fixture
def ctx(api: ApiDriver) -> dict[str, Any]:
    return {"api": api}


@scenario(FEATURE, "Responsible player skipped")
def test_responsible_player_skipped() -> None:
    pass


@scenario(FEATURE, "Every ending can be recorded")
def test_every_ending_can_be_recorded() -> None:
    pass


@scenario(FEATURE, "A replay does not change the score")
def test_a_replay_does_not_change_the_score() -> None:
    pass


@scenario(FEATURE, "Error attributed to the winning side")
def test_error_attributed_to_the_winning_side() -> None:
    pass


@scenario(FEATURE, "14.3.5 Tag before the video is received")
def test_tag_before_the_video_is_received() -> None:
    pass


@scenario(FEATURE, "Two devices tag at once")
def test_two_devices_tag_at_once() -> None:
    pass


@scenario(FEATURE, "Tag a rally")
def test_tag_a_rally_api_part() -> None:
    """The API part; the browser spec checks that the video continues (FR-050)."""


# ------------------------------------------------------------------ Given
@given(parsers.parse('Ivy is tagging her doubles match "{title}"'))
def tagging(ctx: dict[str, Any], title: str) -> None:
    ctx["title"] = title


def _ready(ctx: dict[str, Any]) -> str:
    if "match" not in ctx:
        ctx["match"] = sb.ready_match(ctx["api"], "ivy", ctx["title"])
    return str(ctx["match"])


@given(parsers.parse("rally {number:d} has been marked from start to end"))
def marked(ctx: dict[str, Any], number: int) -> None:
    sb.tag_before(ctx["api"], "ivy", _ready(ctx), number)
    ctx["number"] = number


@given(parsers.parse("Ivy has tagged rally {number:d} without choosing a responsible player"))
def tagged_without_player(ctx: dict[str, Any], number: int) -> None:
    marked(ctx, number)
    body = {**sb._plain("A", "unforced_error"), **sb.times_of(number)}
    body["winning_side"] = "B"
    response = sb.tag_one(ctx["api"], "ivy", ctx["match"], body)
    assert response.status_code == 201, response.text


@given(parsers.parse('the score before rally {number:d} is "{call}"'))
def score_before(ctx: dict[str, Any], number: int, call: str) -> None:
    marked(ctx, number)
    rows = sb.sheet_body(ctx["api"], "ivy", ctx["match"])["rows"]
    assert rows[-1]["score_after"] == call, rows[-1]


@given("Ivy's match has no video yet")
def no_video(ctx: dict[str, Any]) -> None:
    client = ctx["api"].as_user("ivy")
    ctx["match"] = ctx["api"].run(sb.create_doubles(client, "No video yet"))


@given("Ivy tags the same match on her phone and her laptop")
def two_devices(ctx: dict[str, Any]) -> None:
    api = ctx["api"]
    sb.tag_before(api, "ivy", _ready(ctx), 8)
    phone = api.as_user("ivy")
    ctx["laptop"] = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False),
        base_url="http://testserver",
        cookies=phone.cookies,
    )


# ------------------------------------------------------------------ When
@when(parsers.parse('she records it as {side} with "{ending}" by {who}'))
def records_with_player(ctx: dict[str, Any], side: str, ending: str, who: str) -> None:
    body = {**sb._plain(SIDES[side.removeprefix("won by ")], _ending(ending), SLOTS[who])}
    body.update(sb.times_of(ctx["number"]))
    ctx["response"] = sb.tag_one(ctx["api"], "ivy", ctx["match"], body)


@when(parsers.parse('she records it as won by her side with ending "{ending}"'))
def records_ending(ctx: dict[str, Any], ending: str) -> None:
    body = {**sb._plain("A", _ending(ending)), **sb.times_of(ctx["number"])}
    ctx["response"] = sb.tag_one(ctx["api"], "ivy", ctx["match"], body)
    assert ctx["response"].status_code == 201, ctx["response"].text


@when(parsers.parse("she records rally {number:d} as a replay"))
def records_replay(ctx: dict[str, Any], number: int) -> None:
    body = {**sb._plain(None, "replay"), **sb.times_of(number)}
    ctx["response"] = sb.tag_one(ctx["api"], "ivy", ctx["match"], body)
    assert ctx["response"].status_code == 201, ctx["response"].text


@when("she opens the score sheet")
def opens_sheet(ctx: dict[str, Any]) -> None:
    ctx["sheet"] = sb.sheet_body(ctx["api"], "ivy", ctx["match"])


@when("she tries to tag a rally")
def tries_to_tag(ctx: dict[str, Any]) -> None:
    body = {**sb._plain("A"), **sb.times_of(1)}
    ctx["response"] = sb.tag_one(ctx["api"], "ivy", ctx["match"], body)


@when(parsers.parse("both record rally {number:d} at the same moment"))
def both_record(ctx: dict[str, Any], number: int) -> None:
    api, match_id = ctx["api"], ctx["match"]
    phone, laptop = api.as_user("ivy"), ctx["laptop"]
    version = api.run(sb.version_of(phone, match_id))
    body = {**sb._plain("A"), **sb.times_of(number)}

    async def both() -> list[httpx.Response]:
        return list(
            await asyncio.gather(
                sb.command(phone, "tag", version=version, body=body, match_id=match_id),
                sb.command(laptop, "tag", version=version, body=body, match_id=match_id),
            )
        )

    ctx["responses"] = api.run(both())


# ------------------------------------------------------------------ Then
def _row(ctx: dict[str, Any], number: int) -> dict[str, Any]:
    rows = sb.sheet_body(ctx["api"], "ivy", ctx["match"])["rows"]
    row: dict[str, Any] = rows[number - 1]
    assert row["number"] == number
    return row


@then(parsers.parse("rally {number:d} shows the new score"))
def shows_new_score(ctx: dict[str, Any], number: int) -> None:
    assert ctx["response"].status_code == 201, ctx["response"].text
    rows = ctx["response"].json()["sheet"]["rows"]
    assert len(rows) == number
    tags = [*sb.SCENARIO_TAGS[: number - 1], {**sb._plain("B", "unforced_error", "A1")}]
    expected = sb.reference_rows(tags)
    assert sb.taglib.compare_rows(expected, sb.rows_of(ctx["response"].json()["sheet"])) == []


@then("the error is attributed to her")
def attributed_to_her(ctx: dict[str, Any]) -> None:
    assert _row(ctx, ctx["number"])["responsible_player"] == "A1"


@then("the video continues from the end of rally 7, ready to mark rally 8")
def video_continues(ctx: dict[str, Any]) -> None:
    """Browser-only (web/e2e/sprint-02/quick-tag.spec.ts). Here: the tag is saved, so the
    next tag (rally 8) is accepted after it."""
    body = {**sb._plain("A"), **sb.times_of(8)}
    assert sb.tag_one(ctx["api"], "ivy", ctx["match"], body).status_code == 201


@then(parsers.parse("rally {number:d} shows its winner and ending"))
def winner_and_ending(ctx: dict[str, Any], number: int) -> None:
    row = ctx["sheet"]["rows"][number - 1]
    assert (row["winning_side"], row["ending"]) == ("B", "unforced_error")


@then(parsers.parse('rally {number:d} shows "player not tagged"'))
def player_not_tagged(ctx: dict[str, Any], number: int) -> None:
    assert ctx["sheet"]["rows"][number - 1]["responsible_player"] is None


@then(parsers.parse('rally {number:d} shows ending "{ending}" on the score sheet'))
def shows_ending(ctx: dict[str, Any], number: int, ending: str) -> None:
    assert _row(ctx, number)["ending"] == _ending(ending)


@then(parsers.parse('the score after rally {number:d} is still "{call}"'))
def still(ctx: dict[str, Any], number: int, call: str) -> None:
    row = _row(ctx, number)
    assert (row["score_before"], row["score_after"]) == (call, call)


@then("she is told the player who made the error must be on the side that lost the rally")
def wrong_side(ctx: dict[str, Any]) -> None:
    response = ctx["response"]
    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == sb.tagcontract.INVALID_OUTCOME
    assert {"field": "responsible_player", "code": "must_be_on_losing_side"} in error["fields"]
    assert len(sb.sheet_body(ctx["api"], "ivy", ctx["match"])["rows"]) == ctx["number"] - 1


@then("she is told to wait until the video is received")
def told_to_wait(ctx: dict[str, Any]) -> None:
    response = ctx["response"]
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == sb.tagcontract.NOT_READY


@then("no rally is saved")
def no_rally(ctx: dict[str, Any]) -> None:
    assert sb.sheet_body(ctx["api"], "ivy", ctx["match"])["rows"] == []


@then("one tag is saved")
def one_saved(ctx: dict[str, Any]) -> None:
    codes = sorted(r.status_code for r in ctx["responses"])
    assert codes == [201, 409], [r.text[:200] for r in ctx["responses"]]
    assert len(sb.sheet_body(ctx["api"], "ivy", ctx["match"])["rows"]) == 8


@then("the other device is told the match changed and shows the latest score")
def other_told(ctx: dict[str, Any]) -> None:
    stale = next(r for r in ctx["responses"] if r.status_code == 409)
    assert stale.json()["error"]["code"] == sb.tagcontract.STALE
    latest = ctx["api"].run(sb.sheet(ctx["laptop"], ctx["match"]))
    saved = next(r for r in ctx["responses"] if r.status_code == 201)
    assert sb.canonical(latest.json()) == sb.canonical(saved.json()["sheet"])
    ctx["api"].run(ctx["laptop"].aclose())
