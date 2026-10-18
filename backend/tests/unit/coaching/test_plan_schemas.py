"""Request and response schemas of the plan API (ST-061b; api-sprint-04 §2.1, §2.3).

``parse_preferences`` turns a JSON body into ``Preferences`` or refuses it with one closed field
code per field (``required``, ``invalid``, ``out_of_range``, ``unknown_value``, ``duplicate``,
``unknown_field`` with ``field: null``), never echoing input. ``plan_body`` renders a saved,
cited plan as the §2.3 representation. Negative cases first.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from racket.coaching.plan.domain import CitedPlan, TrainingPlan, assemble
from racket.coaching.plan.repository import StoredPlan, StoredSession
from racket.coaching.schemas import UNOFFICIAL_LABEL, PlanView, parse_preferences, plan_body
from racket.coaching.weakness.domain import RallyLoss, rank
from racket.platform.errors import FieldError, ValidationFailed
from tests.unit.coaching.citation_helpers import all_citations
from tests.unit.coaching.plan_helpers import TOP_3, reviewed_test_library, solo_wall

pytestmark = pytest.mark.unit

VALID: dict[str, Any] = {
    "minutes_per_session": 30,
    "sessions_per_week": 3,
    "players_available": 1,
    "equipment": ["wall"],
    "level": "intermediate",
}


def refused(body: Any) -> list[tuple[str | None, str]]:
    with pytest.raises(ValidationFailed) as caught:
        parse_preferences(body)
    return [(f.field, f.code) for f in caught.value.fields]


# ------------------------------------------------------------------ refusals
@pytest.mark.parametrize("body", [None, [], "x", 3, True], ids=repr)
def test_a_body_that_is_not_an_object_is_invalid(body: Any) -> None:
    assert refused(body) == [(None, "invalid")]


def test_every_missing_required_field_is_named_in_table_order() -> None:
    assert refused({}) == [
        ("minutes_per_session", "required"),
        ("sessions_per_week", "required"),
        ("players_available", "required"),
        ("equipment", "required"),
        ("level", "required"),
    ]


def test_an_unknown_key_is_reported_without_its_name_and_first() -> None:
    fields = refused(VALID | {"account_id": "x", "version": 2, "level": "pro"})
    assert fields == [(None, "unknown_field"), ("level", "unknown_value")]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("minutes_per_session", "30"),
        ("minutes_per_session", 30.5),
        ("minutes_per_session", True),
        ("minutes_per_session", None),
        ("sessions_per_week", [3]),
        ("players_available", False),
        ("weekly_minutes", "90"),
        ("equipment", "wall"),
        ("equipment", ["wall", 3]),
        ("level", 2),
    ],
    ids=lambda v: repr(v),
)
def test_a_wrong_json_type_is_invalid(field: str, value: Any) -> None:
    assert refused(VALID | {field: value}) == [(field, "invalid")]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("minutes_per_session", 14),
        ("minutes_per_session", 181),
        ("sessions_per_week", 0),
        ("sessions_per_week", 8),
        ("players_available", 0),
        ("players_available", 5),
        ("weekly_minutes", 44),  # < 3 sessions x 15
        ("weekly_minutes", 1261),  # > 7 x 180 (judgment: no budget uses more)
        ("weekly_minutes", 10**40),
    ],
    ids=lambda v: repr(v),
)
def test_a_number_outside_its_range_is_out_of_range(field: str, value: int) -> None:
    assert refused(VALID | {field: value}) == [(field, "out_of_range")]


@pytest.mark.parametrize(
    ("sessions", "weekly", "want"),
    [
        (8, 100, [("sessions_per_week", "out_of_range")]),  # not 8 x 15 = 120 > 100
        ("3", 30, [("sessions_per_week", "invalid")]),
        (True, 30, [("sessions_per_week", "invalid")]),
        (0, 10, [("sessions_per_week", "out_of_range"), ("weekly_minutes", "out_of_range")]),
    ],
    ids=["too-many", "string", "bool", "zero-and-below-one-session"],
)
def test_the_weekly_floor_uses_sessions_per_week_only_when_it_is_valid(
    sessions: Any, weekly: int, want: list[tuple[str, str]]
) -> None:
    """QA-ST061b-R1-02/R2-01: an invalid ``sessions_per_week`` gets its own code and the
    ``weekly_minutes`` floor falls back to one session (15), so no spurious code is added."""
    assert refused(VALID | {"sessions_per_week": sessions, "weekly_minutes": weekly}) == want


def test_unknown_and_duplicate_equipment_and_an_unknown_level_are_named() -> None:
    assert refused(VALID | {"equipment": ["trampoline"]}) == [("equipment", "unknown_value")]
    assert refused(VALID | {"equipment": ["wall", "wall"]}) == [("equipment", "duplicate")]
    assert refused(VALID | {"level": "pro"}) == [("level", "unknown_value")]


def test_several_bad_fields_give_one_entry_each_and_never_echo_input() -> None:
    body = VALID | {"minutes_per_session": 10, "sessions_per_week": 8, "equipment": ["<script>"]}
    with pytest.raises(ValidationFailed) as caught:
        parse_preferences(body)
    assert caught.value.fields == (
        FieldError("minutes_per_session", "out_of_range"),
        FieldError("sessions_per_week", "out_of_range"),
        FieldError("equipment", "unknown_value"),
    )
    assert "<script>" not in str(caught.value)


# ------------------------------------------------------------------ accepted
@pytest.mark.parametrize(
    "edge",
    [
        {"minutes_per_session": 15, "sessions_per_week": 1, "players_available": 1},
        {"minutes_per_session": 180, "sessions_per_week": 7, "players_available": 4},
        {"weekly_minutes": 45},
        {"weekly_minutes": 1260},
        {"weekly_minutes": None},
        {"equipment": []},
    ],
    ids=repr,
)
def test_the_range_edges_are_accepted(edge: dict[str, Any]) -> None:
    prefs = parse_preferences(VALID | edge)
    assert prefs.minutes_per_session == (VALID | edge)["minutes_per_session"]
    assert prefs.weekly_minutes == (VALID | edge).get("weekly_minutes")


def test_a_valid_body_becomes_preferences() -> None:
    body = VALID | {"equipment": ["wall", "ball_machine"], "weekly_minutes": 80}
    prefs = parse_preferences(body)
    assert prefs.equipment == frozenset({"wall", "ball_machine"})
    assert (prefs.weekly_total, prefs.minutes_budget, prefs.level) == (80, 26, "intermediate")


# ------------------------------------------------------------------ the plan representation
def _view(*, regenerated: str | None = None) -> PlanView:
    plan = assemble(TOP_3, solo_wall(), reviewed_test_library(), "lib-1")
    assert isinstance(plan, TrainingPlan)
    cited = CitedPlan(plan, all_citations(low_top=True), rallies=13)
    match = uuid.uuid4()
    losses = [
        RallyLoss(match, f"r{i}", (match, 1), "serve" if i < 2 else "receive", cat, i == 0, None)
        for i, cat in enumerate(["unforced_errors", "unforced_errors", "serve_faults"])
    ]
    ranking = rank(losses, 3, rallies=13)
    stored = StoredPlan(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        stale=False,
        plan=plan,
        created_at=datetime(2026, 10, 17, 9, 0, tzinfo=UTC),
        sessions=tuple(
            StoredSession(uuid.uuid4(), None, tuple(uuid.uuid4() for _ in s.assignments))
            for s in plan.sessions
        ),
    )
    names = {d.ref: f"Name of {d.id}" for d in reviewed_test_library()}
    return PlanView(stored, ranking, cited, names, regenerated)


def test_a_view_whose_ids_do_not_match_the_plan_is_refused() -> None:
    view = _view()
    short = StoredPlan(view.stored.id, view.stored.owner_id, False, view.stored.plan)
    with pytest.raises(ValueError, match="ids"):
        plan_body(PlanView(short, view.ranking, view.cited, view.drill_names, None))


def test_the_body_has_the_contract_keys_and_honesty_flags() -> None:
    view = _view()
    body = plan_body(view)
    assert set(body) == {
        "id", "version", "created_at", "content_digest", "library_version", "regenerated",
        "unofficial", "label", "drills_verified", "preferences", "ranking", "limited_data",
        "unfitted", "sessions",
    }  # fmt: skip
    assert (body["id"], body["version"]) == (str(view.stored.id), 1)
    assert body["created_at"] == "2026-10-17T09:00:00Z"
    assert body["content_digest"] == view.cited.content_digest()
    assert (body["library_version"], body["regenerated"]) == ("lib-1", None)
    assert (body["unofficial"], body["label"]) == (True, UNOFFICIAL_LABEL)
    assert body["drills_verified"] is False  # test drills are coach-reviewed, not verified
    assert body["limited_data"] == {"rallies": 13}
    assert body["preferences"] == VALID | {"weekly_minutes": 90}
    assert plan_body(_view(regenerated="source_match_deleted"))["regenerated"] == (
        "source_match_deleted"
    )


def test_the_ranking_is_in_rallies_lost_per_game_rounded_to_2_places() -> None:
    ranking = plan_body(_view())["ranking"]
    assert {k: ranking[k] for k in ("unit", "side_out_verified", "games", "rallies")} == {
        "unit": "rallies_lost_per_game",
        "side_out_verified": False,
        "games": 3,
        "rallies": 13,
    }
    assert ranking["skipped_matches"] == 0
    assert ranking["weaknesses"] == [
        {"id": "unforced_errors", "name": "Unforced errors", "metric_id": "AN-04", "rank": 1,
         "per_game": 0.67, "on_serve_per_game": 0.67, "on_receive_per_game": 0.0,
         "conceded_per_game": 0.33},
        {"id": "serve_faults", "name": "Serve faults", "metric_id": "AN-07", "rank": 2,
         "per_game": 0.33, "on_serve_per_game": 0.0, "on_receive_per_game": 0.33,
         "conceded_per_game": 0.0},
    ]  # fmt: skip


def test_sessions_carry_their_ids_drills_minutes_and_citations() -> None:
    view = _view()
    body = plan_body(view)
    assert len(body["sessions"]) == len(view.stored.plan.sessions) == 6
    for s, stored, domain in zip(
        body["sessions"], view.stored.sessions, view.stored.plan.sessions, strict=True
    ):
        assert (s["id"], s["week"], s["index"]) == (str(stored.id), domain.week, domain.index)
        assert (s["minutes_budget"], s["done"], s["done_at"]) == (30, False, None)
        assert [a["id"] for a in s["assignments"]] == [str(i) for i in stored.assignment_ids]
        for a, x in zip(s["assignments"], domain.assignments, strict=True):
            assert (a["position"], a["minutes"]) == (x.position, x.minutes)
            assert a["drill"] == {
                "id": x.drill.id, "version": x.drill.version, "name": f"Name of {x.drill.id}",
                "players": x.drill.players, "needs": sorted(x.drill.needs),
                "skills": sorted(x.drill.skills),
            }  # fmt: skip
            assert (a["weakness_id"], a["warm_up"]) == (x.weakness_id, x.position == 1)
            c = a["citation"]
            assert set(c) == {"metric_id", "metric_version", "side", "value", "n", "k",
                              "low_sample", "rally_ids", "evidence"}  # fmt: skip
            assert c["side"] == "A"
            assert c["evidence"] == [{"match_id": "m1", "side": "A", "n": len(c["rally_ids"])}]
            assert all(r.startswith("m1-r") for r in c["rally_ids"])
            assert a["why"]


def test_values_are_rounded_proportions_4_places_per_game_2() -> None:
    body = plan_body(_view())
    cited = {
        a["citation"]["metric_id"]: a["citation"]
        for s in body["sessions"]
        for a in s["assignments"]
    }
    assert (cited["AN-04"]["value"], cited["AN-04"]["n"]) == (2.0, 1)
    if "AN-05" in cited:
        assert cited["AN-05"]["value"] == round(2 / 7, 4)
