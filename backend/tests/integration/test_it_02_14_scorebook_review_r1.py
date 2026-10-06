"""IT-02-14 (review round 1 of Sprint 2: PE-S2-R1-02..05) through the API on Postgres.

* PE-S2-R1-05: a singles match (no preset until ST-035) refuses ``POST …/games`` with 409
  ``rules_unavailable`` and writes nothing.
* PE-S2-R1-03: ``PATCH …/rallies/{id}`` with ``{"field": "outcome", "value": {...}}`` turns a
  scored rally into a replay and back, one audit row each.
* PE-S2-R1-04: a game-2 tag inside game 1's time span is 422 ``invalid_rally``
  ``start_ms``/``out_of_game_order`` and writes nothing.
* PE-S2-R1-02: after a correction reopens game 1 while game 2 is started and empty, the next tag
  is saved in game 1 and scored (no "needs your decision" dead end); with game-2 rallies, the
  earliest is moved back by ``move_to_previous_game``.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.support import scorebook as sb
from tests.support.api import ApiDriver

WIN = {"ending": "winner", "responsible_player": None, "fault_kind": None}


def _tag(side: str, n: int) -> dict[str, Any]:
    return {**WIN, "winning_side": side, "start_ms": n * 2_000, "end_ms": n * 2_000 + 900}


def _error(response: httpx.Response) -> tuple[int, str, list[tuple[Any, Any]]]:
    error = response.json()["error"]
    return (
        response.status_code,
        error["code"],
        [(f["field"], f["code"]) for f in error.get("fields", [])],
    )


def _game_1_won(api: ApiDriver, title: str) -> tuple[httpx.AsyncClient, str, list[str]]:
    """Game 1 won 11-0 by A at 0, 2000, ... 20000 ms; game 2 started with B serving."""
    ivy = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(ivy, title))
    api.run(sb.receive_video(ivy, match_id))
    api.run(sb.start_game(ivy, match_id))
    tagged = api.run(sb.tag_all(ivy, match_id, [_tag("A", n) for n in range(11)]))
    api.run(sb.start_game(ivy, match_id, side="B"))
    return ivy, match_id, [r.json()[sb.tagcontract.RALLY_ID_KEY] for r in tagged]


def _send(
    api: ApiDriver, client: httpx.AsyncClient, name: str, body: Any = None, **ids: str
) -> httpx.Response:
    version = api.run(sb.version_of(client, ids["match_id"]))
    return api.run(sb.command(client, name, version=version, body=body, **ids))


def test_it_02_14_singles_cannot_start_a_game_without_a_preset(
    api: ApiDriver, committed_db: Any
) -> None:
    ivy = api.as_user("ivy")
    created = api.run(ivy.post("/matches", json={"title": "IT-02-14 singles", "format": "singles"}))
    assert created.status_code == 201, created.text
    match_id = created.json()["id"]
    api.run(sb.receive_video(ivy, match_id))
    before = sb.row_counts(committed_db)
    refused = _send(api, ivy, "start_game", body=sb.tagcontract.START_GAME_BODY, match_id=match_id)
    assert _error(refused) == (409, "rules_unavailable", [])
    assert sb.row_counts(committed_db) == before


def test_it_02_14_a_rally_is_corrected_to_a_replay_and_back(api: ApiDriver) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(ivy, "IT-02-14 outcome"))
    api.run(sb.receive_video(ivy, match_id))
    api.run(sb.start_game(ivy, match_id))
    tagged = api.run(sb.tag_all(ivy, match_id, [_tag("A", 0), _tag("A", 1)]))
    rally_id = tagged[0].json()[sb.tagcontract.RALLY_ID_KEY]
    ids = {"match_id": match_id, "rally_id": rally_id}

    replay = _send(
        api, ivy, "correct", body={"field": "outcome", "value": {"ending": "replay"}}, **ids
    )
    assert replay.status_code == 200, replay.text
    row = replay.json()["sheet"]["rows"][0]
    assert (row["ending"], row["winning_side"], row["corrected_by_user"]) == ("replay", None, True)

    value = {"ending": "forced_error", "winning_side": "B", "responsible_player": "A2"}
    back = _send(api, ivy, "correct", body={"field": "outcome", "value": value}, **ids)
    assert back.status_code == 200, back.text
    row = back.json()["sheet"]["rows"][0]
    assert (row["ending"], row["winning_side"], row["responsible_player"]) == (
        "forced_error",
        "B",
        "A2",
    )

    items = api.run(ivy.get(f"/matches/{match_id}/corrections")).json()["items"]
    outcome_items = [i for i in items if i["field"] == "outcome"]
    assert [(i["old_value"]["ending"], i["new_value"]["ending"]) for i in outcome_items] == [
        ("winner", "replay"),
        ("replay", "forced_error"),
    ]
    bad = _send(
        api, ivy, "correct", body={"field": "outcome", "value": {"ending": "winner"}}, **ids
    )
    assert _error(bad) == (422, "invalid_outcome", [("winning_side", "side_required")])


def test_it_02_14_a_game_2_tag_inside_game_1_is_refused(api: ApiDriver, committed_db: Any) -> None:
    ivy, match_id, _ = _game_1_won(api, "IT-02-14 order")
    before = sb.row_counts(committed_db)
    inside = {**WIN, "winning_side": "B", "start_ms": 1_000, "end_ms": 1_500}  # a gap of game 1
    refused = _send(api, ivy, "tag", body=inside, match_id=match_id)
    assert _error(refused) == (422, "invalid_rally", [("start_ms", "out_of_game_order")])
    assert sb.row_counts(committed_db) == before


def test_it_02_14_a_reopened_game_1_takes_the_next_tag(api: ApiDriver) -> None:
    ivy, match_id, ids = _game_1_won(api, "IT-02-14 reopened")
    fix = _send(api, ivy, "correct", body={"field": "winning_side", "value": "B"},
                match_id=match_id, rally_id=ids[10])  # fmt: skip
    assert fix.status_code == 200, fix.text
    assert fix.json()["sheet"]["games"][0]["winner"] is None

    for n in range(11, 14):  # B serves at 0-10-1; A wins the serve back, then the point
        response = _send(api, ivy, "tag", body=_tag("A", n), match_id=match_id)
        assert response.status_code == 201, response.text
        rows = response.json()["sheet"]["rows"]
        assert (rows[-1]["game"], rows[-1]["marker"]) == (1, None)
        if response.json()["sheet"]["games"][0]["winner"] == "A":
            break
    else:
        pytest.fail("game 1 never ended")
    nxt = _send(api, ivy, "tag", body=_tag("B", 20), match_id=match_id)
    assert nxt.status_code == 201, nxt.text
    assert (nxt.json()["sheet"]["rows"][-1]["game"], nxt.json()["sheet"]["rows"][-1]["marker"]) == (
        2,
        None,
    )


@pytest.mark.needs_verification
def test_it_02_14_c03_rallies_move_back_into_the_reopened_game(api: ApiDriver) -> None:
    ivy, match_id, ids = _game_1_won(api, "IT-02-14 c03")
    game_2 = api.run(sb.tag_all(ivy, match_id, [_tag("B", 11), _tag("A", 12)]))
    first, second = (r.json()[sb.tagcontract.RALLY_ID_KEY] for r in game_2)
    _send(api, ivy, "correct", body={"field": "winning_side", "value": "B"},
          match_id=match_id, rally_id=ids[10])  # fmt: skip

    blocked = _send(api, ivy, "tag", body=_tag("A", 13), match_id=match_id)
    assert _error(blocked)[:2] == (409, "decision_needed")
    out_of_order = _send(api, ivy, "resolve", body={"decision": "move_to_previous_game"},
                         match_id=match_id, rally_id=second)  # fmt: skip
    assert _error(out_of_order) == (422, "validation_failed", [("decision", "not_first_in_game")])
    moved = _send(api, ivy, "resolve", body={"decision": "move_to_previous_game"},
                  match_id=match_id, rally_id=first)  # fmt: skip
    assert moved.status_code == 200, moved.text
    rows = moved.json()["sheet"]["rows"]
    assert (rows[11]["game"], rows[11]["marker"]) == (1, None)


@pytest.mark.needs_verification
def test_it_02_14_r2_rallies_move_forward_latest_first(api: ApiDriver, committed_db: Any) -> None:
    """PE-S2-R2-01 (review round 2): ``move_to_next_game`` moves only the latest kept rally of
    game n, so no game-n rally is left behind a game-n+1 rally on the video (I5)."""
    ivy = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(ivy, "IT-02-14 r2 forward"))
    api.run(sb.receive_video(ivy, match_id))
    api.run(sb.start_game(ivy, match_id))
    sides = ["A"] * 10 + ["B", "A", "A", "A"]  # rally 11 corrected to A: 12-14 after the end
    tagged = api.run(sb.tag_all(ivy, match_id, [_tag(s, n) for n, s in enumerate(sides)]))
    ids = [r.json()[sb.tagcontract.RALLY_ID_KEY] for r in tagged]
    fix = _send(api, ivy, "correct", body={"field": "winning_side", "value": "A"},
                match_id=match_id, rally_id=ids[10])  # fmt: skip
    assert fix.status_code == 200, fix.text
    assert [r["marker"] for r in fix.json()["sheet"]["rows"][11:]] == ["needs_decision"] * 3
    api.run(sb.start_game(ivy, match_id, side="B"))

    before = sb.row_counts(committed_db)
    for n in (11, 12):  # rallies 12 and 13: a later game-1 rally would stay behind
        refused = _send(api, ivy, "resolve", body={"decision": "move_to_next_game"},
                        match_id=match_id, rally_id=ids[n])  # fmt: skip
        assert _error(refused) == (422, "validation_failed", [("decision", "not_last_in_game")])
    assert sb.row_counts(committed_db) == before

    for n in (13, 12, 11):
        moved = _send(api, ivy, "resolve", body={"decision": "move_to_next_game"},
                      match_id=match_id, rally_id=ids[n])  # fmt: skip
        assert moved.status_code == 200, moved.text
    rows = moved.json()["sheet"]["rows"]
    assert [(r["game"], r["marker"]) for r in rows[11:]] == [(2, None)] * 3
    assert [r["rally_id"] for r in rows] == ids  # sheet order is the video order
    shrink = _send(api, ivy, "correct", body={"field": "end_ms", "value": 22_800},
                   match_id=match_id, rally_id=ids[11])  # fmt: skip
    assert shrink.status_code == 200, shrink.text
