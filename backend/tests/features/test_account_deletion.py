"""API binding of tests/features/account_deletion.feature (QA-ACC-3 for ST-051; FR-007,
NFR-066). Two devices are two signed-in clients of the same dev user. The re-sign-in rule is
the PM-1 default (a new, empty account). Written red first: ``red_until`` ST-051.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from pytest_bdd import given, scenarios, then, when

from tests.support import stats as st
from tests.support.api import BASE_URL, ApiDriver, sign_in

pytestmark = [pytest.mark.red_until(story="ST-051")]

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
