"""Binds tests/features/rules_only_plan_api.feature (ST-061b; FR-120..FR-123; api-sprint-04 §2).

Through the API on the committed test database (``api`` fixture): matches are tagged with the
coach's worked example (``tests.support.stats``), the plan comes from ``POST /me/plan`` over the
real drill library and is read back with ``GET /me/plan``.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import stats as st
from tests.support.api import ApiDriver

scenarios("rules_only_plan_api.feature")

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


def _answer(ctx: dict[str, Any]) -> httpx.Response:
    response = ctx["response"]
    assert isinstance(response, httpx.Response)
    return response


def _plan(ctx: dict[str, Any]) -> dict[str, Any]:
    response = _answer(ctx)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def _assignments(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    return [a for s in _plan(ctx)["sessions"] for a in s["assignments"]]


@given(parsers.parse('"{user}" has no tagged match'))
def no_tagged_match(api: ApiDriver, user: str) -> None:
    assert st.me_id(api, user)


@given(parsers.parse('"{user}" has tagged the worked example'))
def tagged_example(api: ApiDriver, user: str) -> None:
    st.tagged_example(api, user, "ST-061b worked example")


@given(parsers.parse('"{user}" has tagged the worked example in {count:d} matches'))
def tagged_examples(api: ApiDriver, ctx: dict[str, Any], user: str, count: int) -> None:
    ctx["matches"] = [st.tagged_example(api, user, f"ST-061b match {i}") for i in range(count)]


@given(
    parsers.parse(
        '"{user}" has a plan as a solo player with a wall, 30 minutes per session, '
        "3 sessions a week"
    )
)
def has_plan(api: ApiDriver, user: str) -> None:
    response = api.request(user, "POST", PLAN, json=SOLO_WALL)
    assert response.status_code == 201, response.text


@when(
    parsers.parse(
        '"{user}" asks for a plan as a solo player with a wall, 30 minutes per session, '
        "3 sessions a week"
    )
)
def ask_solo_wall(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    ctx["response"] = api.request(user, "POST", PLAN, json=SOLO_WALL)


@when(
    parsers.parse(
        '"{user}" asks for a plan with {minutes:d} minutes per session, {sessions:d} sessions '
        'a week and equipment "{item}"'
    )
)
def ask_out_of_range(
    api: ApiDriver, ctx: dict[str, Any], user: str, minutes: int, sessions: int, item: str
) -> None:
    body = SOLO_WALL | {
        "minutes_per_session": minutes,
        "sessions_per_week": sessions,
        "equipment": [item],
    }
    ctx["response"] = api.request(user, "POST", PLAN, json=body)


@when(
    parsers.parse(
        '"{user}" asks for a plan as an advanced solo player with no equipment, 30 minutes per '
        "session, 3 sessions a week"
    )
)
def ask_nothing_fits(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    body = SOLO_WALL | {"equipment": [], "level": "advanced"}
    ctx["response"] = api.request(user, "POST", PLAN, json=body)


@when(parsers.parse('"{user}" deletes one of the {count:d} matches'))
def delete_one(api: ApiDriver, ctx: dict[str, Any], user: str, count: int) -> None:
    assert len(ctx["matches"]) == count
    ctx["deleted"] = ctx["matches"][-1]
    assert st.delete_match(api, user, ctx["deleted"]).status_code == 202


@when(parsers.parse('"{user}" reads the plan'))
def read_plan(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    ctx["read"] = api.request(user, "GET", PLAN)


def _read(ctx: dict[str, Any]) -> dict[str, Any]:
    response = ctx["read"]
    assert isinstance(response, httpx.Response)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


@then("the plan is regenerated because a source match was deleted")
def regenerated(ctx: dict[str, Any]) -> None:
    assert _read(ctx)["regenerated"] == "source_match_deleted"


@then("no drill cites the deleted match")
def not_cited(ctx: dict[str, Any]) -> None:
    for s in _read(ctx)["sessions"]:
        for a in s["assignments"]:
            assert [e["match_id"] for e in a["citation"]["evidence"]] == ctx["matches"][:1], a


@then(parsers.parse("the plan read says it is based on limited data from {rallies:d} rallies"))
def read_limited(ctx: dict[str, Any], rallies: int) -> None:
    assert _read(ctx)["limited_data"] == {"rallies": rallies}


@then(parsers.parse('the answer is {status:d} "{code}" with the reason "{reason}"'))
def refused_with_reason(ctx: dict[str, Any], status: int, code: str, reason: str) -> None:
    response = _answer(ctx)
    assert st.refusal(response)[:2] == (status, code), response.text
    assert response.json()["error"]["message"] == reason


@then(parsers.parse('the answer is 422 with the field codes "{codes}"'))
def refused_fields(ctx: dict[str, Any], codes: str) -> None:
    want = [tuple(pair.split(":")) for pair in codes.split(", ")]
    assert st.refusal(_answer(ctx)) == (422, "validation_failed", want)


@then(parsers.parse('"{user}" has no plan to read'))
def no_plan_to_read(api: ApiDriver, user: str) -> None:
    response = api.request(user, "GET", PLAN)
    assert st.refusal(response)[:2] == (404, "no_plan"), response.text
    assert response.json()["error"]["message"] == "You have no plan yet."


@then("the answer is 201 with the plan")
def created(ctx: dict[str, Any]) -> None:
    response = _answer(ctx)
    assert response.status_code == 201, response.text
    assert response.headers["location"] == PLAN
    assert response.json()["preferences"] == SOLO_WALL | {"weekly_minutes": 90}


@then(
    parsers.parse('the weaknesses are ranked in "{unit}" with the side-out split marked unverified')
)
def ranked(ctx: dict[str, Any], unit: str) -> None:
    ranking = _plan(ctx)["ranking"]
    assert (ranking["unit"], ranking["side_out_verified"]) == (unit, False)
    weaknesses = ranking["weaknesses"]
    assert weaknesses, ranking
    assert [w["rank"] for w in weaknesses] == list(range(1, len(weaknesses) + 1))
    per_game = [w["per_game"] for w in weaknesses]
    assert per_game == sorted(per_game, reverse=True)
    for w in weaknesses:
        assert w["per_game"] == round(w["on_serve_per_game"] + w["on_receive_per_game"], 2)


@then("the plan is marked as unofficial scoring")
def unofficial(ctx: dict[str, Any]) -> None:
    plan = _plan(ctx)
    assert (plan["unofficial"], plan["label"]) == (True, st.UNOFFICIAL)
    assert plan["drills_verified"] is False  # no drill is `verified` before P15


@then("the plan has 6 sessions of at most 30 minutes, each starting with a warm-up")
def sessions(ctx: dict[str, Any]) -> None:
    found = _plan(ctx)["sessions"]
    assert [(s["week"], s["index"]) for s in found] == [(w, i) for w in (1, 2) for i in (1, 2, 3)]
    for s in found:
        assert sum(a["minutes"] for a in s["assignments"]) <= 30
        assert s["assignments"][0]["warm_up"] is True
        assert "warm-up" in s["assignments"][0]["drill"]["skills"]
        assert (s["done"], s["done_at"]) == (False, None)


@then("every drill cites a metric, its value, n and at most 10 rallies")
def cited(ctx: dict[str, Any]) -> None:
    for a in _assignments(ctx):
        c = a["citation"]
        assert c["metric_id"], a
        assert c["value"] is not None, a
        assert c["n"] >= 1, a
        assert 1 <= len(c["rally_ids"]) <= 10, a
        assert c["side"] == "A", a
        assert [e["side"] for e in c["evidence"]] == ["A"], a
        assert a["why"], a


@then(parsers.parse("the plan says it is based on limited data from {rallies:d} rallies"))
def limited(ctx: dict[str, Any], rallies: int) -> None:
    assert _plan(ctx)["limited_data"] == {"rallies": rallies}


@then(parsers.parse('"{user}" reads the same plan back'))
def read_back(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    response = api.request(user, "GET", PLAN)
    assert response.status_code == 200, response.text
    assert response.json() == _plan(ctx)
