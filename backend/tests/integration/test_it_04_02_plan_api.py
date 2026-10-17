"""IT-04-02 (ST-061b; FR-120..FR-123; NFR-019; api-sprint-04 §2): ``POST``/``GET /me/plan`` over
HTTP on Postgres, the real drill library (``content/drills``) and matches tagged through the API.

The plan body is checked against the QA harness's independent reference
(``scripts/measure/planlib.py``: ranking, QD-PL-01..04 grader, citations = GET stats and
GET evidence), which imports nothing from ``racket.coaching``. Negative cases first; a refusal
writes no plan row. NFR-019: generation p95 <= 5 s, measured here on three tagged matches.
"""

from __future__ import annotations

import math
import time
import uuid
from typing import Any

import httpx
import pytest
import sqlalchemy as sa

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver
from tests.support.paths import REPO

pytestmark = [pytest.mark.integration, pytest.mark.coaching]

planlib = sb._load("planlib")
PLAN = "/me/plan"
SOLO_WALL = {
    "minutes_per_session": 30,
    "sessions_per_week": 3,
    "players_available": 1,
    "equipment": ["wall"],
    "level": "intermediate",
}
NOTHING_FITS = SOLO_WALL | {"equipment": [], "level": "advanced"}
GENERATIONS = 20  # NFR-019 sample
NFR_019_P95_S = 5.0


def _plans(engine: Any) -> int:
    with engine.connect() as conn:
        return int(conn.execute(sa.text("SELECT count(*) FROM training_plans")).scalar_one())


def _post(api: ApiDriver, user: str, body: Any = None) -> httpx.Response:
    return api.request(user, "POST", PLAN, json=SOLO_WALL if body is None else body)


def _created(api: ApiDriver, user: str, body: Any = None) -> dict[str, Any]:
    response = _post(api, user, body)
    assert response.status_code == 201, response.text
    plan: dict[str, Any] = response.json()
    return plan


def _evidence(api: ApiDriver, match_id: str) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for metric in st.METRICS:
        url = f"/matches/{match_id}/stats/{metric}/evidence?side=A&limit=10"
        found[metric], cursor = set(), ""
        while cursor is not None:
            response = api.request("ivy", "GET", url + (f"&cursor={cursor}" if cursor else ""))
            assert response.status_code == 200, response.text
            found[metric] |= {item["rally_id"] for item in response.json()["items"]}
            cursor = response.json()["next_cursor"]
    return found


def _ids(plan: dict[str, Any]) -> list[str]:
    return [plan["id"]] + [
        x["id"] for s in plan["sessions"] for x in [s, *s["assignments"]]
    ]


# ------------------------------------------------------------------ refusals (negative first)
def test_it_04_02_no_tagged_match_is_409_with_the_reason_and_writes_nothing(
    api: ApiDriver, committed_db: Any
) -> None:
    response = _post(api, "ivy")
    assert st.refusal(response) == (409, "no_tagged_match", [])
    assert response.json()["error"]["message"] == "Tag at least one match to get a plan."
    sb.ready_match(api, "ivy", "IT-04-02 untagged")  # video received, no rally tagged
    assert st.refusal(_post(api, "ivy"))[:2] == (409, "no_tagged_match")
    assert st.refusal(api.request("ivy", "GET", PLAN))[:2] == (404, "no_plan")
    assert _plans(committed_db) == 0


def test_it_04_02_no_session_is_401_on_both_routes(api: ApiDriver, committed_db: Any) -> None:
    assert api.request("anonymous", "POST", PLAN, json=SOLO_WALL).status_code == 401
    assert api.request("anonymous", "GET", PLAN).status_code == 401
    assert _plans(committed_db) == 0


