"""API binding of tests/features/match_deletion.feature (QA-ACC-3 for ST-050; FR-006, NFR-066,
ADR 0006). Binds "Delete a tagged match" and "Someone else's match"; the confirmation text is
screen copy (browser binding E2E-03-01, dialog X-01). "Anywhere in her account": the match,
its stats, score sheet and video answer 404 and the list omits it. "No stored file or record":
the information-schema inventory and the object keys the database knew (IT-03-06's checks).
Written red first: ``red_until`` ST-050.

ST-050a (TCR row in docs/sprints/03/decisions/ST-050a.md): the module marker is lifted;
"Someone else's match" passes and joins the per-PR gate. "Delete a tagged match" runs the purge
in its last step, so it stays ``red_until`` ST-050b, marked on its own.
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from pytest_bdd import given, scenario, then, when

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

FEATURE = "match_deletion.feature"


@pytest.mark.red_until(story="ST-050b")
@scenario(FEATURE, "Delete a tagged match")
def test_delete_a_tagged_match() -> None:
    pass


@scenario(FEATURE, "Someone else's match")
def test_someone_elses_match() -> None:
    pass


@pytest.fixture
def ctx(api: ApiDriver, committed_db: Any) -> dict[str, Any]:
    return {"api": api, "db": committed_db}


def _gone(ctx: dict[str, Any]) -> bool:
    api, match_id = ctx["api"], ctx["match"]
    reads = [
        st.statscontract.path("match", match_id=match_id),
        st.statscontract.path("stats", match_id=match_id),
        sb.path("sheet", match_id=match_id),
        sb.path("video", match_id=match_id),
    ]
    if any(api.request("ivy", m, u).status_code != 404 for m, u in reads):
        return False
    body = st.request(api, "ivy", "matches").json()
    items = body["items"] if isinstance(body, dict) else body
    return all(item["id"] != match_id for item in items)


@given("Ivy has a tagged match with stats")
@given("Carlos knows the address of Ivy's match")
def tagged_match(ctx: dict[str, Any]) -> None:
    ctx["match"] = st.tagged_example(ctx["api"], "ivy", "Saturday doubles")
    ctx["keys"] = st.object_keys_of(ctx["db"], ctx["match"])
    ctx["rows"] = st.rows_holding(ctx["db"], [ctx["match"]])
    ctx["sheet"] = sb.sheet_body(ctx["api"], "ivy", ctx["match"])
    assert ctx["keys"], "positive control: the match has stored objects"


@when("she deletes the match and confirms the stated consequences")
def deletes(ctx: dict[str, Any]) -> None:
    ctx["at"] = time.monotonic()
    response = st.delete_match(ctx["api"], "ivy", ctx["match"])
    assert response.status_code in st.statscontract.DELETE_OK, response.text


@then("within 1 minute the match no longer appears anywhere in her account")
def hidden_within_a_minute(ctx: dict[str, Any]) -> None:
    while not _gone(ctx):
        assert time.monotonic() - ctx["at"] < 60, "still visible after 60 s (NFR-066 a)"
        time.sleep(0.5)


@then("after the clean-up runs no stored file or record of the match remains")
def nothing_remains(ctx: dict[str, Any]) -> None:
    st.run_purge_once()
    left = {k: n for k, n in st.rows_holding(ctx["db"], [ctx["match"]]).items() if n}
    assert left == {}
    assert st.keys_still_stored(ctx["keys"]) == []


@when("he tries to delete it")
def carlos_deletes(ctx: dict[str, Any]) -> None:
    ctx["response"] = st.delete_match(ctx["api"], "carlos", ctx["match"])


@then("he is told it does not exist")
def does_not_exist(ctx: dict[str, Any]) -> None:
    assert ctx["response"].status_code == 404
    method, url = st.statscontract.path(
        "delete_match", match_id="00000000-0000-4000-8000-000000000000"
    )
    absent = ctx["api"].request("carlos", method, url, json=st.statscontract.CONFIRM_BODY)
    assert ctx["response"].json()["error"]["code"] == absent.json()["error"]["code"]


@then("Ivy's match is unchanged")
def unchanged(ctx: dict[str, Any]) -> None:
    assert st.rows_holding(ctx["db"], [ctx["match"]]) == ctx["rows"]
    assert sb.sheet_body(ctx["api"], "ivy", ctx["match"]) == ctx["sheet"]
    assert st.keys_still_stored(ctx["keys"]) == ctx["keys"]
