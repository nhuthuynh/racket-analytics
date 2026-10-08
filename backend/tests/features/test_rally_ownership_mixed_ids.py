"""Steps for tests/features/rally_ownership_mixed_ids.feature (C3-10; SEC-RV3-03, NFR-051).

Carlos names Ivy's rally under his own match, with his current version so a command passes the
version check and reaches the rally lookup (without it the answer is a 409 that proves nothing).
His own rally on the same route is the positive control: the route works for the match's owner,
so the 404 is not vacuous."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.regression.bola import RALLY_ID_ROUTES_02
from tests.support import scorebook as sb
from tests.support.api import ApiDriver

scenarios("rally_ownership_mixed_ids.feature")

ACTIONS = {
    "correct": ("PATCH", "/matches/{match_id}/rallies/{rally_id}"),
    "decide on": ("POST", "/matches/{match_id}/rallies/{rally_id}/resolution"),
    "watch": ("GET", "/matches/{match_id}/rallies/{rally_id}/media"),
}


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


def _first_rally(api: ApiDriver, user: str, match_id: str) -> str:
    return str(sb.sheet_body(api, user, match_id)["rows"][0]["rally_id"])


def _comparable(response: httpx.Response) -> tuple[int, Any]:
    body = response.json() if response.content else None
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        body = {**body, "error": {k: v for k, v in body["error"].items() if k != "support_ref"}}
    return response.status_code, body


@given("Ivy and Carlos each own a tagged match")
def two_owners(api: ApiDriver, ctx: dict[str, Any]) -> None:
    ctx["ivy_match"] = sb.ready_tagged_match(api, "ivy", title="C3-10 mixed ids ivy")
    ctx["ivy_rally"] = _first_rally(api, "ivy", ctx["ivy_match"])
    ctx["carlos_match"] = sb.ready_tagged_match(api, "carlos", title="C3-10 mixed ids carlos")
    ctx["carlos_rally"] = _first_rally(api, "carlos", ctx["carlos_match"])
    ctx["ivy_sheet"] = sb.sheet_body(api, "ivy", ctx["ivy_match"])


@when(
    parsers.parse(
        "Carlos tries to {action} Ivy's rally under his own match, with his current version"
    )
)
def carlos_mixes_ids(api: ApiDriver, ctx: dict[str, Any], action: str) -> None:
    method, template = ACTIONS[action]
    kwargs = RALLY_ID_ROUTES_02[(method, template)]
    match = ctx["carlos_match"]
    version = api.run(sb.version_of(api.as_user("carlos"), match))
    headers = {sb.tagcontract.VERSION_HEADER: f'"{version}"'}

    def call(rally_id: str) -> httpx.Response:
        url = template.format(match_id=match, rally_id=rally_id)
        return api.request("carlos", method, url, headers=headers, **kwargs())

    ctx["attempt"] = call(ctx["ivy_rally"])
    ctx["missing"] = call(str(uuid.uuid4()))
    ctx["own"] = call(ctx["carlos_rally"])  # positive control, last: it may change his sheet


@then('Carlos gets the same "not found" result as for a rally that does not exist')
def same_not_found(ctx: dict[str, Any]) -> None:
    assert ctx["own"].status_code not in (404, 405, 409), (
        f"positive control: Carlos's own rally gave {ctx['own'].status_code} {ctx['own'].text}"
    )
    assert ctx["attempt"].status_code == 404, ctx["attempt"].text
    assert _comparable(ctx["attempt"]) == _comparable(ctx["missing"])


@then("Ivy's score sheet is unchanged")
def ivy_unchanged(api: ApiDriver, ctx: dict[str, Any]) -> None:
    assert sb.sheet_body(api, "ivy", ctx["ivy_match"]) == ctx["ivy_sheet"]
