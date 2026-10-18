"""Binds tests/features/plan_follow_through.feature (ST-062; FR-124; api-sprint-04 §3).

Through the API on the committed test database (``api`` fixture): the worked example is tagged
(``tests.support.stats``), the plan comes from ``POST /me/plan`` over the real drill library, and
the follow-through route is ``POST /me/plan/sessions/{id}/done``.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import stats as st
from tests.support.api import ApiDriver

scenarios("plan_follow_through.feature")

PLAN = "/me/plan"
SOLO_WALL = {
    "minutes_per_session": 30,
    "sessions_per_week": 3,
    "players_available": 1,
    "equipment": ["wall"],
    "level": "intermediate",
}


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


def _new_plan(api: ApiDriver, ctx: dict[str, Any], user: str, prefs: dict[str, Any]) -> None:
    response = api.request(user, "POST", PLAN, json=prefs)
    assert response.status_code == 201, response.text
    ctx["plan"] = response.json()


@when(parsers.parse('"{user}" marks the first session done with the op id "{op}"'))
def mark_done(api: ApiDriver, ctx: dict[str, Any], user: str, op: str) -> None:
    url = f"{PLAN}/sessions/{ctx['plan']['sessions'][0]['id']}/done"
    ctx["first"] = api.request(user, "POST", url, headers={"Idempotency-Key": op})


@when(parsers.parse('"{user}" sends the same op "{op}" again when back online'))
def replay_done(api: ApiDriver, ctx: dict[str, Any], user: str, op: str) -> None:
    url = f"{PLAN}/sessions/{ctx['plan']['sessions'][0]['id']}/done"
    ctx["second"] = api.request(user, "POST", url, headers={"Idempotency-Key": op})


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
