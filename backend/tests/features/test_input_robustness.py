"""API binding of tests/features/input_robustness.feature (C-01; NFR-058). The generated cases
for every field are IT-02-10; these are the named examples of sprint-02 §14.3.1."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import scorebook as sb
from tests.support.api import ApiDriver

scenarios("input_robustness.feature")

CHARACTERS = {"NUL": "\x00", "line separator": " ", "lone surrogate": "\ud800"}
CODES = {"email address": ("email", "email_invalid"), "title": ("title", "title_invalid")}


@pytest.fixture
def ctx(api: ApiDriver, committed_db: Any) -> dict[str, Any]:
    api.as_user("ivy")
    return {"api": api, "engine": committed_db}


@given(parsers.parse('Ivy is on the "{form}" form'))
def on_form(ctx: dict[str, Any], form: str) -> None:
    ctx["form"] = form


@when(parsers.parse('she submits a {field} containing a "{character}" character'))
def submits(ctx: dict[str, Any], field: str, character: str) -> None:
    bad = CHARACTERS[character]
    if ctx["form"] == "sign-in":
        user, url, body = "anonymous", "/auth/links", {"email": f"iv{bad}y@example.com"}
    else:
        user, url, body = "ivy", "/matches", {**sb.doubles_body(f"Sat{bad}urday")}
    ctx["before"] = sb.row_counts(ctx["engine"])
    ctx["field"] = field
    ctx["response"] = ctx["api"].request(
        user, "POST", url, content=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )  # fmt: skip


@then(parsers.parse("she is told the {field} is not valid"))
def told_not_valid(ctx: dict[str, Any], field: str) -> None:
    response = ctx["response"]
    assert response.status_code == 422, response.text
    name, code = CODES[field]
    assert {"field": name, "code": code} in response.json()["error"]["fields"]


@then("nothing is saved")
def nothing_saved(ctx: dict[str, Any]) -> None:
    assert sb.row_counts(ctx["engine"]) == ctx["before"]