@pytest.mark.parametrize(
    ("body", "fields"),
    [
        ({k: v for k, v in SOLO_WALL.items() if k != "level"}, [("level", "required")]),
        (SOLO_WALL | {"minutes_per_session": "30"}, [("minutes_per_session", "invalid")]),
        (SOLO_WALL | {"players_available": 5}, [("players_available", "out_of_range")]),
        (SOLO_WALL | {"equipment": ["wall", "wall"]}, [("equipment", "duplicate")]),
        (SOLO_WALL | {"weekly_minutes": 44}, [("weekly_minutes", "out_of_range")]),
        (SOLO_WALL | {"account_id": str(uuid.uuid4())}, [(None, "unknown_field")]),
        (["not", "an", "object"], [(None, "invalid")]),
    ],
    ids=["missing", "wrong-type", "range", "duplicate", "weekly", "unknown-key", "not-object"],
)
def test_it_04_02_bad_preferences_are_422_with_field_codes_and_write_nothing(
    api: ApiDriver, committed_db: Any, body: Any, fields: list[tuple[Any, str]]
) -> None:
    st.tagged_example(api, "ivy", "IT-04-02 422")
    response = _post(api, "ivy", body)
    assert st.refusal(response) == (422, "validation_failed", fields)
    assert "account_id" not in response.text  # an unknown key is never echoed (T4-PL-8)
    assert _plans(committed_db) == 0


def test_it_04_02_no_plan_fits_is_409_and_writes_nothing(
    api: ApiDriver, committed_db: Any
) -> None:
    st.tagged_example(api, "ivy", "IT-04-02 nothing fits")
    response = _post(api, "ivy", NOTHING_FITS)
    assert st.refusal(response) == (409, "no_plan_fits", [])
    assert _plans(committed_db) == 0


def test_it_04_02_the_31st_generation_in_an_hour_is_429_and_writes_nothing(
    api: ApiDriver, committed_db: Any
) -> None:
    """SEC-S4-TM-01 (T4-PL-6): 30 generations per account per hour, counted after validation."""
    for _ in range(30):
        assert st.refusal(_post(api, "ivy"))[:2] == (409, "no_tagged_match")
    assert st.refusal(_post(api, "ivy", {"level": "pro"}))[0] == 422  # a 422 spends no slot
    response = _post(api, "ivy")
    assert st.refusal(response)[:2] == (429, "rate_limited")
    assert response.json()["error"]["retry_at"].endswith("Z")
    assert int(response.headers["retry-after"]) >= 1
    assert st.refusal(_post(api, "carlos"))[:2] == (409, "no_tagged_match")  # per account
    assert _plans(committed_db) == 0


# ------------------------------------------------------------------ the plan
@pytest.mark.needs_verification
def test_it_04_02_a_plan_from_the_worked_example_equals_the_independent_reference(
    api: ApiDriver, committed_db: Any
) -> None:
    match_id = st.tagged_example(api, "ivy", "IT-04-02 worked example")
    response = _post(api, "ivy")
    assert response.status_code == 201, response.text
    assert response.headers["location"] == PLAN
    plan = response.json()
    library = planlib.load_library(REPO / "content" / "drills")
    want = planlib.ranking([{"first_serving_side": "A", "tags": st.WORKED_EXAMPLE}], "A")
    assert planlib.ranking_problems(want, plan["ranking"]) == []
    assert planlib.grade(plan, library) == []
    stats = st.stats_body(api, "ivy", match_id)
    evidence = _evidence(api, match_id)
    assert planlib.citation_problems(plan, stats, "A", evidence, library) == []
    assert (plan["unofficial"], plan["label"], plan["drills_verified"]) == (
        True,
        st.UNOFFICIAL,
        False,
    )
    assert plan["ranking"]["unit"] == "rallies_lost_per_game"
    assert plan["ranking"]["side_out_verified"] is False
    assert plan["limited_data"] == {"rallies": 13}
    assert plan["preferences"] == SOLO_WALL | {"weekly_minutes": 90}
    assert (plan["version"], plan["regenerated"]) == (1, None)
    assert plan["content_digest"].startswith("sha256:")
    for a in (a for s in plan["sessions"] for a in s["assignments"]):
        assert a["citation"]["evidence"] == [
            {"match_id": match_id, "side": "A", "n": a["citation"]["evidence"][0]["n"]}
        ]
        assert set(a["citation"]["rally_ids"]) <= evidence[a["citation"]["metric_id"]]
    assert _plans(committed_db) == 1


