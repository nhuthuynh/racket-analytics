"""The scorebook tables store inputs only (ST-026; FR-049; match-aggregate §6, §9).

No I/O: the table definitions. "No score column exists" is the schema test match-aggregate §9
names; the round trip through Postgres is IT-02-01 (QA lane).
"""

from __future__ import annotations

import pytest

from racket.matches.repository import matches
from racket.matches.scorebook.repository import match_corrections, match_games, match_rallies

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "table", [match_games, match_rallies, match_corrections, matches], ids=lambda t: t.name
)
def test_no_table_of_the_aggregate_has_a_score_column(table: object) -> None:
    names = [c.name for c in table.columns]  # type: ignore[attr-defined]
    assert not [n for n in names if "score" in n and n != "scoring_system"]


def test_a_rally_stores_times_and_the_outcome_input() -> None:
    assert {c.name for c in match_rallies.columns} == {
        "id",
        "match_id",
        "game_number",
        "seq",
        "start_ms",
        "end_ms",
        "ending",
        "winning_side",
        "responsible_player",
        "fault_kind",
        "withdrawn",
        "created_version",
    }


def test_the_match_row_carries_the_optimistic_lock_and_best_of() -> None:
    assert {"version", "best_of"} <= {c.name for c in matches.columns}


def test_every_child_row_is_deleted_with_its_match() -> None:
    for table in (match_games, match_rallies, match_corrections):
        (fk,) = table.c.match_id.foreign_keys
        assert (fk.column.table.name, fk.ondelete) == ("matches", "CASCADE")
