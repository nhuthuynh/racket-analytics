"""Steps for tests/features/object_level_authorisation.feature (ST-006; NFR-051, NFR-064;
AQS/SEC-09, AQS/SEC-03)."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import httpx
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.regression.bola import uncovered_routes
from tests.support import contract
from tests.support.api import ApiDriver

pytestmark = pytest.mark.red_until(story="ST-006")

scenarios("object_level_authorisation.feature")

ACTIONS = {
    "open": ("GET", contract.MATCH, {}),
    "upload to": (
        "POST",
        contract.UPLOAD_CREATE,
        {"headers": {"Tus-Resumable": contract.TUS_VERSION, "Upload-Length": "10"}},
    ),
    "see facts of": ("GET", contract.MATCH_MEDIA, {}),
}
IVY_TITLE = "Ivy private match 7f3a"


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


def _create(api: ApiDriver, user: str, title: str) -> str:
    response = api.request(
        user, "POST", contract.MATCHES, json={"title": title, "format": "singles"}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


@given("Ivy owns a match")
def ivy_owns_a_match(api: ApiDriver, ctx: dict[str, Any]) -> None:
    ctx["match_id"] = _create(api, "ivy", IVY_TITLE)


@when(parsers.parse("Carlos tries to {action} that match by its ID"))
def carlos_tries(
    api: ApiDriver, ctx: dict[str, Any], action: str, caplog: pytest.LogCaptureFixture
) -> None:
    method, template, kwargs = ACTIONS[action]
    api.as_user("carlos")
    caplog.clear()
    with caplog.at_level(logging.INFO, logger=contract.SECURITY_LOGGER):
        ctx["attempt"] = api.request(
            "carlos", method, template.format(match_id=ctx["match_id"]), **kwargs
        )
        ctx["security_records"] = [
            r for r in caplog.records if r.name.startswith(contract.SECURITY_LOGGER)
        ]
    ctx["missing"] = api.request("carlos", method, template.format(match_id=uuid.uuid4()), **kwargs)
    # positive control: the route exists and works for the owner (no vacuous 404s)
    ctx["owner"] = api.request("ivy", method, template.format(match_id=ctx["match_id"]), **kwargs)


def _comparable(response: httpx.Response) -> tuple[int, Any]:
    try:
        body = response.json()
    except json.JSONDecodeError:
        return response.status_code, response.text
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        body = {**body, "error": {k: v for k, v in body["error"].items() if k != "support_ref"}}
    return response.status_code, body


@then('Carlos gets the same "not found" result as for a match that does not exist')
def same_not_found(ctx: dict[str, Any]) -> None:
    assert ctx["owner"].status_code not in (404, 405), "route missing: the owner gets 404/405 too"
    assert ctx["attempt"].status_code == 404
    assert _comparable(ctx["attempt"]) == _comparable(ctx["missing"])


@then("the attempt appears in the security log without Ivy's details")
def security_logged(ctx: dict[str, Any]) -> None:
    records = ctx["security_records"]
    assert records, f"no record on logger {contract.SECURITY_LOGGER!r} for the denied attempt"
    for record in records:
        text = record.getMessage() + " " + json.dumps(record.__dict__, default=str)
        assert "ivy" not in text.lower()
        assert IVY_TITLE not in text


@given("Ivy owns 2 matches and Carlos owns 1 match")
def three_matches(api: ApiDriver) -> None:
    _create(api, "ivy", "Ivy one")
    _create(api, "ivy", "Ivy two")
    _create(api, "carlos", "Carlos one")


@when("Carlos opens his matches list", target_fixture="listing")
def carlos_lists(api: ApiDriver) -> httpx.Response:
    return api.request("carlos", "GET", contract.MATCHES)


@then(parsers.parse("he sees exactly {count:d} match"))
def sees_exactly(listing: httpx.Response, count: int) -> None:
    assert listing.status_code == 200, listing.text
    body = listing.json()
    items = body["items"] if isinstance(body, dict) else body
    assert len(items) == count
    assert {m["title"] for m in items} == {"Carlos one"}


@given(
    "a route that takes a match ID is added without a BOLA matrix entry",
    target_fixture="app_under_test",
)
def add_unprotected_route(committed_app: Any) -> Any:
    committed_app.add_api_route(
        "/matches/{match_id}/unreviewed-export", lambda match_id: {}, methods=["GET"]
    )
    return committed_app


@when("the regression suite runs", target_fixture="uncovered")
def run_inventory(app_under_test: Any) -> list[str]:
    return uncovered_routes(app_under_test)


@then("the suite fails and names the uncovered route")
def names_route(uncovered: list[str]) -> None:
    assert uncovered == ["GET /matches/{match_id}/unreviewed-export"]
