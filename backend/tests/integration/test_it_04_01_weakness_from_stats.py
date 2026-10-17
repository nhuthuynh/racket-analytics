"""IT-04-01 (ST-055; FR-120; ADR 0003; coaching-plan §3-§4): weakness ranking from tagged matches
in Postgres, read through Coaching's ACL.

Matches are created and tagged through the API (Ivy is slot A1, ``is_me``, so side A); the
ranking is then built by ``racket.coaching.weakness.acl.ranking_for`` on a fresh session, which
reads only ``racket.matches.public.player_sides`` and ``racket.analytics.public.rally_facts``.
The expected rows are the coach's worked examples in docs/domain/weakness-catalogue.md §7,
read from the file and compared in the catalogue's own row format. Negative cases first.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy.orm import Session

from racket.coaching.weakness import acl
from racket.coaching.weakness.domain import WeaknessRanking
from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver
from tests.unit.coaching.weakness_examples import catalogue_rows, corrected_games, render

pytestmark = [pytest.mark.needs_verification, pytest.mark.coaching]


def _ranking(engine: Any, api: ApiDriver, user: str) -> WeaknessRanking:
    owner = uuid.UUID(st.me_id(api, user))
    with Session(bind=engine) as session:
        return acl.ranking_for(session, owner)


def _no_me_match(api: ApiDriver, user: str, title: str) -> str:
    client = api.as_user(user)
    body = {k: v for k, v in sb.doubles_body(title).items() if k != "participants"}  # Sprint 0
    response = api.run(client.post("/matches", json=body))
    assert response.status_code == 201, response.text
    match_id = str(response.json()["id"])
    api.run(sb.receive_video(client, match_id))
    api.run(sb.start_game(client, match_id))
    api.run(sb.tag_all(client, match_id, list(st.WORKED_EXAMPLE)))
    return match_id


def test_it_04_01_no_tagged_match_gives_an_empty_ranking_with_a_reason(
    api: ApiDriver, committed_db: Any
) -> None:
    empty = _ranking(committed_db, api, "ivy")
    assert (empty.weaknesses, empty.reason, empty.games) == ((), "no_tagged_match", 0)
    sb.ready_match(api, "ivy", "IT-04-01 started, no rally")
    started = _ranking(committed_db, api, "ivy")
    assert (started.weaknesses, started.reason, started.games) == ((), "no_tagged_match", 0)


def test_it_04_01_a_match_without_me_is_skipped_and_counted(
    api: ApiDriver, committed_db: Any
) -> None:
    _no_me_match(api, "ivy", "IT-04-01 no me")
    ranking = _ranking(committed_db, api, "ivy")
    assert (ranking.weaknesses, ranking.reason, ranking.skipped_matches) == (
        (),
        "no_tagged_match",
        1,
    )


def test_it_04_01_a_deleted_match_and_another_players_match_never_count(
    api: ApiDriver, committed_db: Any
) -> None:
    mine = st.tagged_example(api, "ivy", "IT-04-01 deleted")
    st.tagged_example(api, "carlos", "IT-04-01 someone else")
    assert _ranking(committed_db, api, "ivy").games == 1
    response = st.delete_match(api, "ivy", mine)
    assert response.status_code in (200, 202, 204), response.text
    ranking = _ranking(committed_db, api, "ivy")
    assert (ranking.weaknesses, ranking.reason) == ((), "no_tagged_match")


def test_it_04_01_the_tagged_worked_example_ranks_as_the_catalogue(
    api: ApiDriver, committed_db: Any
) -> None:
    st.tagged_example(api, "ivy", "IT-04-01 worked example")
    ranking = _ranking(committed_db, api, "ivy")
    games, cell, totals = catalogue_rows()[("dict §2", "A")]
    assert ranking.games == games
    assert render(ranking) == (cell, totals)
    assert (ranking.rallies, ranking.skipped_matches, ranking.reason) == (13, 0, None)
    assert (ranking.unit, ranking.provisional, ranking.side_out_verified) == (
        "rallies_lost_per_game",
        True,
        False,
    )


def test_it_04_01_golden_match_gm1_ranks_as_the_catalogue_and_matches_pool(
    api: ApiDriver, committed_db: Any
) -> None:
    st.tag_games(api, "ivy", corrected_games("gm1"), "IT-04-01 gm1")
    gm1 = _ranking(committed_db, api, "ivy")
    games, cell, totals = catalogue_rows()[("gm1", "A")]
    assert gm1.games == games
    assert render(gm1) == (cell, totals)

    st.tagged_example(api, "ivy", "IT-04-01 pooled")
    pooled = _ranking(committed_db, api, "ivy")
    alone = {w.id: w.lost for w in gm1.weaknesses}
    for w in pooled.weaknesses:
        extra = {"opponent_winners": 3, "unforced_errors": 2, "serve_faults": 2}.get(w.id, 0)
        assert w.lost == alone.get(w.id, 0) + extra, w.id
    assert (pooled.games, pooled.rallies) == (gm1.games + 1, gm1.rallies + 13)
