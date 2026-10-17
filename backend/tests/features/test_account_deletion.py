"""API binding of tests/features/account_deletion.feature (QA-ACC-3 for ST-051; FR-007,
NFR-066). Two devices are two signed-in clients of the same dev user. The re-sign-in rule is
the PM-1 default (a new, empty account). Written red first: ``red_until`` ST-051.

ST-051-API (TCR row in docs/sprints/03/decisions/ST-051-API.md): the module marker is lifted;
``DELETE /me`` is built and both scenarios join the per-PR gate.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from pytest_bdd import given, scenarios, then, when

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import BASE_URL, ApiDriver, sign_in

scenarios("account_deletion.feature")


@pytest.fixture
def ctx(api: ApiDriver, committed_db: Any) -> Iterator[dict[str, Any]]:
    transport = httpx.ASGITransport(app=api.app, raise_app_exceptions=False)
    laptop = httpx.AsyncClient(transport=transport, base_url=BASE_URL)
    yield {"api": api, "db": committed_db, "laptop": laptop}
    api.run(laptop.aclose())


def _laptop(ctx: dict[str, Any], name: str) -> httpx.Response:
    method, url = st.statscontract.path(name)
    response: httpx.Response = ctx["api"].run(ctx["laptop"].request(method, url))
    return response


@given("Ivy has 3 matches and is signed in on her phone and her laptop")
def three_matches_two_devices(ctx: dict[str, Any]) -> None:
    api = ctx["api"]
    ctx["matches"] = [st.tagged_example(api, "ivy", f"Match {i}") for i in range(3)]
    ctx["keys"] = [k for m in ctx["matches"] for k in st.object_keys_of(ctx["db"], m)]
    ctx["id"] = st.me_id(api, "ivy")
    api.run(sign_in(ctx["laptop"], "ivy"))
    assert _laptop(ctx, "me").json()["id"] == ctx["id"]


@given("Ivy deleted her account")
def deleted_account(ctx: dict[str, Any]) -> None:
    three_matches_two_devices(ctx)
    deletes_account(ctx)


@when("she deletes her account and confirms")
def deletes_account(ctx: dict[str, Any]) -> None:
    response = st.delete_account(ctx["api"], "ivy")
    assert response.status_code in st.statscontract.DELETE_OK, response.text


@then("she is signed out on both devices")
def signed_out(ctx: dict[str, Any]) -> None:
    assert st.request(ctx["api"], "ivy", "me").status_code == 401
    assert _laptop(ctx, "me").status_code == 401


@then("after the clean-up runs none of her matches or her profile remain stored")
def nothing_stored(ctx: dict[str, Any]) -> None:
    st.run_purge_once()
    ids = [ctx["id"], *ctx["matches"]]
    assert {k: n for k, n in st.rows_holding(ctx["db"], ids).items() if n} == {}
    assert st.keys_still_stored(ctx["keys"]) == []


@when("she signs in again with the same address")
def signs_in_again(ctx: dict[str, Any]) -> None:
    ctx["api"].run(sign_in(ctx["laptop"], "ivy"))
    assert _laptop(ctx, "me").json()["id"] != ctx["id"]


@then("she sees no matches")
def no_matches(ctx: dict[str, Any]) -> None:
    body = _laptop(ctx, "matches").json()
    assert (body["items"] if isinstance(body, dict) else body) == []


# ------------------------------------------------------------------ C4-TAC5 (T-AC-5)
def _labelling_match(ctx: dict[str, Any], title: str) -> str:
    api = ctx["api"]
    client = api.as_user("ivy")
    match_id: str = api.run(sb.create_doubles(client, title))
    api.run(sb.receive_video(client, match_id))
    st.probe_videos()
    st.record_consent(match_id)
    return match_id


@given("Ivy was a labeller and deleted her account")
def deleted_labeller(ctx: dict[str, Any]) -> None:
    api = ctx["api"]
    st.grant_labeller(api, "ivy")
    ctx["id"] = st.me_id(api, "ivy")
    own = _labelling_match(ctx, "Labelled match")
    opened = st.fulltag(api, "ivy", "label_match", match_id=own)
    assert opened.status_code == 200, f"positive control: {opened.status_code} {opened.text}"
    deletes_account(ctx)


@then("the Full Tag tool is not there for her, even on her own consented match")
def no_full_tag(ctx: dict[str, Any]) -> None:
    api = ctx["api"]
    api.run(sign_in(api.as_user("ivy"), "ivy"))  # the driver's phone client follows her
    mine = _labelling_match(ctx, "After re-sign-in")
    for route in sorted(st.FULLTAG_ROUTES):
        body = {"type": "hit", "frame": 1840, "hitter": "B1"} if route == "label_events" else None
        answer = st.fulltag(api, "ivy", route, json_body=body, match_id=mine)
        assert st.refusal(answer)[:2] == (404, "not_found"), f"{route}: {answer.text}"
