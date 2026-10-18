"""IT-04-04 (ST-062; FR-124; api-sprint-04 §3.1, §3.2, §8): mark a session done, idempotent by
the client's op id (``Idempotency-Key``), and undo it, over HTTP on Postgres.

Negative cases first: a missing or malformed key (422), another account's or an unknown session
(404, the same body), the same key for another session (409 ``idempotency_key_reused``) and a
session of a replaced plan (404). Then: done once, a replay returns the stored result without
bumping the version, a new key on a done session is a no-op, undo, undo when not done, and the
op rows (one per mark, none for a no-op, per account, gone with the plan).
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import pytest
import sqlalchemy as sa

from tests.support import stats as st
from tests.support.api import ApiDriver

pytestmark = [pytest.mark.integration, pytest.mark.coaching]

PLAN = "/me/plan"
SOLO_WALL = {
    "minutes_per_session": 30,
    "sessions_per_week": 3,
    "players_available": 1,
    "equipment": ["wall"],
    "level": "intermediate",
}


def _plan(api: ApiDriver, user: str) -> dict[str, Any]:
    st.tagged_example(api, user, f"IT-04-04 {user}")
    response = api.request(user, "POST", PLAN, json=SOLO_WALL)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def _read(api: ApiDriver, user: str) -> dict[str, Any]:
    response = api.request(user, "GET", PLAN)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _done(api: ApiDriver, user: str, session_id: str, key: str | None) -> httpx.Response:
    headers = {} if key is None else {"Idempotency-Key": key}
    return api.request(user, "POST", f"{PLAN}/sessions/{session_id}/done", headers=headers)


def _undo(api: ApiDriver, user: str, session_id: str) -> httpx.Response:
    return api.request(user, "DELETE", f"{PLAN}/sessions/{session_id}/done")


def _ops(engine: Any) -> list[tuple[str, str, int]]:
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT op_id, session_id, plan_version FROM plan_done_ops ORDER BY op_id")
        ).all()
    return [(r.op_id, str(r.session_id), r.plan_version) for r in rows]


def _no_ref(response: httpx.Response) -> tuple[int, Any]:
    body = response.json()
    body["error"].pop("support_ref", None)
    return response.status_code, body


# ------------------------------------------------------------------ refusals (negative first)
@pytest.mark.parametrize(
    ("key", "code"),
    [(None, "required"), ("", "required"), ("bad key!", "invalid"), ("x" * 65, "invalid")],
)
def test_it_04_04_a_missing_or_malformed_op_id_is_422_and_changes_nothing(
    api: ApiDriver, committed_db: Any, key: str | None, code: str
) -> None:
    plan = _plan(api, "ivy")
    response = _done(api, "ivy", plan["sessions"][0]["id"], key)
    assert st.refusal(response) == (422, "validation_failed", [("Idempotency-Key", code)])
    assert _read(api, "ivy") == plan
    assert _ops(committed_db) == []


def test_it_04_04_another_accounts_session_is_the_404_of_an_unknown_one(
    api: ApiDriver, committed_db: Any
) -> None:
    ivy, _ = _plan(api, "ivy"), _plan(api, "carlos")
    own = ivy["sessions"][0]["id"]
    attacker = _done(api, "carlos", own, "op-carlos-1")
    unknown = _done(api, "carlos", str(uuid.uuid4()), "op-carlos-2")
    malformed = _done(api, "carlos", "not-a-uuid", "op-carlos-3")
    undo = _undo(api, "carlos", own)
    assert attacker.status_code == 404, attacker.text
    assert _no_ref(attacker) == _no_ref(unknown) == _no_ref(malformed) == _no_ref(undo)
    assert _read(api, "ivy") == ivy
    assert _ops(committed_db) == []


def test_it_04_04_the_same_op_id_for_another_session_is_409_reused(
    api: ApiDriver, committed_db: Any
) -> None:
    plan = _plan(api, "ivy")
    first, second = plan["sessions"][0]["id"], plan["sessions"][1]["id"]
    assert _done(api, "ivy", first, "op-1").status_code == 200
    before = _read(api, "ivy")
    response = _done(api, "ivy", second, "op-1")
    assert st.refusal(response)[:2] == (409, "idempotency_key_reused"), response.text
    assert response.json()["error"]["message"] == "This request id was already used."
    assert _read(api, "ivy") == before
    assert _ops(committed_db) == [("op-1", first, plan["version"] + 1)]


def test_it_04_04_an_op_for_a_session_of_a_replaced_plan_is_404(
    api: ApiDriver, committed_db: Any
) -> None:
    old = _plan(api, "ivy")
    session_id = old["sessions"][0]["id"]
    assert _done(api, "ivy", session_id, "op-old").status_code == 200
    replaced = api.request("ivy", "POST", PLAN, json=SOLO_WALL)
    assert replaced.status_code == 201, replaced.text
    assert _ops(committed_db) == []  # the op rows went with the old plan
    replay = _done(api, "ivy", session_id, "op-old")
    assert st.refusal(replay)[:2] == (404, "not_found"), replay.text
    assert st.refusal(_undo(api, "ivy", session_id))[:2] == (404, "not_found")
    assert [s["done"] for s in _read(api, "ivy")["sessions"]] == [False] * 6


# ------------------------------------------------------------------ done once, replay, undo
def test_it_04_04_done_marks_once_and_a_replay_returns_the_stored_result(
    api: ApiDriver, committed_db: Any
) -> None:
    plan = _plan(api, "ivy")
    session_id = plan["sessions"][2]["id"]
    first = _done(api, "ivy", session_id, "3f0c1d2e-9a7b-4c1d-8e2f-0a1b2c3d4e5f")
    assert first.status_code == 200, first.text
    body = first.json()
    assert set(body) == {"session_id", "done", "done_at", "plan_version", "replayed"}
    assert (body["session_id"], body["done"], body["replayed"]) == (session_id, True, False)
    assert body["plan_version"] == plan["version"] + 1
    assert body["done_at"].endswith("Z")

    replay = _done(api, "ivy", session_id, "3f0c1d2e-9a7b-4c1d-8e2f-0a1b2c3d4e5f")
    assert replay.status_code == 200, replay.text
    assert replay.json() == body | {"replayed": True}

    read = _read(api, "ivy")
    assert read["version"] == body["plan_version"]
    assert [s["done"] for s in read["sessions"]] == [False, False, True, False, False, False]
    assert read["sessions"][2]["done_at"] == body["done_at"]
    assert read["content_digest"] == plan["content_digest"]  # done state is not plan content
    assert _ops(committed_db) == [
        ("3f0c1d2e-9a7b-4c1d-8e2f-0a1b2c3d4e5f", session_id, body["plan_version"])
    ]


def test_it_04_04_a_new_op_id_on_a_done_session_is_a_no_op(
    api: ApiDriver, committed_db: Any
) -> None:
    plan = _plan(api, "ivy")
    session_id = plan["sessions"][0]["id"]
    first = _done(api, "ivy", session_id, "op-a").json()
    again = _done(api, "ivy", session_id, "op-b")
    assert again.status_code == 200, again.text
    assert again.json() == first  # same done_at and version, not a replay of op-a
    assert _read(api, "ivy")["version"] == plan["version"] + 1
    # T4-PL-5: the no-op stores no record, so a client looping new keys grows nothing
    assert _ops(committed_db) == [("op-a", session_id, plan["version"] + 1)]
    assert _done(api, "ivy", session_id, "op-b").json() == first
    assert _ops(committed_db) == [("op-a", session_id, plan["version"] + 1)]


def test_it_04_04_an_op_id_is_scoped_to_the_account(api: ApiDriver, committed_db: Any) -> None:
    """T4-PL-3 / SEC-S4-TM-02: Ivy's key is just a new key for Carlos, never her result."""
    ivy, carlos = _plan(api, "ivy"), _plan(api, "carlos")
    hers, his = ivy["sessions"][0]["id"], carlos["sessions"][0]["id"]
    assert _done(api, "ivy", hers, "op-shared").status_code == 200
    on_hers = _done(api, "carlos", hers, "op-shared")
    unknown = _done(api, "carlos", str(uuid.uuid4()), "op-shared")
    assert on_hers.status_code == 404, on_hers.text
    assert _no_ref(on_hers) == _no_ref(unknown)
    on_his = _done(api, "carlos", his, "op-shared")
    assert on_his.status_code == 200, on_his.text
    body = on_his.json()
    assert (body["session_id"], body["done"], body["replayed"]) == (his, True, False)
    assert body["plan_version"] == carlos["version"] + 1
    assert sorted(_ops(committed_db)) == sorted(
        [("op-shared", hers, ivy["version"] + 1), ("op-shared", his, carlos["version"] + 1)]
    )


