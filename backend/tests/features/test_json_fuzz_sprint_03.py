"""API binding of tests/features/json_fuzz_sprint_03.feature (QA-FUZZ-3; rule L11; NFR-023,
NFR-058). The named hidden characters of IT-03-12 on the match delete confirmation, and the
delete racing a tag. "Unchanged": every row holding the match id and the scorebook row counts
are equal before and after. Written red first: ``red_until`` ST-050.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenario, then, when

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

pytestmark = [pytest.mark.red_until(story="ST-050")]

FEATURE = "json_fuzz_sprint_03.feature"
HIDDEN = {"a NUL": "\x00", "a lone surrogate": "\ud800", "a line separator": "\u2028"}


@scenario(FEATURE, "A delete confirmation with a hidden character is refused")
def test_a_delete_confirmation_with_a_hidden_character_is_refused() -> None:
    pass


@scenario(FEATURE, "A delete and a tag at the same moment")
def test_a_delete_and_a_tag_at_the_same_moment() -> None:
    pass


@pytest.fixture
def ctx(api: ApiDriver, committed_db: Any) -> dict[str, Any]:
    return {"api": api, "db": committed_db}


def _state(ctx: dict[str, Any]) -> dict[str, int]:
    return {**st.rows_holding(ctx["db"], [ctx["match"]]), **sb.row_counts(ctx["db"])}


@given("Ivy has a match with a received video")
def received(ctx: dict[str, Any]) -> None:
    client = ctx["api"].as_user("ivy")
    ctx["match"] = ctx["api"].run(sb.create_doubles(client, "QA-FUZZ-3"))
    ctx["api"].run(sb.receive_video(client, ctx["match"]))
    ctx["before"] = _state(ctx)


@when(parsers.parse('she deletes it typing "delete" with {character} inside'))
def deletes_with_hidden(ctx: dict[str, Any], character: str) -> None:
    raw = json.dumps({"confirm": "del" + HIDDEN[character] + "ete"}).encode()  # \\uXXXX escapes
    method, url = st.statscontract.path("delete_match", match_id=ctx["match"])
    headers = {"Content-Type": "application/json"}
    ctx["response"] = ctx["api"].request("ivy", method, url, content=raw, headers=headers)


@then("she is told the deletion is not confirmed")
def not_confirmed(ctx: dict[str, Any]) -> None:
    assert st.refusal(ctx["response"]) == st.CONFIRMATION_REQUIRED, ctx["response"].text


@then("her match is unchanged")
def unchanged(ctx: dict[str, Any]) -> None:
    assert _state(ctx) == ctx["before"]
    method, url = sb.path("sheet", match_id=ctx["match"])
    assert ctx["api"].request("ivy", method, url).status_code == 200


@given("Ivy has a match ready to tag")
def ready(ctx: dict[str, Any]) -> None:
    ctx["match"] = sb.ready_match(ctx["api"], "ivy", "QA-FUZZ-3 race")


@when("she tags a rally and deletes the match at the same moment")
def race(ctx: dict[str, Any]) -> None:
    api, match_id = ctx["api"], ctx["match"]
    client = api.as_user("ivy")
    version = api.run(sb.version_of(client, match_id))
    tag_method, tag_url = sb.path("tag", match_id=match_id)
    del_method, del_url = st.statscontract.path("delete_match", match_id=match_id)

    async def both() -> tuple[int, int]:
        tagged, deleted = await asyncio.gather(
            client.request(
                tag_method,
                tag_url,
                json=st.WORKED_EXAMPLE[0],
                headers={sb.tagcontract.VERSION_HEADER: f'"{version}"'},
            ),
            client.request(del_method, del_url, json=st.statscontract.CONFIRM_BODY),
        )
        return tagged.status_code, deleted.status_code

    ctx["tag_code"], ctx["delete_code"] = api.run(both())


@then("the delete succeeds")
def delete_succeeds(ctx: dict[str, Any]) -> None:
    assert ctx["delete_code"] in st.statscontract.DELETE_OK, ctx["delete_code"]
    assert ctx["tag_code"] in (201, 404, 409), ctx["tag_code"]


@then("nothing of the match can be read any more")
def nothing_readable(ctx: dict[str, Any]) -> None:
    match_id = ctx["match"]
    reads = (sb.path("sheet", match_id=match_id), st.statscontract.path("stats", match_id=match_id))
    for method, url in reads:
        assert ctx["api"].request("ivy", method, url).status_code == 404, url
