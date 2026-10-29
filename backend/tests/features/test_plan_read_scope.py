"""Binds tests/features/plan_read_scope.feature (SRE-VERIFY04R3-01; G04-02 c; coaching-plan §3, §8).

Through the API on the committed test database (``api`` fixture); the statements a read sends
are recorded on every engine (``tests.support.statements``)."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import stats as st
from tests.support.api import ApiDriver
from tests.support.statements import SCOREBOOK_TABLES, reads_of, statements, writes

scenarios("plan_read_scope.feature")

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


def _read(api: ApiDriver, user: str) -> dict[str, Any]:
    response = api.request(user, "GET", PLAN)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


@given(parsers.parse('"{user}" has tagged the worked example and has a plan'))
def planned(api: ApiDriver, ctx: dict[str, Any], committed_db: Any, user: str) -> None:
    ctx["match"] = st.tagged_example(api, user, "SRE-VERIFY04R3-01 scenario")
    response = api.request(user, "POST", PLAN, json=SOLO_WALL)
    assert response.status_code == 201, response.text


@given(parsers.parse('"{user}" has read the plan'))
def has_read(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    ctx["before"] = _read(api, user)


@when(parsers.parse('"{user}" corrects rally 3 of the match'))
def corrects(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    assert st.correct_rally_3(api, user, ctx["match"]).status_code == 200


@when(parsers.parse('"{user}" reads the plan'))
def reads(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    with statements() as sent:
        ctx["after"] = _read(api, user)
    ctx["sent"] = sent


@then("the ranking read differs from the one read before")
def ranking_differs(ctx: dict[str, Any]) -> None:
    assert ctx["after"]["ranking"] != ctx["before"]["ranking"]


@then("the plan read is the plan read before")
def same_plan(ctx: dict[str, Any]) -> None:
    assert ctx["after"] == ctx["before"]


@then("the read replayed no scorebook and wrote nothing")
def nothing_replayed(ctx: dict[str, Any]) -> None:
    assert reads_of(ctx["sent"], *SCOREBOOK_TABLES) == []
    assert writes(ctx["sent"]) == []
