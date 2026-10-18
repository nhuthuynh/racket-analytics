"""Binds tests/features/plan_swap_guards.feature (ST-062; FR-124; T4-PL-6, T4-PL-9).

Through the API on the committed test database (``api`` and ``committed_db`` fixtures): the
worked example is tagged (``tests.support.stats``), the plan comes from ``POST /me/plan`` over
the real drill library and the swap is ``POST /me/plan/assignments/{id}/swap``. The saved plan
is read from its rows, because ``GET /me/plan`` regenerates a plan whose source was deleted.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import pytest
import sqlalchemy as sa
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import stats as st
from tests.support.api import ApiDriver

scenarios("plan_swap_guards.feature")

PLAN = "/me/plan"
GROUP_ALL = {
    "minutes_per_session": 30,
    "sessions_per_week": 3,
    "players_available": 4,
    "equipment": ["wall", "half_court", "full_court", "ball_machine", "partner_feeder"],
    "level": "intermediate",
}


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


def _swap(api: ApiDriver, user: str, assignment_id: str, body: Any = None) -> httpx.Response:
    url = f"{PLAN}/assignments/{assignment_id}/swap"
    return api.request(user, "POST", url, json={} if body is None else body)


def _saved(engine: Any) -> tuple[Any, ...]:
    with engine.connect() as conn:
        plan = conn.execute(
            sa.text("SELECT id::text, version, excluded_drills::text FROM training_plans")
        ).all()
        rows = conn.execute(
            sa.text(
                "SELECT id::text, drill_ref, minutes, reason_not_for_me FROM plan_assignments"
                " ORDER BY id"
            )
        ).all()
    return [tuple(r) for r in plan], [tuple(r) for r in rows]


@given(parsers.parse('"{user}" has tagged the worked example'))
def tagged_example(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    ctx["match"] = st.tagged_example(api, user, "ST-062 swap guards")


@given(parsers.parse('"{user}" has a plan as a group of 4 with every kind of equipment'))
def has_group_plan(api: ApiDriver, committed_db: Any, ctx: dict[str, Any], user: str) -> None:
    response = api.request(user, "POST", PLAN, json=GROUP_ALL)
    assert response.status_code == 201, response.text
    ctx["assignment"] = response.json()["sessions"][0]["assignments"][1]["id"]


@given(parsers.parse('"{user}" has sent {count:d} swaps in the last hour'))
def sent_swaps(api: ApiDriver, ctx: dict[str, Any], user: str, count: int) -> None:
    unknown = str(uuid.uuid4())  # each spends a slot and leaves the plan as it is
    for _ in range(count):
        response = _swap(api, user, unknown)
        assert response.status_code == 404, response.text


@given(parsers.parse('"{user}" has deleted the worked example match'))
def deleted_match(api: ApiDriver, ctx: dict[str, Any], user: str) -> None:
    assert st.delete_match(api, user, ctx["match"]).status_code == 202


@when(
    parsers.parse(
        '"{user}" says "Not for me" to the second drill of the first session because "{reason}"'
    )
)
def swap_with_reason(
    api: ApiDriver, committed_db: Any, ctx: dict[str, Any], user: str, reason: str
) -> None:
    ctx["before"], ctx["reason"] = _saved(committed_db), reason
    ctx["response"] = _swap(api, user, ctx["assignment"], {"reason": reason})


@then(parsers.parse('the answer is 429 "rate_limited" with a time to retry'))
def rate_limited(ctx: dict[str, Any]) -> None:
    response = ctx["response"]
    assert st.refusal(response)[:2] == (429, "rate_limited"), response.text
    assert response.json()["error"]["retry_at"].endswith("Z")
    assert int(response.headers["retry-after"]) >= 1


@then(parsers.parse('the answer is {status:d} "{code}" with the reason "{reason}"'))
def refused_with_reason(ctx: dict[str, Any], status: int, code: str, reason: str) -> None:
    response = ctx["response"]
    assert st.refusal(response)[:2] == (status, code), response.text
    assert response.json()["error"]["message"] == reason


@then("the saved plan is unchanged and stores no reason")
def unchanged(committed_db: Any, ctx: dict[str, Any]) -> None:
    assert ctx["reason"] not in ctx["response"].text
    assert _saved(committed_db) == ctx["before"]


@then(parsers.parse('"{user}" can still send a swap'))
def other_account(api: ApiDriver, user: str) -> None:
    assert _swap(api, user, str(uuid.uuid4())).status_code == 404  # not 429: per account
