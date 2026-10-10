"""ST-052c (FR-150, FR-151; api-sprint-03 §5.1-§5.4): the Full Tag label routes on real Postgres
and the object store, for the checks IT-03-11 does not name. Negative cases first.

1. A consented match whose video is not probed yet: every label route answers 409
   ``match_not_ready`` (no frame grid to check a label against) and nothing is stored.
2. A label body with a non-finite number (``NaN``, which Python's JSON reader accepts and JSONB
   refuses) is 422 ``invalid_label``, never a 5xx, and nothing is stored.
3. The opened session carries the frame grid of the probed video: ``fps`` and
   ``frame_count = floor(duration_ms x fps / 1000)`` from the media facts, and the four doubles
   slots; the export is a ``no-store`` attachment whose clip is ``match:<id>``.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

pytestmark = [pytest.mark.integration]


def _consented(api: ApiDriver, title: str, *, probed: bool) -> str:
    st.grant_labeller(api, "dana")
    match_id = str(api.run(sb.create_doubles(api.as_user("dana"), title)))
    api.run(sb.receive_video(api.as_user("dana"), match_id))
    if probed:
        st.probe_videos()
    st.record_consent(match_id)
    return match_id


def _sessions(engine: Any) -> int:
    with engine.connect() as conn:
        return int(conn.execute(sa.text("SELECT count(*) FROM label_sessions")).scalar_one())


def _stored_labels(engine: Any) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(
                sa.text(
                    "SELECT coalesce(sum(jsonb_array_length(rallies) + jsonb_array_length(events)),"
                    " 0) FROM label_sessions"
                )
            ).scalar_one()
        )


@pytest.mark.parametrize("route", sorted(st.FULLTAG_ROUTES))
def test_st_052c_an_unprobed_video_is_not_ready_and_nothing_is_stored(
    api: ApiDriver, committed_db: Any, route: str
) -> None:
    match_id = _consented(api, "ST-052c unprobed", probed=False)
    before = _sessions(committed_db)
    body = {"type": "hit", "frame": 10, "hitter": "B1"} if route == "label_events" else None
    response = st.fulltag(api, "dana", route, json_body=body, match_id=match_id)
    assert st.refusal(response)[:2] == (409, "match_not_ready"), response.text
    assert _sessions(committed_db) == before


RALLY = {
    "type": "rally",
    "start_frame": 1800,
    "end_frame": 1900,
    "outcome": {"ending": "winner", "winning_side": "B", "responsible_player": "B1"},
}


@pytest.mark.parametrize(
    "raw",
    [
        # a bounce position is any pair of numbers to the label schema, so only the finite check
        # stands between NaN/Infinity and JSONB here
        b'{"type": "bounce", "frame": 1850, "court_xy_m": [NaN, 1.0]}',
        b'{"type": "bounce", "frame": 1850, "court_xy_m": [1.0, Infinity]}',
        b'{"type": "hit", "frame": NaN, "hitter": "B1"}',
    ],
    ids=["nan-in-bounce-position", "infinity-in-bounce-position", "nan-frame"],
)
def test_st_052c_a_non_finite_number_is_an_invalid_label_and_nothing_is_stored(
    api: ApiDriver, committed_db: Any, raw: bytes
) -> None:
    match_id = _consented(api, "ST-052c NaN", probed=True)
    rally = st.fulltag(api, "dana", "label_events", json_body=RALLY, match_id=match_id)
    assert rally.status_code == 201, rally.text
    before = _stored_labels(committed_db)
    _, template = st.FULLTAG_ROUTES["label_events"]
    response = api.request(
        "dana",
        "POST",
        template.format(match_id=match_id),
        content=raw,
        headers={"Content-Type": "application/json"},
    )
    assert st.refusal(response)[:2] == (422, "invalid_label"), response.text
    assert _stored_labels(committed_db) == before


def test_st_052c_the_session_has_the_probed_frame_grid_and_the_export_is_an_attachment(
    api: ApiDriver, committed_db: Any
) -> None:
    from racket.video_ingest.public import media_summary

    match_id = _consented(api, "ST-052c grid", probed=True)
    with Session(committed_db) as session:
        facts = media_summary(session, uuid.UUID(match_id)).facts
    assert facts is not None
    assert facts.fps == int(facts.fps)

    opened = st.fulltag(api, "dana", "label_match", match_id=match_id)
    assert opened.status_code == 200, opened.text
    assert opened.headers["cache-control"] == "no-store"
    body = opened.json()
    assert body["fps"] == int(facts.fps)
    assert body["frame_count"] == facts.duration_ms * int(facts.fps) // 1000
    assert body["players"] == ["A1", "A2", "B1", "B2"]
    assert body["version"] == 0

    export = st.fulltag(api, "dana", "label_export", match_id=match_id)
    assert export.status_code == 200, export.text
    assert export.headers["cache-control"] == "no-store"
    assert export.headers["content-disposition"] == (
        f'attachment; filename="labels-{match_id}.json"'
    )
    doc = export.json()
    assert st.LABEL_SCHEMA.load()(doc) == ()
    assert doc["clip"] == f"match:{match_id}"
    assert doc == body["document"]