def test_it_04_02_get_reads_the_saved_plan_with_stable_ids(
    api: ApiDriver, committed_db: Any
) -> None:
    st.tagged_example(api, "ivy", "IT-04-02 read back")
    plan = _created(api, "ivy")
    for _ in range(2):
        response = api.request("ivy", "GET", PLAN)
        assert response.status_code == 200, response.text
        assert response.json() == plan
    ids = _ids(plan)
    assert len(set(ids)) == len(ids) and all(uuid.UUID(i).version == 4 for i in ids)


def test_it_04_02_a_new_post_replaces_the_plan_and_the_same_input_gives_the_same_content(
    api: ApiDriver, committed_db: Any
) -> None:
    st.tagged_example(api, "ivy", "IT-04-02 replace")
    first, again = _created(api, "ivy"), _created(api, "ivy")
    assert again["content_digest"] == first["content_digest"]
    assert set(_ids(again)).isdisjoint(_ids(first))
    other = _created(api, "ivy", SOLO_WALL | {"minutes_per_session": 45, "sessions_per_week": 2})
    assert len(other["sessions"]) == 4 and other["content_digest"] != first["content_digest"]
    assert api.request("ivy", "GET", PLAN).json() == other
    assert _plans(committed_db) == 1


def test_it_04_02_another_account_never_sees_or_cites_the_players_data(
    api: ApiDriver, committed_db: Any
) -> None:
    """T4-PL-2 / NFR-051: Carlos's GET is 404; each plan cites only its owner's matches."""
    ivy_match = st.tagged_example(api, "ivy", "IT-04-02 Ivy")
    ivy = _created(api, "ivy")
    response = api.request("carlos", "GET", PLAN)
    assert st.refusal(response)[:2] == (404, "no_plan")
    carlos_match = st.tagged_example(api, "carlos", "IT-04-02 Carlos")
    carlos = _created(api, "carlos")
    for plan, own in ((ivy, ivy_match), (carlos, carlos_match)):
        cited = {
            e["match_id"]
            for s in plan["sessions"]
            for a in s["assignments"]
            for e in a["citation"]["evidence"]
        }
        assert cited == {own}
    assert set(_ids(ivy)).isdisjoint(_ids(carlos))
    assert api.request("ivy", "GET", PLAN).json() == ivy


def test_it_04_02_a_plan_whose_only_match_is_deleted_is_no_plan(
    api: ApiDriver, committed_db: Any
) -> None:
    """coaching-plan §8: no tagged match remains -> the plan is deleted, 404 ``no_plan``."""
    match_id = st.tagged_example(api, "ivy", "IT-04-02 deleted")
    _created(api, "ivy")
    assert st.delete_match(api, "ivy", match_id).status_code in (200, 202, 204)
    assert st.refusal(api.request("ivy", "GET", PLAN))[:2] == (404, "no_plan")
    assert _plans(committed_db) == 0


# ------------------------------------------------------------------ NFR-019 and OpenAPI
def test_it_04_02_nfr_019_generation_p95_is_at_most_5_s(
    api: ApiDriver, committed_db: Any
) -> None:
    for n in range(3):
        st.tagged_example(api, "ivy", f"IT-04-02 NFR-019 {n}")
    took = []
    for _ in range(GENERATIONS):
        started = time.perf_counter()
        response = _post(api, "ivy")
        took.append(time.perf_counter() - started)
        assert response.status_code == 201, response.text
    p95 = sorted(took)[math.ceil(0.95 * len(took)) - 1]
    print(f"NFR-019 generation over 3 matches: n={len(took)} p95={p95:.3f}s max={max(took):.3f}s")
    assert p95 <= NFR_019_P95_S


def test_it_04_02_openapi_documents_both_routes(api: ApiDriver) -> None:
    response = api.request("anonymous", "GET", "/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"][PLAN]
    assert {"201", "409", "422"} <= set(paths["post"]["responses"])
    assert {"200", "404"} <= set(paths["get"]["responses"])
    schema = paths["post"]["requestBody"]["content"]["application/json"]["schema"]
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        schema = response.json()["components"]["schemas"][name]
    assert set(schema["required"]) == set(SOLO_WALL)
    assert set(schema["properties"]) == set(SOLO_WALL) | {"weekly_minutes"}
    assert schema["additionalProperties"] is False
