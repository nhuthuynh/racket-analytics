"""IT-04-02 read cost (SRE-VERIFY04R3-01; G04-02 c: ``GET /me/plan`` at 50 RPS, p95 <= 300 ms; NFR-019
read side; coaching-plan §3 scope, §8). Root cause of the missed G04-02 (c): every ``GET``
replayed each scope match's scorebook twice (ranking and citations) and ran the stats read
repair, ~19 statements and ~28 ms of one worker's CPU per read (decisions/SRE-VERIFY04R3-01.md), so one
API process served < 40 reads/s. A read of an unchanged scope reuses the ranking and citation
facts; any change of the scope (a tag or correction bumps the match's scorebook version, a
deleted match leaves it) is read live. HTTP on Postgres, matches tagged through the API.
Negative cases first.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.support import stats as st
from tests.support.api import ApiDriver
from tests.support.statements import SCOREBOOK_TABLES, reads_of, statements, writes

pytestmark = [pytest.mark.integration, pytest.mark.coaching]

PLAN = "/me/plan"
SOLO_WALL = {
    "minutes_per_session": 30,
    "sessions_per_week": 3,
    "players_available": 1,
    "equipment": ["wall"],
    "level": "intermediate",
}
READ_BUDGET = 8  # statements of a GET whose scope is unchanged (was ~19)


def _read(api: ApiDriver, user: str) -> dict[str, Any]:
    response = api.request(user, "GET", PLAN)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _planned(api: ApiDriver, user: str, title: str) -> str:
    match_id = st.tagged_example(api, user, title)
    assert api.request(user, "POST", PLAN, json=SOLO_WALL).status_code == 201
    return match_id


# ------------------------------------------------------------------ a changed scope is live
def test_a_correction_after_a_read_shows_in_the_next_read(
    api: ApiDriver, committed_db: Any
) -> None:
    match_id = _planned(api, "ivy", "SRE-VERIFY04R3-01 corrected")
    before = _read(api, "ivy")
    assert st.correct_rally_3(api, "ivy", match_id).status_code == 200
    after = _read(api, "ivy")
    assert after["ranking"] != before["ranking"]
    assert after == _read(api, "ivy")


def test_a_new_tagged_match_after_a_read_is_in_the_next_read(
    api: ApiDriver, committed_db: Any
) -> None:
    _planned(api, "ivy", "SRE-VERIFY04R3-01 first")
    before = _read(api, "ivy")
    st.tagged_example(api, "ivy", "SRE-VERIFY04R3-01 second")
    after = _read(api, "ivy")
    assert after["ranking"] != before["ranking"]


def test_a_deleted_match_after_a_read_is_no_plan(api: ApiDriver, committed_db: Any) -> None:
    match_id = _planned(api, "ivy", "SRE-VERIFY04R3-01 deleted")
    _read(api, "ivy")
    assert st.delete_match(api, "ivy", match_id).status_code in (200, 202, 204)
    assert st.refusal(api.request("ivy", "GET", PLAN))[:2] == (404, "no_plan")


def test_another_account_reading_its_own_plan_never_gets_the_players(
    api: ApiDriver, committed_db: Any
) -> None:
    _planned(api, "ivy", "SRE-VERIFY04R3-01 ivy")
    ivy = _read(api, "ivy")
    assert st.refusal(api.request("carlos", "GET", PLAN))[:2] == (404, "no_plan")
    _planned(api, "carlos", "SRE-VERIFY04R3-01 carlos")
    carlos = _read(api, "carlos")
    assert carlos["id"] != ivy["id"]
    assert {e["match_id"] for e in _evidence(carlos)}.isdisjoint(
        e["match_id"] for e in _evidence(ivy)
    )


def _evidence(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        e for s in plan["sessions"] for a in s["assignments"] for e in a["citation"]["evidence"]
    ]


# ------------------------------------------------------------------ an unchanged scope is cheap
def test_a_read_of_an_unchanged_scope_replays_no_scorebook_and_writes_nothing(
    api: ApiDriver, committed_db: Any
) -> None:
    _planned(api, "ivy", "SRE-VERIFY04R3-01 unchanged")
    first = _read(api, "ivy")
    with statements() as sent:
        again = _read(api, "ivy")
    assert again == first
    assert reads_of(sent, *SCOREBOOK_TABLES) == []
    assert writes(sent) == []
    assert len(sent) <= READ_BUDGET, sent
