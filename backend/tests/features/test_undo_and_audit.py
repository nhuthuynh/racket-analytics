"""API binding of tests/features/undo_and_audit.feature (QA-ACC for ST-031; FR-052).

Rally 5 of the scenario layout (``scorebook.SCENARIO_TAGS``) is a replay in the journey, so the
scenarios tag a 6-rally match whose rally 5 is a plain "winner" by side A.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import scorebook as sb
from tests.support.api import ApiDriver

scenarios("undo_and_audit.feature")

TAGS = sb.taglib.with_times([sb._plain(w) for w in "ABABAA"], duration_ms=48_000)


@pytest.fixture
def ctx(api: ApiDriver) -> dict[str, Any]:
    match_id = sb.ready_tagged_match(api, "ivy", tags=TAGS, title="Undo and history")
    rows = sb.sheet_body(api, "ivy", match_id)["rows"]
    return {"api": api, "match": match_id, "rally_5": rows[4]["rally_id"]}


def _command(ctx: dict[str, Any], name: str, **kwargs: Any) -> Any:
    api, ivy = ctx["api"], ctx["api"].as_user("ivy")
    version = api.run(sb.version_of(ivy, ctx["match"]))
    response = api.run(sb.command(ivy, name, version=version, match_id=ctx["match"], **kwargs))
    assert response.status_code == 200, response.text
    return response


@given("Ivy changed rally 5's winner")
def changed_winner(ctx: dict[str, Any]) -> None:
    ctx["before"] = sb.canonical(sb.sheet_body(ctx["api"], "ivy", ctx["match"]))
    _command(ctx, "correct", body={"field": "winning_side", "value": "B"}, rally_id=ctx["rally_5"])


@given(parsers.parse('Ivy changed rally 5\'s ending from "{old}" to "{new}"'))
def changed_ending(ctx: dict[str, Any], old: str, new: str) -> None:
    row = sb.sheet_body(ctx["api"], "ivy", ctx["match"])["rows"][4]
    assert row["ending"] == old.replace(" ", "_")
    body = {"field": "ending", "value": new.replace(" ", "_")}
    _command(ctx, "correct", body=body, rally_id=ctx["rally_5"])


@when("she undoes the change")
def undoes(ctx: dict[str, Any]) -> None:
    _command(ctx, "undo")


@when("she opens the correction history")
def opens_history(ctx: dict[str, Any]) -> None:
    method, url = sb.path("history", match_id=ctx["match"])
    response = ctx["api"].request("ivy", method, url)
    assert response.status_code == 200
    ctx["history"] = response.json()["items"]


@then("the score sheet is identical to the one before her change")
def identical(ctx: dict[str, Any]) -> None:
    assert sb.canonical(sb.sheet_body(ctx["api"], "ivy", ctx["match"])) == ctx["before"]


@then("her correction history lists both the change and the undo")
def lists_both(ctx: dict[str, Any]) -> None:
    opens_history(ctx)
    kinds = [(i["kind"], i["rally_id"]) for i in ctx["history"] if i["kind"] != "game_started"]
    assert kinds == [("correction", ctx["rally_5"]), ("undo", ctx["rally_5"])]
    correction, undo = (i for i in ctx["history"] if i["kind"] in ("correction", "undo"))
    assert undo["undoes"] == correction["id"]
    assert (correction["field"], correction["old_value"], correction["new_value"]) == (
        "winning_side", "A", "B",
    )  # fmt: skip


@then(
    parsers.parse(
        'it shows rally {number:d}, the field "{field}", the old value "{old}" and the new value '
        '"{new}"'
    )
)
def shows_change(ctx: dict[str, Any], number: int, field: str, old: str, new: str) -> None:
    item = next(i for i in ctx["history"] if i["kind"] == "correction")
    assert item["rally_number"] == number
    assert item["field"] == field
    assert item["old_value"] == old.replace(" ", "_")
    assert item["new_value"] == new.replace(" ", "_")
