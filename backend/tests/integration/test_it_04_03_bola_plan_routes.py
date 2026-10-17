"""IT-04-03 (ST-061b; NFR-051; api-sprint-04 §8; SEC-4 T4-PL-1): the plan's session and
assignment ids are owned resources. Carlos, who has a plan of his own, probes every plan id route
(``tests.regression.bola.PLAN_ID_ROUTES_04``) with Ivy's real ids and gets exactly the 404 of an
unknown or malformed id. A served route (``SERVED_04``, ST-062) also gets the owner's positive
control, run after the attacker because the routes change state.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import pytest

from tests.regression.bola import MATRIX, PLAN_ID_ROUTES_04, SERVED_04, plan_resource
from tests.support import stats as st
from tests.support.api import ApiDriver

pytestmark = [pytest.mark.integration, pytest.mark.coaching]

SOLO_WALL = {
    "minutes_per_session": 30,
    "sessions_per_week": 3,
    "players_available": 1,
    "equipment": ["wall"],
    "level": "intermediate",
}


def _plan(api: ApiDriver, user: str) -> dict[str, Any]:
    st.tagged_example(api, user, f"IT-04-03 {user}")
    response = api.request(user, "POST", "/me/plan", json=SOLO_WALL)
    assert response.status_code == 201, response.text
    plan: dict[str, Any] = response.json()
    return plan


def _ids(plan: dict[str, Any]) -> dict[str, str]:
    session = plan["sessions"][-1]
    return {"plan_session": session["id"], "plan_assignment": session["assignments"][-1]["id"]}


def _url(template: str, resource_id: str) -> str:
    return template.replace("{session_id}", resource_id).replace("{assignment_id}", resource_id)


def _without_support_ref(response: httpx.Response) -> tuple[int, Any]:
    body = response.json() if response.content else None
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        body["error"].pop("support_ref", None)
    return response.status_code, body


def test_it_04_03_the_plan_id_rows_name_the_contract_routes_and_kinds() -> None:
    assert sorted(PLAN_ID_ROUTES_04) == [
        ("DELETE", "/me/plan/sessions/{session_id}/done"),
        ("POST", "/me/plan/assignments/{assignment_id}/swap"),
        ("POST", "/me/plan/sessions/{session_id}/done"),
    ]
    assert {plan_resource(t) for _, t in PLAN_ID_ROUTES_04} == {"plan_session", "plan_assignment"}
    assert set(SERVED_04) <= set(MATRIX) and SERVED_04 <= set(PLAN_ID_ROUTES_04)
    assert not (set(PLAN_ID_ROUTES_04) - SERVED_04) & set(MATRIX)  # unserved rows stay out


@pytest.mark.parametrize(
    ("method", "template"), sorted(PLAN_ID_ROUTES_04), ids=lambda x: str(x).strip("/")
)
def test_it_04_03_another_account_gets_the_404_of_an_unknown_id(
    api: ApiDriver, committed_db: Any, method: str, template: str
) -> None:
    ivy, carlos = _plan(api, "ivy"), _plan(api, "carlos")
    kind = plan_resource(template)
    kwargs = PLAN_ID_ROUTES_04[(method, template)]
    own = _ids(ivy)[kind]
    assert own not in _ids(carlos).values()

    attacker = api.request("carlos", method, _url(template, own), **kwargs())
    unknown = api.request("carlos", method, _url(template, str(uuid.uuid4())), **kwargs())
    malformed = api.request("carlos", method, _url(template, "not-a-uuid"), **kwargs())

    assert attacker.status_code == 404, attacker.text
    assert _without_support_ref(attacker) == _without_support_ref(unknown)
    assert _without_support_ref(attacker) == _without_support_ref(malformed)
    if (method, template) in SERVED_04:
        owner = api.request("ivy", method, _url(template, own), **kwargs())
        assert owner.status_code not in (404, 405), f"positive control failed: {owner.text}"
    assert api.request("ivy", "GET", "/me/plan").json()["sessions"] == ivy["sessions"]