def test_it_04_04_undo_clears_done_and_undo_when_not_done_is_a_no_op(
    api: ApiDriver, committed_db: Any
) -> None:
    plan = _plan(api, "ivy")
    session_id = plan["sessions"][1]["id"]
    not_done = _undo(api, "ivy", session_id)
    assert not_done.status_code == 200, not_done.text
    assert not_done.json() == {
        "session_id": session_id,
        "done": False,
        "done_at": None,
        "plan_version": plan["version"],
    }
    assert _done(api, "ivy", session_id, "op-1").status_code == 200
    undone = _undo(api, "ivy", session_id)
    assert undone.status_code == 200, undone.text
    assert undone.json() == {
        "session_id": session_id,
        "done": False,
        "done_at": None,
        "plan_version": plan["version"] + 2,
    }
    read = _read(api, "ivy")
    assert (read["version"], read["sessions"][1]["done"]) == (plan["version"] + 2, False)
    # an offline replay after the undo returns the stored result and changes nothing
    replay = _done(api, "ivy", session_id, "op-1")
    assert (replay.json()["replayed"], replay.json()["plan_version"]) == (True, plan["version"] + 1)
    assert _read(api, "ivy") == read


def test_it_04_04_the_routes_are_in_the_openapi_document(api: ApiDriver) -> None:
    paths = api.app.openapi()["paths"]
    assert {"post", "delete"} <= set(paths["/me/plan/sessions/{session_id}/done"])
    assert "post" in paths["/me/plan/assignments/{assignment_id}/swap"]
