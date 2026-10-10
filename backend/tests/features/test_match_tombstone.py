"""API binding of tests/features/match_tombstone.feature (ST-050a; FR-006, NFR-066 a;
api-sprint-03 §4.1; ADR 0042). Hidden at once: the 202 states ``purge_due_by`` within 7 days,
then every read of the match answers 404 and the list omits it. The purge itself is ST-050b
(match_deletion.feature, "after the clean-up runs ...")."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pytest_bdd import given, scenario, then, when

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

FEATURE = "match_tombstone.feature"


@scenario(FEATURE, "Deleting without the typed confirmation deletes nothing")
def test_deleting_without_the_typed_confirmation_deletes_nothing() -> None:
    pass


@scenario(FEATURE, "A deleted match is gone from her account at once")
def test_a_deleted_match_is_gone_from_her_account_at_once() -> None:
    pass


@pytest.fixture
def ctx(api: ApiDriver, committed_db: Any) -> dict[str, Any]:
    return {"api": api, "db": committed_db}


def _listed(ctx: dict[str, Any]) -> bool:
    body = st.request(ctx["api"], "ivy", "matches").json()
    items = body["items"] if isinstance(body, dict) else body
    return any(item["id"] == ctx["match"] for item in items)


@given("Ivy has a tagged match with stats")
def tagged_match(ctx: dict[str, Any]) -> None:
    ctx["match"] = st.tagged_example(ctx["api"], "ivy", "Saturday doubles")
    ctx["sheet"] = sb.sheet_body(ctx["api"], "ivy", ctx["match"])
    ctx["version"] = ctx["api"].run(sb.version_of(ctx["api"].as_user("ivy"), ctx["match"]))


@when("she deletes the match without typing the confirmation")
def deletes_unconfirmed(ctx: dict[str, Any]) -> None:
    ctx["response"] = st.delete_match(ctx["api"], "ivy", ctx["match"], body={})


@then("she is asked to confirm")
def asked_to_confirm(ctx: dict[str, Any]) -> None:
    assert st.refusal(ctx["response"]) == st.CONFIRMATION_REQUIRED, ctx["response"].text


@then("her match is still in her list with its score sheet")
def still_there(ctx: dict[str, Any]) -> None:
    assert _listed(ctx)
    assert sb.sheet_body(ctx["api"], "ivy", ctx["match"]) == ctx["sheet"]


@when("she deletes the match and confirms the stated consequences")
def deletes(ctx: dict[str, Any]) -> None:
    ctx["at"] = datetime.now(UTC)
    ctx["response"] = st.delete_match(ctx["api"], "ivy", ctx["match"])


@then("she is told when it will be purged, within 7 days")
def purge_due(ctx: dict[str, Any]) -> None:
    response = ctx["response"]
    assert response.status_code == 202, response.text
    due = datetime.fromisoformat(response.json()["purge_due_by"].replace("Z", "+00:00"))
    assert ctx["at"] + timedelta(days=7) - timedelta(seconds=2) <= due
    assert due <= datetime.now(UTC) + timedelta(days=7)


@then("the match, its stats, its evidence, its score sheet and its video are not found")
def reads_404(ctx: dict[str, Any]) -> None:
    match_id = ctx["match"]
    reads = [
        st.statscontract.path("match", match_id=match_id),
        st.statscontract.path("stats", match_id=match_id),
        st.statscontract.path("evidence", match_id=match_id, metric_id="AN-01", side="A"),
        sb.path("sheet", match_id=match_id),
        sb.path("video", match_id=match_id),
    ]
    for method, url in reads:
        got = ctx["api"].request("ivy", method, url)
        assert got.status_code == 404, f"{method} {url}: {got.status_code}"


@then("her list no longer shows the match")
def not_listed(ctx: dict[str, Any]) -> None:
    assert not _listed(ctx)


@then("tagging a rally of it is refused as not found")
def tag_refused(ctx: dict[str, Any]) -> None:
    client = ctx["api"].as_user("ivy")
    tag = dict(st.WORKED_EXAMPLE[0])
    response = ctx["api"].run(
        sb.command(client, "tag", version=ctx["version"], body=tag, match_id=ctx["match"])
    )
    assert response.status_code == 404, response.text
