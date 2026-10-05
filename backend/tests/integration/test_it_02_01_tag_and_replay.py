"""IT-02-01 (ST-026; FR-049, NFR-075): tag 30 rallies through the API; the stored outcomes
replay to the same sheet; the rules version is stored with the match.

The score is never stored (no score column in any scorebook table); the sheet is a projection.
Expected scores come from the harness's independent stepper (``taglib``), not the engine.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa

from tests.support import contract
from tests.support import scorebook as sb
from tests.support.api import ApiDriver

# 30 rallies that never end the game under the provisional preset (10-7-1 after rally 30).
WINNERS_30 = "BABBBABABABABBABAAAAAABABBBBBB"
TAGS_30 = sb.taglib.with_times(
    [
        {"winning_side": w, "ending": "winner", "responsible_player": None, "fault_kind": None}
        for w in WINNERS_30
    ],
    duration_ms=60_000,
)
SCOREBOOK_TABLES = ("match_games", "match_rallies", "match_corrections")


def _stored_tags(engine: Any, match_id: str) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT winning_side, ending, responsible_player, fault_kind, start_ms, end_ms "
                "FROM match_rallies WHERE match_id = :m AND NOT withdrawn ORDER BY start_ms, seq"
            ),
            {"m": match_id},
        ).mappings()
        return [dict(r) for r in rows]


def test_it_02_01_thirty_tags_replay_to_the_same_sheet(api: ApiDriver, committed_db: Any) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(ivy, "IT-02-01"))
    api.run(sb.receive_video(ivy, match_id))
    api.run(sb.start_game(ivy, match_id))
    responses = api.run(sb.tag_all(ivy, match_id, TAGS_30))

    # Each tag answers the new projection; rally n's row is the reference row n.
    expected = sb.reference_rows(TAGS_30)
    for n, response in enumerate(responses, start=1):
        rows = sb.rows_of(response.json()[sb.tagcontract.SHEET_KEY])
        assert len(rows) == n
        assert sb.taglib.compare_rows(expected[:n], rows) == []

    # The sheet read back equals the last command's sheet, byte for byte.
    last = responses[-1].json()[sb.tagcontract.SHEET_KEY]
    read = api.run(sb.sheet(ivy, match_id)).json()
    assert sb.canonical(read) == sb.canonical(last)

    # The stored outcomes alone (read from the database) replay to the same rows.
    stored = _stored_tags(committed_db, match_id)
    assert len(stored) == 30
    assert sb.taglib.compare_rows(sb.reference_rows(stored), sb.rows_of(read)) == []

    # A fresh application instance (nothing cached in memory) projects the same bytes.
    fresh = ApiDriver(contract.APP_FACTORY.load()())
    try:
        fresh.as_user("ivy")
        again = fresh.run(sb.sheet(fresh.as_user("ivy"), match_id)).json()
    finally:
        fresh.close()
    assert sb.canonical(again) == sb.canonical(read)

    # rules_version is stored with the match and shown on the sheet (NFR-075).
    with committed_db.connect() as conn:
        stored_version = conn.execute(
            sa.text("SELECT rules_version FROM matches WHERE id = :m"), {"m": match_id}
        ).scalar_one()
    assert stored_version == contract.PROVISIONAL_PRESET
    assert read["rules_version"] == stored_version
    assert read["label"] == sb.taglib.UNOFFICIAL_LABEL


def test_it_02_01_no_scorebook_table_stores_a_score(committed_db: Any) -> None:
    with committed_db.connect() as conn:
        columns = conn.execute(
            sa.text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = ANY(:t)"
            ),
            {"t": list(SCOREBOOK_TABLES)},
        ).all()
    assert {t for t, _ in columns} == set(SCOREBOOK_TABLES), "a scorebook table is missing"
    assert [c for c in columns if "score" in c[1] or "call" in c[1]] == []
