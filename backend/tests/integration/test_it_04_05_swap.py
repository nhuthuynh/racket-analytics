"""IT-04-05 (ST-062; FR-124; api-sprint-04 §3.3, §8): "Not for me" swaps one drill assignment,
over HTTP on Postgres and the real drill library (``content/drills``).

Negative cases first: a bad body (422 with its field code), another account's or an unknown
assignment (404, the same body), a done session (409 ``session_done``) and no alternative (409
``no_alternative``), each leaving the plan unchanged. Then the swap: the assignment keeps its id,
gets another reviewed drill citing the same metric, the plan keeps QD-PL-01..03 (QA's
independent grader ``scripts/measure/planlib.py``), the version goes up by one, the reason is
stored and never echoed, and a swapped-out drill is never offered again in that plan.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import pytest
import sqlalchemy as sa

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver
from tests.support.paths import REPO

pytestmark = [pytest.mark.integration, pytest.mark.coaching]

planlib = sb._load("planlib")
PLAN = "/me/plan"
SOLO_WALL = {
    "minutes_per_session": 30,
    "sessions_per_week": 3,
    "players_available": 1,
    "equipment": ["wall"],
    "level": "intermediate",
}
SWAPS_MAX = 40
REASON = "My wrist hurts after this one"


def _plan(api: ApiDriver, user: str) -> dict[str, Any]:
    st.tagged_example(api, user, f"IT-04-05 {user}")
    response = api.request(user, "POST", PLAN, json=SOLO_WALL)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def _read(api: ApiDriver, user: str) -> dict[str, Any]:
    response = api.request(user, "GET", PLAN)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _swap(api: ApiDriver, user: str, assignment_id: str, body: Any = None) -> httpx.Response:
    url = f"{PLAN}/assignments/{assignment_id}/swap"
    return api.request(user, "POST", url, json={} if body is None else body)


def _ref(assignment: dict[str, Any]) -> str:
    return f"{assignment['drill']['id']}@{assignment['drill']['version']}"


def _no_ref(response: httpx.Response) -> tuple[int, Any]:
    body = response.json()
    body["error"].pop("support_ref", None)
    return response.status_code, body


def _reasons(engine: Any) -> list[str | None]:
    with engine.connect() as conn:
        rows = conn.execute(sa.text("SELECT reason_not_for_me FROM plan_assignments")).scalars()
        return sorted(rows, key=lambda r: (r is None, r or ""))


def _swap_until_refused(api: ApiDriver, assignment_id: str) -> list[str]:
    offered = []
    for _ in range(SWAPS_MAX):
        response = _swap(api, "ivy", assignment_id)
        if response.status_code == 409:
            assert st.refusal(response)[:2] == (409, "no_alternative"), response.text
            return offered
        assert response.status_code == 200, response.text
        session = response.json()["session"]
        offered.append(_ref(next(a for a in session["assignments"] if a["id"] == assignment_id)))
    pytest.fail(f"no 409 no_alternative after {SWAPS_MAX} swaps")


# ------------------------------------------------------------------ refusals (negative first)
@pytest.mark.parametrize(
    ("body", "fields"),
    [
        ({"reason": "x" * 201}, [("reason", "too_long")]),
        ({"reason": "   "}, [("reason", "invalid")]),
        ({"reason": 7}, [("reason", "invalid")]),
        ({"reason": "ok", "drill": "pb.serve.deep-target"}, [(None, "unknown_field")]),
        (["not", "an", "object"], [(None, "invalid")]),
    ],
)
def test_it_04_05_a_bad_body_is_422_and_changes_nothing(
    api: ApiDriver, committed_db: Any, body: Any, fields: list[tuple[Any, str]]
) -> None:
    plan = _plan(api, "ivy")
    response = _swap(api, "ivy", plan["sessions"][0]["assignments"][1]["id"], body)
    assert st.refusal(response) == (422, "validation_failed", fields)
    assert "x" * 201 not in response.text
    assert _read(api, "ivy") == plan


def test_it_04_05_another_accounts_assignment_is_the_404_of_an_unknown_one(
    api: ApiDriver, committed_db: Any
) -> None:
    ivy, _ = _plan(api, "ivy"), _plan(api, "carlos")
    own = ivy["sessions"][0]["assignments"][1]["id"]
    attacker = _swap(api, "carlos", own, {"reason": REASON})
    unknown = _swap(api, "carlos", str(uuid.uuid4()), {"reason": REASON})
    malformed = _swap(api, "carlos", "not-a-uuid", {"reason": REASON})
    session_id = _swap(api, "carlos", ivy["sessions"][0]["id"])  # a session id is not one
    assert attacker.status_code == 404, attacker.text
    assert _no_ref(attacker) == _no_ref(unknown) == _no_ref(malformed) == _no_ref(session_id)
    assert _read(api, "ivy") == ivy
    assert _reasons(committed_db) == [None] * len(_reasons(committed_db))


def test_it_04_05_a_drill_of_a_done_session_is_409_session_done(
    api: ApiDriver, committed_db: Any
) -> None:
    plan = _plan(api, "ivy")
    session = plan["sessions"][0]
    done = api.request(
        "ivy", "POST", f"{PLAN}/sessions/{session['id']}/done", headers={"Idempotency-Key": "op-1"}
    )
    assert done.status_code == 200, done.text
    before = _read(api, "ivy")
    response = _swap(api, "ivy", session["assignments"][1]["id"], {"reason": REASON})
    assert st.refusal(response)[:2] == (409, "session_done"), response.text
    assert response.json()["error"]["message"] == "This session is already done."
    assert _read(api, "ivy") == before
    assert REASON not in _reasons(committed_db)


def test_it_04_05_no_alternative_is_409_and_leaves_the_plan_unchanged(
    api: ApiDriver, committed_db: Any
) -> None:
    plan = _plan(api, "ivy")
    assignment = plan["sessions"][0]["assignments"][1]
    offered = _swap_until_refused(api, assignment["id"])
    before = _read(api, "ivy")
    assert before["version"] == plan["version"] + len(offered)
    response = _swap(api, "ivy", assignment["id"], {"reason": REASON})
    assert st.refusal(response)[:2] == (409, "no_alternative"), response.text
    assert response.json()["error"]["message"] == "No other drill fits your settings for this."
    assert REASON not in response.text
    assert _read(api, "ivy") == before
    assert REASON not in _reasons(committed_db)


# ------------------------------------------------------------------ the swap
def test_it_04_05_swap_gives_another_reviewed_drill_for_the_same_metric(
    api: ApiDriver, committed_db: Any, caplog: pytest.LogCaptureFixture
) -> None:
    plan = _plan(api, "ivy")
    library = planlib.load_library(REPO / "content" / "drills")
    old_session = plan["sessions"][0]
    old = old_session["assignments"][1]
    response = _swap(api, "ivy", old["id"], {"reason": f"  {REASON} "})
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"plan_version", "session"}
    assert body["plan_version"] == plan["version"] + 1
    session = body["session"]
    assert set(session) == set(old_session)
    assert (session["id"], session["week"], session["index"]) == (
        old_session["id"],
        old_session["week"],
        old_session["index"],
    )
    new = session["assignments"][1]
    assert (new["id"], new["position"], new["weakness_id"]) == (
        old["id"],
        old["position"],
        old["weakness_id"],
    )
    assert _ref(new) != _ref(old)
    assert library[_ref(new)]["review_status"] in ("coach-reviewed", "verified")
    assert new["citation"]["metric_id"] == old["citation"]["metric_id"]
    assert new["citation"]["metric_id"] in library[_ref(new)]["target_metrics"]
    assert new["why"]
    assert [a["id"] for a in session["assignments"]] == [a["id"] for a in old_session["assignments"]]
    assert session["assignments"][0] == old_session["assignments"][0]
    assert session["assignments"][2:] == old_session["assignments"][2:]
    assert REASON not in response.text

    read = _read(api, "ivy")
    assert read["version"] == body["plan_version"]
    assert read["sessions"][0] == session
    assert read["sessions"][1:] == plan["sessions"][1:]
    assert planlib.grade(read, library) == []
    assert _reasons(committed_db)[0] == REASON  # stored trimmed
    assert REASON not in caplog.text  # never logged


def test_it_04_05_a_swapped_out_drill_is_never_offered_again_in_that_plan(
    api: ApiDriver, committed_db: Any
) -> None:
    plan = _plan(api, "ivy")
    library = planlib.load_library(REPO / "content" / "drills")
    assignment = plan["sessions"][0]["assignments"][1]
    offered = _swap_until_refused(api, assignment["id"])
    assert offered, "the solo-wall plan's second drill has no alternative in the library"
    history = [_ref(assignment), *offered]
    assert len(set(history)) == len(history), history
    read = _read(api, "ivy")
    assert planlib.grade(read, library) == []
    metric = assignment["citation"]["metric_id"]
    assert read["sessions"][0]["assignments"][1]["citation"]["metric_id"] == metric
    # a new plan starts with nothing excluded
    again = api.request("ivy", "POST", PLAN, json=SOLO_WALL)
    assert again.status_code == 201, again.text
    first = _swap(api, "ivy", again.json()["sessions"][0]["assignments"][1]["id"])
    assert first.status_code == 200, first.text


def test_it_04_05_a_warm_up_is_swapped_only_for_another_warm_up(
    api: ApiDriver, committed_db: Any
) -> None:
    plan = _plan(api, "ivy")
    library = planlib.load_library(REPO / "content" / "drills")
    warm = plan["sessions"][0]["assignments"][0]
    response = _swap(api, "ivy", warm["id"])
    if response.status_code == 409:
        assert st.refusal(response)[:2] == (409, "no_alternative")
        assert _read(api, "ivy") == plan
        return
    assert response.status_code == 200, response.text
    new = response.json()["session"]["assignments"][0]
    assert (new["id"], new["warm_up"], new["weakness_id"]) == (warm["id"], True, None)
    assert "warm-up" in library[_ref(new)]["skills"]
    assert new["citation"]["metric_id"] == warm["citation"]["metric_id"]
    assert planlib.grade(_read(api, "ivy"), library) == []
