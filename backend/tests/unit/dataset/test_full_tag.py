"""Full Tag access, consent record and label session (ST-052; FR-150, FR-151). Pure domain.

TDD order of sprint-03 §5, negative cases first:
``FullTagAccess``: a player -> not available (the API answers 404); a labeller on a match
without a consent record -> refused, told why; a labeller with consent -> allowed.
``LabelExport``: a label with an unknown player -> refused; a frame out of range -> refused;
the export validates against ``full-tag-labels/v1`` and contains the tagged frame and player.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from racket.dataset.full_tag import (
    Access,
    ConsentRecord,
    ExportInvalid,
    FullTagSession,
    InvalidConsent,
    LabelRefused,
    decide_access,
)
from racket.dataset.labels import validate_labels

pytestmark = pytest.mark.unit

AT = datetime(2026, 10, 7, 9, 0, tzinfo=UTC)
CLIP = {"clip": "match:7b1f", "fps": 60, "frame_count": 3600, "players": ("A1", "A2", "B1", "B2")}
HIT = {"type": "hit", "frame": 1840, "hitter": "B1"}
RALLY = {
    "type": "rally",
    "start_frame": 1800,
    "end_frame": 1900,
    "outcome": {"ending": "winner", "winning_side": "B", "responsible_player": "B1",
                "fault_kind": None},
}  # fmt: skip


def consent(match_id: str = "m-1") -> ConsentRecord:
    return ConsentRecord.create(match_id, "CONSENT-TEAM-SYNTHETIC-001", "acct-9f2", AT)


def session(*bodies: dict[str, Any]) -> FullTagSession:
    s = FullTagSession(**CLIP)
    for body in bodies:
        s = s.add(body)
    return s


# --------------------------------------------------------------- FullTagAccess
def test_a_player_is_told_full_tag_is_not_available_even_on_a_consented_match() -> None:
    assert (
        decide_access(is_labeller=False, match_id="m-1", consent=consent()) is Access.NOT_AVAILABLE
    )
    assert decide_access(is_labeller=False, match_id="m-1", consent=None) is Access.NOT_AVAILABLE


def test_a_labeller_on_a_match_without_a_consent_record_is_refused() -> None:
    assert decide_access(is_labeller=True, match_id="m-1", consent=None) is Access.NO_CONSENT


def test_a_consent_record_for_another_match_does_not_count() -> None:
    other = consent("m-2")
    assert decide_access(is_labeller=True, match_id="m-1", consent=other) is Access.NO_CONSENT


def test_a_labeller_with_consent_is_allowed() -> None:
    assert decide_access(is_labeller=True, match_id="m-1", consent=consent()) is Access.ALLOWED


# --------------------------------------------------------------- consent record
@pytest.mark.parametrize(
    "reference",
    ["", "ivy@example.com", "Ivy Smith", "x" * 65, "CONSENT\n001", "-leading-dash"],
)
def test_a_consent_reference_that_could_carry_a_name_or_address_is_refused(reference: str) -> None:
    with pytest.raises(InvalidConsent):
        ConsentRecord.create("m-1", reference, "acct-9f2", AT)


def test_a_consent_record_needs_a_match_a_recorder_and_an_aware_time() -> None:
    with pytest.raises(InvalidConsent):
        ConsentRecord.create("", "CONSENT-1", "acct-9f2", AT)
    with pytest.raises(InvalidConsent):
        ConsentRecord.create("m-1", "CONSENT-1", "", AT)
    with pytest.raises(InvalidConsent):
        ConsentRecord.create("m-1", "CONSENT-1", "acct-9f2", datetime(2026, 10, 7))


def test_a_valid_consent_record_keeps_its_fields() -> None:
    record = consent()
    assert (record.match_id, record.reference, record.recorded_by, record.recorded_at) == (
        "m-1", "CONSENT-TEAM-SYNTHETIC-001", "acct-9f2", AT,
    )  # fmt: skip


# --------------------------------------------------------------- label commands
@pytest.mark.parametrize(
    ("body", "why"),
    [
        ({**HIT, "hitter": "C9"}, "hitter"),
        ({**HIT, "frame": 18_402}, "outside the clip"),
        ({**HIT, "frame": -1}, "frame"),
        ({**HIT, "frame": True}, "frame"),
        ({**HIT, "type": "smash"}, "type"),
        ({**HIT, "note": "Ivy"}, "unknown field"),
        ({**HIT, "facets": {"position": "kitchen"}}, "derived"),
        ("hit", "object"),
    ],
    ids=["unknown-player", "beyond-clip", "negative", "bool-frame", "unknown-type",
         "extra-field", "derived-facet", "not-an-object"],
)  # fmt: skip
def test_an_invalid_event_is_refused_and_the_session_is_unchanged(body: Any, why: str) -> None:
    before = session(RALLY)
    with pytest.raises(LabelRefused) as refused:
        before.add(body)
    assert why in str(refused.value)
    assert before.export() == session(RALLY).export()


def test_an_event_outside_every_rally_is_refused() -> None:
    with pytest.raises(LabelRefused, match="no rally contains frame 1840"):
        session().add(HIT)


def test_two_hits_on_one_frame_are_refused() -> None:
    with pytest.raises(LabelRefused, match="two hits on one frame"):
        session(RALLY, HIT).add({**HIT, "hitter": "A1"})


@pytest.mark.parametrize(
    "rally",
    [
        {**RALLY, "start_frame": 1900, "end_frame": 1800},
        {**RALLY, "end_frame": 3600},
        {**RALLY, "outcome": {**RALLY["outcome"], "responsible_player": "A1"}},
    ],
    ids=["reversed", "end-beyond-clip", "responsible-on-wrong-side"],
)
def test_an_invalid_rally_is_refused(rally: dict[str, Any]) -> None:
    with pytest.raises(LabelRefused):
        session().add(rally)


def test_an_overlapping_rally_is_refused() -> None:
    with pytest.raises(LabelRefused, match="overlap"):
        session(RALLY).add({**RALLY, "start_frame": 1850, "end_frame": 1950})


def test_a_second_rally_elsewhere_keeps_the_first_rallys_events() -> None:
    later = {**RALLY, "start_frame": 1000, "end_frame": 1100}
    doc = session(RALLY, HIT, later).export()
    assert [len(r["events"]) for r in doc["rallies"]] == [0, 1]


# --------------------------------------------------------------- export
def test_the_export_validates_and_contains_the_tagged_frame_and_player() -> None:
    doc = session(RALLY, HIT).export()
    assert validate_labels(doc) == ()
    assert doc["schema"] == "full-tag-labels/v1"
    assert doc["rallies"][0]["events"] == [{"type": "hit", "frame": 1840, "hitter": "B1",
                                            "facets": {}}]  # fmt: skip


def test_the_export_orders_rallies_and_events_by_frame_and_numbers_rallies() -> None:
    bounce = {"type": "bounce", "frame": 1820, "visible": True, "court_xy_m": None}
    early = {**RALLY, "start_frame": 100, "end_frame": 200,
             "outcome": {"ending": "replay", "winning_side": None, "responsible_player": None,
                         "fault_kind": None}}  # fmt: skip
    doc = session(RALLY, HIT, bounce, early).export()
    assert [r["id"] for r in doc["rallies"]] == ["r1", "r2"]
    assert [r["start_frame"] for r in doc["rallies"]] == [100, 1800]
    assert [e["frame"] for e in doc["rallies"][1]["events"]] == [1820, 1840]
    assert validate_labels(doc) == ()


def test_an_empty_session_exports_a_valid_empty_document() -> None:
    doc = session().export()
    assert doc["rallies"] == []
    assert validate_labels(doc) == ()


def test_a_clip_that_is_not_singles_or_doubles_cannot_be_exported() -> None:
    with pytest.raises(ExportInvalid):
        FullTagSession(clip="match:1", fps=60, frame_count=10, players=("A1",)).export()


# --------------------------------------------------------------- aliasing (PE-052a-1, BE-R1-1)
# The session owns its state: a caller that keeps a reference to what it passed in, or to what
# an export returned, cannot change an accepted session. Negative cases: each edit below would
# make the export invalid if it reached the session.
def _bounce_with_xy() -> dict[str, Any]:
    return {"type": "bounce", "frame": 1820, "visible": True, "court_xy_m": [1.5, 3.0]}


def test_editing_a_rally_body_after_add_does_not_change_the_session() -> None:
    rally = {**RALLY, "outcome": dict(RALLY["outcome"])}
    s = session(rally)
    rally["outcome"]["responsible_player"] = "Q7"
    rally["end_frame"] = -1
    assert validate_labels(s.export()) == ()
    assert s.export()["rallies"][0]["outcome"]["responsible_player"] == "B1"


def test_editing_an_event_body_after_add_does_not_change_the_session() -> None:
    hit = {**HIT, "facets": {"contact": "volley"}}
    bounce = _bounce_with_xy()
    s = session(RALLY, hit, bounce)
    hit["facets"]["position"] = "kitchen"
    hit["hitter"] = "Z9"
    bounce["court_xy_m"].append(9.9)
    events = s.export()["rallies"][0]["events"]
    assert events[1] == {"type": "hit", "frame": 1840, "hitter": "B1",
                         "facets": {"contact": "volley"}}  # fmt: skip
    assert events[0]["court_xy_m"] == [1.5, 3.0]


def test_editing_an_export_does_not_change_the_session() -> None:
    s = session(RALLY, HIT, _bounce_with_xy())
    doc = s.export()
    doc["rallies"][0]["events"][1]["hitter"] = "Z9"
    doc["rallies"][0]["events"][1]["facets"]["position"] = "kitchen"
    doc["rallies"][0]["events"][0]["court_xy_m"][0] = "x"
    doc["rallies"][0]["outcome"]["responsible_player"] = "Q7"
    doc["rallies"][0]["events"].clear()
    doc["players"].append("C1")
    again = s.export()
    assert validate_labels(again) == ()
    assert again == session(RALLY, HIT, _bounce_with_xy()).export()


def test_a_session_keeps_no_reference_to_the_callers_objects() -> None:
    hit = {**HIT, "facets": {"contact": "volley"}}
    s = session(RALLY, hit)
    assert all(e is not hit and e["facets"] is not hit["facets"] for e in s.events)
    assert all(r is not RALLY and r["outcome"] is not RALLY["outcome"] for r in s.rallies)
