"""API binding of tests/features/full_tag.feature (QA-ACC-3 for ST-052; FR-150, FR-151).
"Stepping frame by frame" is the browser's (E2E-03-05); here the labeller (dev user Dana with
the labeller role) marks the rally and the hit through the label routes, and the export is
validated against ``full-tag-labels/v1``. Routes and the admin CLI are the QA proposals in
``tests/support/stats.py`` until PE-1. Written red first: ``red_until`` ST-052.

Marker ``red_until`` ST-052 removed (VR2-S3-01, TCR row 2026-10-07): the story is built and
every row passes, so the file is in the per-PR gate and the coverage selection.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

scenarios("full_tag.feature")


@pytest.fixture
def ctx(api: ApiDriver) -> dict[str, Any]:
    return {"api": api}


def _received(ctx: dict[str, Any], user: str) -> str:
    api = ctx["api"]
    match_id = api.run(sb.create_doubles(api.as_user(user), "Full Tag"))
    api.run(sb.receive_video(api.as_user(user), match_id))
    st.probe_videos()
    return str(match_id)


@given("a labeller is stepping frame by frame through a consented match")
def consented(ctx: dict[str, Any]) -> None:
    ctx["match"] = _received(ctx, "dana")
    st.grant_labeller(ctx["api"], "dana")
    st.record_consent(ctx["match"])
    opened = st.fulltag(ctx["api"], "dana", "label_match", match_id=ctx["match"])
    assert opened.status_code == 200, opened.text


@when(parsers.parse("they tag a hit by player {player} at frame {frame}"))
def tag_hit(ctx: dict[str, Any], player: str, frame: str) -> None:
    number = int(frame.replace(",", ""))
    rally = {
        "type": "rally",
        "start_frame": number - 40,
        "end_frame": number + 60,
        "outcome": {
            "ending": "winner",
            "winning_side": player[0],
            "responsible_player": player,
            "fault_kind": None,
        },
    }
    for body in (rally, {"type": "hit", "frame": number, "hitter": player}):
        response = st.fulltag(
            ctx["api"], "dana", "label_events", json_body=body, match_id=ctx["match"]
        )
        assert response.status_code in (200, 201), response.text
    ctx["hit"] = (number, player)


@then("the exported label file contains that hit with its frame and player")
def exported(ctx: dict[str, Any]) -> None:
    export = st.fulltag(ctx["api"], "dana", "label_export", match_id=ctx["match"])
    assert export.status_code == 200, export.text
    doc = export.json()
    assert st.LABEL_SCHEMA.load()(doc) == ()
    hits = {
        (e["frame"], e["hitter"])
        for rally in doc["rallies"]
        for e in rally["events"]
        if e["type"] == "hit"
    }
    assert ctx["hit"] in hits


@given("Ivy has a normal player account")
def player(ctx: dict[str, Any]) -> None:
    ctx["match"] = _received(ctx, "ivy")
    st.record_consent(ctx["match"])


@then("the Full Tag mode is not available to her")
def not_available(ctx: dict[str, Any]) -> None:
    for name in st.FULLTAG_ROUTES:
        response = st.fulltag(ctx["api"], "ivy", name, match_id=ctx["match"])
        assert response.status_code == 404, f"{name}: {response.status_code}"


@given("a labeller opens a match that has no consent record")
def no_consent(ctx: dict[str, Any]) -> None:
    ctx["match"] = _received(ctx, "dana")
    st.grant_labeller(ctx["api"], "dana")
    ctx["response"] = st.fulltag(ctx["api"], "dana", "label_match", match_id=ctx["match"])


@then("they are told the match cannot be labelled")
def cannot_be_labelled(ctx: dict[str, Any]) -> None:
    response = ctx["response"]
    # api-sprint-03 §5.1: exactly 409 no_consent (QA-R1S3-05).
    assert st.refusal(response)[:2] == (409, "no_consent"), response.text
    assert response.status_code != 404
    assert "consent" in response.text.lower()
