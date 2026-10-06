"""IT-02-03 (ST-031; FR-052; match-aggregate I8): UPDATE or DELETE on the corrections table is
refused by the database itself, for the application's own role.

Positive controls: the application appends rows (a correction and an undo through the API),
and deleting the whole match cascades (BE-D1-06: the only delete that may reach the table).
"""

from __future__ import annotations

from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError

from tests.support import scorebook as sb
from tests.support.api import ApiDriver


@pytest.fixture
def audited_match(api: ApiDriver) -> str:
    match_id = sb.ready_tagged_match(api, "ivy", title="IT-02-03")
    ivy = api.as_user("ivy")
    rally_2 = api.run(sb.sheet(ivy, match_id)).json()["rows"][1]["rally_id"]
    version = api.run(sb.version_of(ivy, match_id))
    response = api.run(
        sb.command(ivy, "correct", version=version, body={"field": "ending", "value": "winner"},
                   match_id=match_id, rally_id=rally_2)
    )  # fmt: skip
    assert response.status_code == 200, response.text
    undo = api.run(sb.command(ivy, "undo", version=response.json()["version"], match_id=match_id))
    assert undo.status_code == 200, undo.text
    return match_id


def _count(engine: Any, match_id: str) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(
                sa.text("SELECT count(*) FROM match_corrections WHERE match_id = :m"),
                {"m": match_id},
            ).scalar_one()
        )


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE match_corrections SET new_value = '\"B\"'::jsonb WHERE match_id = :m",
        "UPDATE match_corrections SET kind = 'correction' WHERE match_id = :m",
        "DELETE FROM match_corrections WHERE match_id = :m",
    ],
    ids=["update-value", "update-kind", "delete"],
)
def test_it_02_03_update_or_delete_of_an_audit_row_is_refused(
    committed_db: Any, audited_match: str, statement: str
) -> None:
    before = _count(committed_db, audited_match)
    assert before >= 3  # game started, correction, undo (positive control: rows are appended)
    with pytest.raises(DBAPIError, match="append-only"), committed_db.begin() as conn:
        conn.execute(sa.text(statement), {"m": audited_match})
    assert _count(committed_db, audited_match) == before


def test_it_02_03_truncate_is_not_granted_to_public(committed_db: Any) -> None:
    with committed_db.connect() as conn:
        granted = (
            conn.execute(
                sa.text(
                    "SELECT privilege_type FROM information_schema.role_table_grants "
                    "WHERE table_name = 'match_corrections' AND grantee = 'PUBLIC'"
                )
            )
            .scalars()
            .all()
        )
    assert not {"UPDATE", "DELETE", "TRUNCATE"} & set(granted)


def test_it_02_03_deleting_the_match_cascades_to_its_audit_rows(
    committed_db: Any, audited_match: str
) -> None:
    with committed_db.begin() as conn:
        conn.execute(sa.text("DELETE FROM matches WHERE id = :m"), {"m": audited_match})
    assert _count(committed_db, audited_match) == 0


def test_it_02_03_truncate_by_the_owning_app_role_is_refused(
    committed_db: Any, audited_match: str
) -> None:
    """SEC-S2-TM-02 / QA-RV2-09 (T-SB-7): the app role owns the table, so the REVOKE from
    PUBLIC does not stop TRUNCATE and no row trigger fires on it; a statement trigger does."""
    before = _count(committed_db, audited_match)
    with pytest.raises(DBAPIError, match="append-only"), committed_db.begin() as conn:
        conn.execute(sa.text("TRUNCATE match_corrections"))
    assert _count(committed_db, audited_match) == before


def _delete_from_another_trigger(conn: Any, match_id: str) -> None:
    """Arms an AFTER INSERT trigger on a temp table that deletes the match's audit rows, then
    fires it (probe E1 of threat-model-sprint-02 §8)."""
    conn.execute(sa.text("CREATE TEMP TABLE it_02_03_probe (match_id uuid)"))
    conn.execute(
        sa.text(
            "CREATE FUNCTION pg_temp.it_02_03_wipe() RETURNS trigger LANGUAGE plpgsql AS $$ "
            "BEGIN DELETE FROM public.match_corrections WHERE match_id = NEW.match_id; "
            "RETURN NEW; END $$"
        )
    )
    conn.execute(
        sa.text(
            "CREATE TRIGGER it_02_03_wipe AFTER INSERT ON it_02_03_probe "
            "FOR EACH ROW EXECUTE FUNCTION pg_temp.it_02_03_wipe()"
        )
    )
    with pytest.raises(DBAPIError, match="append-only"):
        conn.execute(sa.text("INSERT INTO it_02_03_probe VALUES (:m)"), {"m": match_id})


def test_it_02_03_a_delete_from_another_trigger_is_refused_while_the_match_exists(
    committed_db: Any, audited_match: str
) -> None:
    """SEC-S2-TM-01 (T-SB-6): ``pg_trigger_depth() > 1`` alone let any trigger-nested DELETE
    through. Only the cascade from deleting the match may remove audit rows (the cascade
    control above stays green). Rolled back."""
    before = _count(committed_db, audited_match)
    with committed_db.connect() as conn:
        trans = conn.begin()
        try:
            _delete_from_another_trigger(conn, audited_match)
        finally:
            trans.rollback()
    assert _count(committed_db, audited_match) == before


def test_it_02_03_a_temp_table_named_matches_does_not_open_the_cascade_path(
    committed_db: Any, audited_match: str
) -> None:
    """SEC-S2-TM-01 hardening: an empty temporary ``matches`` is searched before ``public``;
    the trigger reads ``public.matches`` with a pinned ``search_path``, so it is not fooled."""
    before = _count(committed_db, audited_match)
    with committed_db.connect() as conn:
        trans = conn.begin()
        try:
            conn.execute(sa.text("CREATE TEMP TABLE matches (id uuid)"))
            conn.execute(sa.text("DISCARD PLANS"))  # a pooled session may hold an older plan
            _delete_from_another_trigger(conn, audited_match)
        finally:
            trans.rollback()
    assert _count(committed_db, audited_match) == before
