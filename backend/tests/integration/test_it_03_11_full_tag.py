"""IT-03-11 (ST-052; FR-150, FR-151, NFR-078): API <-> DB, the Full Tag labelling tool.

TDD order (sprint-03 §5 ``FullTagAccess``, ``LabelExport``), negative cases first:

1. a player (no labeller role) gets 404 on every label route, as for a missing match
   (FR-150 "not available"), even on a consented match;
1b. a labeller who names another account's match gets the same 404 ``not_found`` as for an
   unknown match on every label route, with and without a consent record on it, never
   409 ``no_consent`` (that would tell them the match exists: T-BO-3, SEC-S3-TM-08); the owner
   filter runs before the consent check (api-sprint-03 §5.1 order of checks); nothing is stored;
2. a labeller on a match without a consent record is refused, and nothing is stored;
3. a label with an unknown player, or a frame outside the clip, is refused;
4. with consent, a hit by B1 at frame 1,840 is stored and the export validates against
   ``full-tag-labels/v1`` (``racket.dataset.labels.validate_labels``) and contains that hit.

The synthetic 60 s clip has 3,600 frames (60 fps), so the plan's frame 18,402 (sprint-03 §6) is
out of range for it and is used as the out-of-range case; the in-range hit is at 1,840
(decision-log 2026-10-06). Routes and the labeller-admin CLI are QA proposals in
``tests/support/stats.py`` until PE-1. Written red first (QA-ACC-3): ``red_until`` ST-052.

ST-052c (TCR row in docs/sprints/03/decisions/ST-052c.md): the label routes are built, every row
passes, so the module marker is removed and the file joins the per-PR gate; a received match is
probed in ``_received`` (api-sprint-03 §5.1: an unprobed video is 409 ``match_not_ready``).
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
import sqlalchemy as sa

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

HIT = {"type": "hit", "frame": 1840, "hitter": "B1"}
# The rally the hit belongs to (rally boundary + outcome), in full-tag-labels/v1 terms.
RALLY = {
    "type": "rally",
    "start_frame": 1800,
    "end_frame": 1900,
    "outcome": {
        "ending": "winner",
        "winning_side": "B",
        "responsible_player": "B1",
        "fault_kind": None,
    },
}


def _received(api: ApiDriver, user: str, title: str) -> str:
    client = api.as_user(user)
    match_id = api.run(sb.create_doubles(client, title))
    api.run(sb.receive_video(client, match_id))
    st.probe_videos()  # ready: the label routes answer 409 match_not_ready before the probe
    return match_id


def _label_rows(engine: Any) -> int:
    with engine.connect() as conn:
        tables = (
            conn.execute(
                sa.text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = current_schema() AND table_name LIKE '%label%'"
                )
            )
            .scalars()
            .all()
        )
        return sum(
            int(conn.execute(sa.text(f'SELECT count(*) FROM "{t}"')).scalar_one()) for t in tables
        )


def _control_label_route_is_served(api: ApiDriver) -> None:
    st.grant_labeller(api, "dana")
    own = _received(api, "dana", "IT-03-11 own (control)")
    st.probe_videos()  # ready, so only an unserved route can fail the control
    st.record_consent(own)
    control = st.fulltag(api, "dana", "label_match", match_id=own)
    assert control.status_code == 200, f"positive control: {control.status_code} {control.text}"


@pytest.mark.parametrize("route", sorted(st.FULLTAG_ROUTES))
def test_it_03_11_a_player_gets_404_on_every_label_route(api: ApiDriver, route: str) -> None:
    """Positive control first (as in the labeller row below): Dana's own consented match opens
    (200), because a route that is not served is also a 404 and would pass vacuously."""
    _control_label_route_is_served(api)
    match_id = _received(api, "ivy", "IT-03-11 player")
    st.record_consent(match_id)
    body = HIT if route == "label_events" else None
    response = st.fulltag(api, "ivy", route, json_body=body, match_id=match_id)
    assert response.status_code == 404, response.text


@pytest.mark.parametrize("consented", [True, False], ids=["with-consent", "without-consent"])
@pytest.mark.parametrize("route", sorted(st.FULLTAG_ROUTES))
def test_it_03_11_a_labeller_gets_404_on_another_accounts_match(
    api: ApiDriver, committed_db: Any, route: str, consented: bool
) -> None:
    """SEC-S3-TM-08 (T-BO-3, BOLA): Ivy owns the match; Dana is a labeller. Every label route
    answers Dana exactly as for an unknown match id, whether or not Ivy's match has a consent
    record. Positive control first: Dana's own consented match opens (200), because a route
    that is not served is also a 404 ``not_found`` envelope and would pass vacuously."""
    st.grant_labeller(api, "dana")
    own = _received(api, "dana", "IT-03-11 own (control)")
    st.record_consent(own)
    control = st.fulltag(api, "dana", "label_match", match_id=own)
    assert control.status_code == 200, f"positive control: {control.status_code} {control.text}"

    ivys = _received(api, "ivy", "IT-03-11 another account's match")
    if consented:
        st.record_consent(ivys)
    body = HIT if route == "label_events" else None
    unknown = st.fulltag(api, "dana", route, json_body=body, match_id=str(uuid.uuid4()))
    before = _label_rows(committed_db)
    response = st.fulltag(api, "dana", route, json_body=body, match_id=ivys)
    assert st.refusal(response)[:2] == (404, "not_found"), response.text
    assert st.refusal(response) == st.refusal(unknown), "must equal the unknown-match answer"
    assert "consent" not in response.text.lower(), "the consent check must not be reached"
    assert _label_rows(committed_db) == before


def test_it_03_11_a_labeller_is_refused_a_match_without_consent(
    api: ApiDriver, committed_db: Any
) -> None:
    match_id = _received(api, "dana", "IT-03-11 no consent")
    st.grant_labeller(api, "dana")
    before = _label_rows(committed_db)
    opened = st.fulltag(api, "dana", "label_match", match_id=match_id)
    tagged = st.fulltag(api, "dana", "label_events", json_body=HIT, match_id=match_id)
    # api-sprint-03 §5.1: exactly 409 no_consent (QA-R1S3-05: any 4xx let a missing route pass).
    assert st.refusal(opened)[:2] == (409, "no_consent"), opened.text
    assert opened.status_code != 404, "a labeller is told why, not 'not found'"
    assert "consent" in opened.text.lower(), "the refusal must say why (no consent record)"
    assert st.refusal(tagged)[:2] == (409, "no_consent"), tagged.text
    assert _label_rows(committed_db) == before


@pytest.mark.parametrize(
    "event",
    [
        {**HIT, "hitter": "C9"},
        {**HIT, "frame": 18_402},
        {**HIT, "frame": -1},
        {**HIT, "type": "smash"},
    ],
    ids=["unknown-player", "frame-beyond-clip", "negative-frame", "unknown-type"],
)
def test_it_03_11_an_invalid_label_is_refused(
    api: ApiDriver, committed_db: Any, event: dict[str, Any]
) -> None:
    match_id = _received(api, "dana", "IT-03-11 invalid")
    st.grant_labeller(api, "dana")
    st.record_consent(match_id)
    before = _label_rows(committed_db)
    response = st.fulltag(api, "dana", "label_events", json_body=event, match_id=match_id)
    # api-sprint-03 §5.4: exactly 422 invalid_label (QA-R1S3-05: a missing route is 404/405).
    assert st.refusal(response)[:2] == (422, "invalid_label"), response.text
    assert _label_rows(committed_db) == before


def test_it_03_11_a_labeller_tags_a_hit_and_the_export_validates(api: ApiDriver) -> None:
    match_id = _received(api, "dana", "IT-03-11 consented")
    st.grant_labeller(api, "dana")
    st.record_consent(match_id)
    assert st.fulltag(api, "dana", "label_match", match_id=match_id).status_code == 200
    rally = st.fulltag(api, "dana", "label_events", json_body=RALLY, match_id=match_id)
    assert rally.status_code in (200, 201), rally.text
    response = st.fulltag(api, "dana", "label_events", json_body=HIT, match_id=match_id)
    assert response.status_code in (200, 201), response.text

    export = st.fulltag(api, "dana", "label_export", match_id=match_id)
    assert export.status_code == 200, export.text
    doc = export.json()
    assert st.LABEL_SCHEMA.load()(doc) == ()
    hits = [
        e
        for rally in doc.get("rallies", [])
        for e in rally.get("events", [])
        if e.get("type") == "hit"
    ]
    assert any(e["frame"] == 1840 and e["hitter"] == "B1" for e in hits), hits
