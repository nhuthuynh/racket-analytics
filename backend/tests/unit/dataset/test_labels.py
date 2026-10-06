"""Full Tag label schema v1 (ST-040, FR-150, FR-151; docs/data/gold-label-schema.md).

Pure domain: the label document arrives as parsed JSON data. Negative cases first.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from racket.dataset.labels import LABEL_SCHEMA, UnreadableLabels, validate_labels

pytestmark = pytest.mark.unit


def a_hit(frame: int, hitter: str = "A1", **facets: str) -> dict[str, Any]:
    return {"type": "hit", "frame": frame, "hitter": hitter, "facets": dict(facets)}


def a_bounce(frame: int, court_xy_m: list[float] | None = None) -> dict[str, Any]:
    return {"type": "bounce", "frame": frame, "visible": True, "court_xy_m": court_xy_m}


def a_rally(
    start: int = 10,
    end: int = 200,
    *,
    ending: str = "winner",
    winning_side: str | None = "A",
    responsible_player: str | None = "A1",
    fault_kind: str | None = None,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "id": f"r{start}",
        "start_frame": start,
        "end_frame": end,
        "outcome": {
            "ending": ending,
            "winning_side": winning_side,
            "responsible_player": responsible_player,
            "fault_kind": fault_kind,
        },
        "events": events if events is not None else [a_hit(20), a_bounce(45), a_hit(60, "B1")],
    }


def a_doc(**overrides: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "schema": LABEL_SCHEMA,
        "clip": "clips/c1.mp4",
        "fps": 60,
        "frame_count": 600,
        "players": ["A1", "A2", "B1", "B2"],
        "rallies": [a_rally()],
    }
    doc.update(overrides)
    return doc


def messages(doc: object) -> list[str]:
    return [p.describe() for p in validate_labels(doc)]


# --- negative cases first -------------------------------------------------------------


@pytest.mark.parametrize("doc", [None, [], "labels", 3])
def test_a_label_document_must_be_an_object(doc: object) -> None:
    assert messages(doc) == ["document: label document must be a JSON object"]


def test_an_unreadable_file_is_one_problem_naming_the_reason() -> None:
    assert messages(UnreadableLabels("Expecting value: line 1")) == [
        "document: label file is not valid JSON: Expecting value: line 1"
    ]


def test_wrong_schema_id_is_refused() -> None:
    assert messages(a_doc(schema="full-tag-labels/v0")) == [
        f"schema: must be {LABEL_SCHEMA!r}, got 'full-tag-labels/v0'"
    ]


@pytest.mark.parametrize("field", ["clip", "fps", "frame_count", "players", "rallies"])
def test_a_missing_top_level_field_is_named(field: str) -> None:
    doc = a_doc()
    del doc[field]
    assert f"{field}: required" in messages(doc)


@pytest.mark.parametrize("fps", [0, -30, True, "60", 60.5])
def test_fps_must_be_a_positive_integer(fps: object) -> None:
    assert "fps: must be a positive integer" in messages(a_doc(fps=fps))


@pytest.mark.parametrize(
    "players",
    [
        ["A1", "A2", "B1"],  # uneven sides
        ["A1", "A1", "B1", "B2"],  # duplicate slot
        ["A1", "C1"],  # unknown slot
        [],
        ["A3", "B1"],
    ],
)
def test_players_must_be_singles_or_doubles_slots(players: list[str]) -> None:
    assert "players: must be ['A1', 'B1'] (singles) or ['A1', 'A2', 'B1', 'B2'] (doubles)" in (
        messages(a_doc(players=players))
    )


def test_a_rally_must_start_before_it_ends() -> None:
    doc = a_doc(rallies=[a_rally(100, 100, events=[])])
    assert "rallies[0]: start_frame must be before end_frame" in messages(doc)


def test_a_rally_must_lie_inside_the_clip() -> None:
    doc = a_doc(rallies=[a_rally(500, 600, events=[])])
    assert "rallies[0].end_frame: must be within 0..599" in messages(doc)


def test_rallies_must_be_ordered_and_must_not_overlap() -> None:
    doc = a_doc(rallies=[a_rally(10, 200, events=[]), a_rally(150, 300, events=[])])
    assert "rallies[1]: starts before rallies[0] ends (overlap or out of order)" in messages(doc)


def test_an_event_outside_its_rally_is_named() -> None:
    doc = a_doc(rallies=[a_rally(10, 200, events=[a_hit(250)])])
    assert "rallies[0].events[0].frame: outside the rally (10..200)" in messages(doc)


def test_events_must_be_in_frame_order() -> None:
    doc = a_doc(rallies=[a_rally(events=[a_hit(60), a_bounce(45)])])
    assert "rallies[0].events[1].frame: events must be in frame order" in messages(doc)


def test_two_hits_on_the_same_frame_are_refused() -> None:
    doc = a_doc(rallies=[a_rally(events=[a_hit(60), a_hit(60, "B1")])])
    assert "rallies[0].events[1].frame: two hits on one frame" in messages(doc)


def test_unknown_event_type_is_refused() -> None:
    doc = a_doc(rallies=[a_rally(events=[{"type": "net", "frame": 20}])])
    assert "rallies[0].events[0].type: must be one of ['bounce', 'hit']" in messages(doc)


def test_hitter_must_be_a_player_of_the_clip() -> None:
    doc = a_doc(players=["A1", "B1"], rallies=[a_rally(events=[a_hit(20, "A2")])])
    assert "rallies[0].events[0].hitter: 'A2' is not one of ['A1', 'B1']" in messages(doc)


def test_position_is_derived_and_must_not_be_labelled() -> None:
    doc = a_doc(rallies=[a_rally(events=[a_hit(20, position="serve")])])
    assert (
        "rallies[0].events[0].facets.position: derived by rule, never labelled (QD-TX-01)"
        in messages(doc)
    )


@pytest.mark.parametrize(
    ("facet", "value"),
    [("trajectory", "smash"), ("intent", "attack"), ("technique", "tweener"), ("contact", "half")],
)
def test_facet_values_come_from_the_taxonomy(facet: str, value: str) -> None:
    doc = a_doc(rallies=[a_rally(events=[a_hit(20, **{facet: value})])])
    found = [m for m in messages(doc) if m.startswith(f"rallies[0].events[0].facets.{facet}:")]
    assert found
    assert f"{value!r} is not one of" in found[0]


def test_unknown_facet_is_refused() -> None:
    doc = a_doc(rallies=[a_rally(events=[a_hit(20, spin="top")])])
    assert "rallies[0].events[0].facets.spin: unknown facet" in messages(doc)


def test_bounce_position_must_be_two_metres_values_or_null() -> None:
    doc = a_doc(rallies=[a_rally(events=[a_bounce(20, court_xy_m=[1.0])])])
    assert "rallies[0].events[0].court_xy_m: must be [x, y] in metres or null" in messages(doc)


@pytest.mark.parametrize("ending", ["let", "", None])
def test_ending_comes_from_the_match_aggregate_list(ending: object) -> None:
    doc = a_doc(rallies=[a_rally(ending=ending, events=[])])  # type: ignore[arg-type]
    assert any(m.startswith("rallies[0].outcome.ending: must be one of") for m in messages(doc))


def test_replay_has_no_winning_side() -> None:
    doc = a_doc(rallies=[a_rally(ending="replay", winning_side="A", responsible_player=None)])
    assert "rallies[0].outcome.winning_side: must be null for a replay" in messages(doc)


def test_a_counted_rally_needs_a_winning_side() -> None:
    doc = a_doc(rallies=[a_rally(winning_side=None, responsible_player=None)])
    assert "rallies[0].outcome.winning_side: must be 'A' or 'B'" in messages(doc)


@pytest.mark.parametrize(
    ("ending", "responsible", "expected_side"),
    [
        ("winner", "B1", "winning"),
        ("unforced_error", "A1", "losing"),
        ("forced_error", "A2", "losing"),
        ("fault", "A1", "losing"),
    ],
)
def test_responsible_player_is_on_the_side_match_aggregate_names(
    ending: str, responsible: str, expected_side: str
) -> None:
    doc = a_doc(rallies=[a_rally(ending=ending, winning_side="A", responsible_player=responsible)])
    assert (
        f"rallies[0].outcome.responsible_player: must be on the {expected_side} side for {ending}"
        in messages(doc)
    )


def test_fault_kind_only_for_a_fault() -> None:
    doc = a_doc(rallies=[a_rally(ending="winner", fault_kind="foot_fault")])
    assert "rallies[0].outcome.fault_kind: only for a fault" in messages(doc)


def test_fault_kind_comes_from_the_sport_list() -> None:
    doc = a_doc(
        rallies=[
            a_rally(ending="fault", winning_side="B", responsible_player="A1", fault_kind="net")
        ]
    )
    assert any(m.startswith("rallies[0].outcome.fault_kind: must be one of") for m in messages(doc))


def test_problems_are_listed_together_not_only_the_first() -> None:
    doc = a_doc(fps=0, rallies=[a_rally(events=[a_hit(20, "C9")])])
    assert len(messages(doc)) >= 2


def test_nested_garbage_is_reported_not_raised() -> None:
    doc = a_doc(rallies=[None, {"events": "x"}, a_rally(events=[None])])
    assert messages(doc)  # no exception, problems listed


# --- contract with Match & Scoring and the sport plug-in -------------------------------


def test_endings_and_fault_kinds_match_the_scoring_vocabulary() -> None:
    from racket.dataset.labels import ENDINGS, FAULT_KINDS
    from racket.matches.scorebook.domain.values import ENDINGS as SCORING_ENDINGS
    from racket.sports.pickleball.rules.config import FaultKind

    assert set(ENDINGS) == set(SCORING_ENDINGS)
    assert set(FAULT_KINDS) == {k.value for k in FaultKind}


# --- positive cases ---------------------------------------------------------------------


def test_a_valid_doubles_document_has_no_problems() -> None:
    doc = a_doc(
        rallies=[
            a_rally(
                events=[
                    a_hit(20, "A1", trajectory="drive", contact="groundstroke"),
                    a_bounce(45, court_xy_m=[3.1, 12.4]),
                    a_hit(60, "B2", trajectory="dink", intent="reset", technique="none"),
                ]
            ),
            a_rally(
                300,
                420,
                ending="fault",
                winning_side="B",
                responsible_player="A2",
                fault_kind="nvz",
                events=[a_hit(310, "A2")],
            ),
            a_rally(
                450, 500, ending="replay", winning_side=None, responsible_player=None, events=[]
            ),
        ]
    )
    assert messages(doc) == []


def test_a_valid_singles_document_has_no_problems() -> None:
    doc = a_doc(players=["A1", "B1"], rallies=[a_rally(events=[a_hit(20), a_hit(60, "B1")])])
    assert messages(doc) == []


def test_responsible_player_is_optional() -> None:
    doc = a_doc(
        rallies=[a_rally(ending="unforced_error", winning_side="A", responsible_player=None)]
    )
    assert messages(doc) == []


def test_validation_does_not_change_the_document() -> None:
    doc = a_doc()
    before = copy.deepcopy(doc)
    validate_labels(doc)
    assert doc == before
