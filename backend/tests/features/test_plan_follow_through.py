"""Binds tests/features/plan_follow_through.feature (ST-062; FR-124; api-sprint-04 §3).

Through the API on the committed test database (``api`` fixture): the worked example is tagged
(``tests.support.stats``), the plan comes from ``POST /me/plan`` over the real drill library, and
the follow-through routes are ``POST/DELETE /me/plan/sessions/{id}/done`` and
``POST /me/plan/assignments/{id}/swap``. Plans are graded with the QA harness's independent
reference (``scripts/measure/planlib.py``), which imports nothing from ``racket.coaching``.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver
from tests.support.paths import REPO

scenarios("plan_follow_through.feature")

planlib = sb._load("planlib")
PLAN = "/me/plan"
SOLO_WALL = {
    "minutes_per_session": 30,
    "sessions_per_week": 3,
    "players_available": 1,
    "equipment": ["wall"],
    "level": "intermediate",
}
# A setup where the second drill of the first session has alternatives in content/drills
GROUP_ALL = SOLO_WALL | {
    "players_available": 4,
    "equipment": ["wall", "half_court", "full_court", "ball_machine", "partner_feeder"],
}
SWAPS_MAX = 40  # more than the drill library holds: a swap loop that does not end fails


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


def _answer(ctx: dict[str, Any], key: str = "response") -> httpx.Response:
    response = ctx[key]
    assert isinstance(response, httpx.Response)
    return response


def _plan(api: ApiDriver, user: str) -> dict[str, Any]:
    response = api.request(user, "GET", PLAN)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _swap(api: ApiDriver, user: str, assignment_id: str, body: Any = None) -> httpx.Response:
    url = f"{PLAN}/assignments/{assignment_id}/swap"
    return api.request(user, "POST", url, json={} if body is None else body)


def _ref(assignment: dict[str, Any]) -> str:
    return f"{assignment['drill']['id']}@{assignment['drill']['version']}"


@given(parsers.parse('"{user}" has tagged the worked example'))
def tagged_example(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    ctx["match"] = st.tagged_example(api, user, "ST-062 worked example")


@given(
    parsers.parse(
        '"{user}" has a plan as a solo player with a wall, 30 minutes per session, '
        "3 sessions a week"
    )
)
def has_plan(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    _new_plan(api, ctx, user, SOLO_WALL)


@given(
    parsers.parse(
        '"{user}" has a plan as a group of 4 with every kind of equipment, 30 minutes per '
        "session, 3 sessions a week"
    )
)
def has_group_plan(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    _new_plan(api, ctx, user, GROUP_ALL)


def _new_plan(api: ApiDriver, ctx: dict[str, Any], user: str, prefs: dict[str, Any]) -> None:
    response = api.request(user, "POST", PLAN, json=prefs)
    assert response.status_code == 201, response.text
    ctx["plan"] = response.json()
    target = ctx["plan"]["sessions"][0]["assignments"][1]
    ctx["assignment"], ctx["original"] = target["id"], target


@given(
    parsers.parse(
        '"{user}" has said "Not for me" to the second drill of the first session until no other '
        "drill fits"
    )
)
def swapped_until_none(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    seen = [_ref(ctx["original"])]
    for _ in range(SWAPS_MAX):
        response = _swap(api, user, ctx["assignment"])
        if response.status_code == 409:
            break
        assert response.status_code == 200, response.text
        ref = _ref(response.json()["session"]["assignments"][1])
        assert ref not in seen, f"{ref} was offered again after {seen}"
        seen.append(ref)
    else:
        pytest.fail(f"no 409 no_alternative after {SWAPS_MAX} swaps")
    ctx["before"] = _plan(api, user)


@when(parsers.parse('"{user}" says "Not for me" to that drill again'))
def swap_again(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    ctx["response"] = _swap(api, user, ctx["assignment"])


@when(
    parsers.parse(
        '"{user}" says "Not for me" to the second drill of the first session because "{reason}"'
    )
)
def swap_with_reason(api: ApiDriver, ctx: dict[str, Any], user: str, reason: str) -> None:
    ctx["response"] = _swap(api, user, ctx["assignment"], {"reason": reason})


@when(parsers.parse('"{user}" marks the first session done with the op id "{op}"'))
def mark_done(api: ApiDriver, ctx: dict[str, Any], user: str, op: str) -> None:
    url = f"{PLAN}/sessions/{ctx['plan']['sessions'][0]['id']}/done"
    ctx["first"] = api.request(user, "POST", url, headers={"Idempotency-Key": op})


@when(parsers.parse('"{user}" sends the same op "{op}" again when back online'))
def replay_done(api: ApiDriver, ctx: dict[str, Any], user: str, op: str) -> None:
    url = f"{PLAN}/sessions/{ctx['plan']['sessions'][0]['id']}/done"
    ctx["second"] = api.request(user, "POST", url, headers={"Idempotency-Key": op})


@then(parsers.parse('the answer is {status:d} "{code}" with the reason "{reason}"'))
def refused_with_reason(ctx: dict[str, Any], status: int, code: str, reason: str) -> None:
    response = _answer(ctx)
    assert st.refusal(response)[:2] == (status, code), response.text
    assert response.json()["error"]["message"] == reason


@then(parsers.parse('"{user}" reads the same plan at the same version as before'))
def same_plan(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    assert _plan(api, user) == ctx["before"]


@then("the answer is 200 with the session and the next plan version")
def swapped(ctx: dict[str, Any]) -> None:
    response = _answer(ctx)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["plan_version"] == ctx["plan"]["version"] + 1
    assert body["session"]["id"] == ctx["plan"]["sessions"][0]["id"]
    ctx["session"] = body["session"]


@then("the assignment keeps its id and gets another reviewed drill for the same metric")
def same_metric(ctx: dict[str, Any]) -> None:
    new = ctx["session"]["assignments"][1]
    old = ctx["original"]
    assert new["id"] == old["id"]
    assert _ref(new) != _ref(old)
    assert new["citation"]["metric_id"] == old["citation"]["metric_id"]
    assert new["weakness_id"] == old["weakness_id"]
    library = planlib.load_library(REPO / "content" / "drills")
    assert library[_ref(new)]["review_status"] in ("coach-reviewed", "verified")
    assert "reason" not in str(new)
    assert "My wrist hurts" not in str(ctx["session"])


@then("the plan still keeps every rule QD-PL-01 to QD-PL-03")
def keeps_rules(api: ApiDriver, ctx: dict[str, Any]) -> None:
    plan = _plan(api, "ivy")
    library = planlib.load_library(REPO / "content" / "drills")
    assert planlib.grade(plan, library) == []
    assert plan["sessions"][0] == ctx["session"]
    assert plan["sessions"][1:] == ctx["plan"]["sessions"][1:]
    ctx["after"] = plan


@then("the swapped-out drill is not offered again for that assignment")
def not_again(api: ApiDriver, ctx: dict[str, Any]) -> None:
    response = _swap(api, "ivy", ctx["assignment"])
    if response.status_code == 409:
        assert st.refusal(response)[:2] == (409, "no_alternative")
        return
    assert response.status_code == 200, response.text
    offered = _ref(response.json()["session"]["assignments"][1])
    assert offered not in (_ref(ctx["original"]), _ref(ctx["session"]["assignments"][1]))


@then("the second answer is the first one, replayed, at the same plan version")
def replayed(ctx: dict[str, Any]) -> None:
    first, second = _answer(ctx, "first"), _answer(ctx, "second")
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["replayed"] is False
    assert second.json() == first.json() | {"replayed": True}


@then(parsers.parse('"{user}" reads the first session done once and the plan version raised by 1'))
def done_once(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    plan = _plan(api, user)
    first = _answer(ctx, "first").json()
    assert plan["version"] == ctx["plan"]["version"] + 1 == first["plan_version"]
    assert [s["done"] for s in plan["sessions"]] == [True] + [False] * 5
    assert plan["sessions"][0]["done_at"] == first["done_at"]
