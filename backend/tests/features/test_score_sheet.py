"""API binding of tests/features/score_sheet.feature (QA-ACC for ST-030; FR-049, FR-055).

Binds "Read the match without the video" and "Rules not yet verified"; the narrow-screen
scenario is browser-only (``web/e2e/sprint-02/score-sheet.spec.ts``). The 3-game match is
``taglib.three_game_script(seed=2)``; its rows are compared with the independent stepper.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, scenario, then, when

from tests.support import scorebook as sb
from tests.support.api import ApiDriver

FEATURE = "score_sheet.feature"
ROW_FIELDS = ("number", "serving_side", "score_before", "score_after", "winning_side", "ending")


@pytest.fixture
def ctx(api: ApiDriver) -> dict[str, Any]:
    return {"api": api}


@scenario(FEATURE, "Read the match without the video")
def test_read_the_match_without_the_video() -> None:
    pass


@scenario(FEATURE, "Rules not yet verified")
def test_rules_not_yet_verified() -> None:
    pass


@given("Ivy has tagged a 3-game match")
def three_games(ctx: dict[str, Any]) -> None:
    api = ctx["api"]
    ivy = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(ivy, "Three games"))
    api.run(sb.receive_video(ivy, match_id))
    games, clock = sb.taglib.three_game_script(seed=2), 0
    for game in games:
        api.run(sb.start_game(ivy, match_id, game["first_serving_side"]))
        tags = sb.taglib.with_times(game["tags"], duration_ms=len(game["tags"]) * 400)
        tags = [
            {**t, "start_ms": t["start_ms"] + clock, "end_ms": t["end_ms"] + clock} for t in tags
        ]
        clock = tags[-1]["end_ms"] + 100
        api.run(sb.tag_all(ivy, match_id, tags))
    ctx["match"], ctx["games"] = match_id, games
    # One correction, so a "corrected by you" row exists: the winner of game 3's last rally
    # stays the same side, only its ending changes (no rescoring of the decided match).
    rows = sb.sheet_body(api, "ivy", match_id)["rows"]
    version = api.run(sb.version_of(ivy, match_id))
    corrected = api.run(
        sb.command(ivy, "correct", version=version, body={"field": "ending", "value": "fault"},
                   match_id=match_id, rally_id=rows[-1]["rally_id"])
    )  # fmt: skip
    assert corrected.status_code == 200, corrected.text
    ctx["corrected"] = rows[-1]["rally_id"]


@given("the active rules preset contains an unverified rule")
def unverified_preset(ctx: dict[str, Any]) -> None:
    ctx["match"] = sb.ready_tagged_match(ctx["api"], "ivy", title="Unofficial")


@when("she opens the score sheet")
@when("Ivy opens any score sheet")
def opens(ctx: dict[str, Any]) -> None:
    ctx["sheet"] = sb.sheet_body(ctx["api"], "ivy", ctx["match"])


@then("every rally shows its number, server, score before and after, winner and ending")
def every_rally(ctx: dict[str, Any]) -> None:
    sheet = ctx["sheet"]
    rows = sheet["rows"]
    assert len(rows) == sum(len(g["tags"]) for g in ctx["games"])
    assert [r["number"] for r in rows] == list(range(1, len(rows) + 1))
    for row in rows:
        assert all(row.get(f) is not None for f in ROW_FIELDS), row
        assert row["server"] in ("A1", "A2", "B1", "B2"), row
    offset = 0
    for number, game in enumerate(ctx["games"], start=1):
        expected = sb.taglib.expected_rows(
            game["tags"], first_serving_side=game["first_serving_side"]
        )
        actual = [r for r in rows if r["game"] == number]
        for e, a in zip(expected, actual, strict=True):
            for f in ("serving_side", "score_before", "score_after", "winning_side"):
                assert e[f] == a[f], (number, e, a)
        offset += len(actual)
    assert sheet["match_winner"] in ("A", "B")


@then('corrected rallies are marked "corrected by you" in text')
def corrected_marked(ctx: dict[str, Any]) -> None:
    marked = [r["rally_id"] for r in ctx["sheet"]["rows"] if r["corrected_by_user"]]
    assert marked == [ctx["corrected"]]


@then('she sees "unofficial scoring (rules not yet verified)"')
def unofficial(ctx: dict[str, Any]) -> None:
    sheet = ctx["sheet"]
    assert sheet["unofficial"] is True
    assert sheet["label"] == "unofficial scoring (rules not yet verified)"
    assert sheet["rules_version"] == "PROVISIONAL-UNVERIFIED"
