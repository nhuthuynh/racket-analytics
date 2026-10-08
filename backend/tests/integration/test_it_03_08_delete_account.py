"""IT-03-08 (ST-051; FR-007, NFR-066 b, NFR-057): API <-> DB, delete my account.

Ivy is signed in on two devices (two sessions) and has three matches. A DELETE without the
typed confirmation deletes nothing. With it: both sessions answer 401 at once; after one purge
pass no row in any table holds her account id or a match id, and no object of her matches is
stored. Signing in again with the same address gives a new, empty account (PM-1 default,
sprint-03 §3.4 ST-051; a different PM-1 decision is a TCR row). Carlos's data is untouched.

Written red first (QA-ACC-3): ``red_until`` ST-051.

Marker ``red_until`` ST-051 removed (VR2-S3-01, TCR row 2026-10-07): the story is built and
every row passes, so the file is in the per-PR gate and the coverage selection.
"""

from __future__ import annotations

from typing import Any

import httpx

from tests.support import stats as st
from tests.support.api import BASE_URL, ApiDriver, sign_in


def _second_device(api: ApiDriver, username: str) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=api.app, raise_app_exceptions=False)
    client = httpx.AsyncClient(transport=transport, base_url=BASE_URL)
    api.run(sign_in(client, username))
    return client


def _me(api: ApiDriver, client: httpx.AsyncClient) -> httpx.Response:
    method, url = st.statscontract.path("me")
    return api.run(client.request(method, url))


def test_it_03_08_no_typed_confirmation_deletes_nothing(api: ApiDriver, committed_db: Any) -> None:
    match_id = st.tagged_example(api, "ivy", "IT-03-08 confirm")
    me = st.me_id(api, "ivy")
    before = st.rows_holding(committed_db, [me, match_id])
    response = st.delete_account(api, "ivy", body={})
    # api-sprint-03 §4.2: exactly 422 confirmation_required; a missing route (404/405) is not it.
    assert st.refusal(response) == st.CONFIRMATION_REQUIRED, response.text
    assert st.rows_holding(committed_db, [me, match_id]) == before
    assert st.request(api, "ivy", "me").status_code == 200


def test_it_03_08_both_sessions_end_and_the_purge_leaves_nothing(
    api: ApiDriver, committed_db: Any
) -> None:
    matches = [st.tagged_example(api, "ivy", f"IT-03-08 {i}") for i in range(3)]
    carlos_match = st.tagged_example(api, "carlos", "IT-03-08 carlos")
    carlos_rows = st.rows_holding(committed_db, [carlos_match])
    old_id = st.me_id(api, "ivy")
    laptop = _second_device(api, "ivy")
    try:
        assert _me(api, laptop).json()["id"] == old_id
        keys = [k for m in matches for k in st.object_keys_of(committed_db, m)]
        assert keys

        response = st.delete_account(api, "ivy")
        assert response.status_code in st.statscontract.DELETE_OK, response.text
        assert st.request(api, "ivy", "me").status_code == 401  # this phone
        assert _me(api, laptop).status_code == 401  # the laptop too

        st.run_purge_once()
        left = {k: n for k, n in st.rows_holding(committed_db, [old_id, *matches]).items() if n}
        assert left == {}, f"rows still hold the account or its matches: {left}"
        assert st.keys_still_stored(keys) == []
        assert st.rows_holding(committed_db, [carlos_match]) == carlos_rows

        api.run(sign_in(laptop, "ivy"))
        again = _me(api, laptop)
        assert again.status_code == 200
        assert again.json()["id"] != old_id
        method, url = st.statscontract.path("matches")
        listed = api.run(laptop.request(method, url)).json()
        assert (listed["items"] if isinstance(listed, dict) else listed) == []
    finally:
        api.run(laptop.aclose())
