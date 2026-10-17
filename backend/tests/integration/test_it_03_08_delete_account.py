"""IT-03-08 (ST-051; FR-007, NFR-066 b, NFR-057): API <-> DB, delete my account.

Ivy is signed in on two devices (two sessions) and has three matches. A DELETE without the
typed confirmation deletes nothing. With it: both sessions answer 401 at once; after one purge
pass no row in any table holds her account id or a match id, and no object of her matches is
stored. Signing in again with the same address gives a new, empty account (PM-1 default,
sprint-03 §3.4 ST-051; a different PM-1 decision is a TCR row). Carlos's data is untouched.

Written red first (QA-ACC-3): ``red_until`` ST-051.

ST-051-API (TCR row in docs/sprints/03/decisions/ST-051-API.md): the module marker is lifted;
``DELETE /me`` is built and both rows join the per-PR gate.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import sqlalchemy as sa

from tests.support import scorebook as sb
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


# ------------------------------------------------------------------ IT-04-12 (C4-TAC5, T-AC-5)
def _consented_labelling_match(api: ApiDriver, user: str, title: str) -> str:
    """A match of ``user`` the label routes can open: video received and probed, consent kept."""
    client = api.as_user(user)
    match_id = api.run(sb.create_doubles(client, title))
    api.run(sb.receive_video(client, match_id))
    st.probe_videos()  # an unprobed video is 409 match_not_ready (api-sprint-03 §5.1)
    st.record_consent(match_id)
    return match_id


def _roles_of(engine: Any, account_id: str) -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT role FROM account_roles WHERE account_id = :id ORDER BY role"),
            {"id": account_id},
        )
        return [str(r) for r in rows.scalars()]


def _label_answers(api: ApiDriver, user: str, match_id: str) -> dict[str, Any]:
    """The refusal of every label route (``label_events`` with a valid hit body)."""
    hit = {"type": "hit", "frame": 1840, "hitter": "B1"}
    return {
        route: st.refusal(
            st.fulltag(api, user, route, json_body=hit if route == "label_events" else None,
                       match_id=match_id)
        )
        for route in sorted(st.FULLTAG_ROUTES)
    }  # fmt: skip


def test_it_04_12_a_re_created_account_has_no_labeller_role(
    api: ApiDriver, committed_db: Any
) -> None:
    """T-AC-5 (SEC-S3-TM-07; ADR 0045; threat-model-sprint-03 T-AC-5): Ivy holds the labeller
    role, deletes her account and signs in again with the same address *before* the purge has
    run, so her tombstone still holds the role row. The new account holds no role: every label
    route answers her own consented, probed match exactly as an unknown match: 404
    ``not_found`` (SEC-S3-TM-08, the tool is not revealed; the ticket's "403" is this refusal,
    threat-model-sprint-03 T-AC-5 says 404). The same holds after the purge, which leaves no
    role row of the old account.

    Positive control first: before the deletion the same kind of match opens (200), so a 404
    later is the missing role, not a missing route or an unready match."""
    st.grant_labeller(api, "ivy")
    old_id = st.me_id(api, "ivy")
    before = _consented_labelling_match(api, "ivy", "IT-04-12 labeller")
    control = st.fulltag(api, "ivy", "label_match", match_id=before)
    assert control.status_code == 200, f"positive control: {control.status_code} {control.text}"
    assert _roles_of(committed_db, old_id) == ["labeller"]

    response = st.delete_account(api, "ivy")
    assert response.status_code in st.statscontract.DELETE_OK, response.text
    assert _roles_of(committed_db, old_id) == ["labeller"], "the tombstone keeps it until purge"

    api.run(sign_in(api.as_user("ivy"), "ivy"))  # the same address, before the purge
    new_id = st.me_id(api, "ivy")
    assert new_id != old_id
    assert _roles_of(committed_db, new_id) == [], "the role was carried to the new account"
    mine = _consented_labelling_match(api, "ivy", "IT-04-12 re-created")
    unknown = _label_answers(api, "ivy", str(uuid.uuid4()))
    not_found = dict.fromkeys(st.FULLTAG_ROUTES, (404, "not_found"))
    assert {r: a[:2] for r, a in unknown.items()} == not_found
    assert _label_answers(api, "ivy", mine) == unknown, "a re-created account opened Full Tag"

    st.run_purge_once()
    assert _roles_of(committed_db, old_id) == []
    assert _roles_of(committed_db, new_id) == []
    assert _label_answers(api, "ivy", mine) == unknown, "after the purge the tool appeared"
