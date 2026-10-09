"""ST-051 (FR-007, NFR-066 b, NFR-057; deletion-and-purge.md §3.3, §4.2): the purge removes a
deleted account last, real Postgres and object store. Negative cases first.

1. The store refuses every delete during a pass: Ivy's match cannot be purged, so her account
   tombstone stays (no personal column, ``deleted_at`` set). A pass that removed the row first
   would leave match rows and objects that no deleted account points to any more. The next pass
   with a working store removes the match, then the account.
2. SEC-S3-TM-05 second net: a match of a deleted account that is still live (a creation that
   committed past ``DELETE /me``) is tombstoned by the pass and purged with the account.

Carlos's rows are untouched in both. Not an accepted test file: new, so no TCR row is needed.
"""

from __future__ import annotations

import contextlib
from typing import Any

import pytest
import sqlalchemy as sa

from tests.support import stats as st
from tests.support.api import ApiDriver


def _account(engine: Any, account_id: str) -> dict[str, Any] | None:
    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT email, email_key, username, display_name, deleted_at "
                "FROM accounts WHERE id = :id"
            ),
            {"id": account_id},
        ).mappings().first()
    return None if row is None else dict(row)


def _live_matches(engine: Any, owner_id: str) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(
                sa.text("SELECT count(*) FROM matches WHERE owner_id = :o AND deleted_at IS NULL"),
                {"o": owner_id},
            ).scalar_one()
        )


def _left(engine: Any, ids: list[str]) -> dict[str, int]:
    return {k: n for k, n in st.rows_holding(engine, ids).items() if n}


def test_st_051_a_match_left_unpurged_keeps_the_account_tombstone(
    api: ApiDriver, committed_db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    match_id = st.tagged_example(api, "ivy", "ST-051 purged last")
    carlos_match = st.tagged_example(api, "carlos", "ST-051 carlos")
    carlos_rows = st.rows_holding(committed_db, [carlos_match])
    me = st.me_id(api, "ivy")
    keys = st.object_keys_of(committed_db, match_id)
    assert keys
    assert st.delete_account(api, "ivy").status_code in st.statscontract.DELETE_OK

    store_cls = st.OBJECT_STORE.load()
    real_delete = store_cls.delete
    refused = {"n": 0}

    def refusing_delete(self: Any, key: str) -> None:
        refused["n"] += 1
        raise ConnectionError("injected store failure (ST-051 purged last)")

    monkeypatch.setattr(store_cls, "delete", refusing_delete)
    with contextlib.suppress(Exception):  # a failed match may end the run with exit 1
        st.PURGE_MAIN.load()(["--once"])
    assert refused["n"] >= 1, "the purge never tried to delete an object of the match"

    tombstone = _account(committed_db, me)
    assert tombstone is not None, "the account row was purged while its match was left"
    assert tombstone["deleted_at"] is not None
    assert {k: tombstone[k] for k in ("email", "email_key", "username", "display_name")} == {
        "email": None, "email_key": None, "username": None, "display_name": None,
    }  # fmt: skip
    assert _left(committed_db, [match_id]), "the match rows went although its objects remain"

    monkeypatch.setattr(store_cls, "delete", real_delete)
    st.run_purge_once()
    assert _left(committed_db, [me, match_id]) == {}
    assert _account(committed_db, me) is None
    assert st.keys_still_stored(keys) == []
    assert st.rows_holding(committed_db, [carlos_match]) == carlos_rows


def test_st_051_a_live_match_of_a_deleted_account_is_caught_by_the_pass(
    api: ApiDriver, committed_db: Any
) -> None:
    match_id = st.tagged_example(api, "ivy", "ST-051 second net")
    carlos_match = st.tagged_example(api, "carlos", "ST-051 carlos net")
    carlos_rows = st.rows_holding(committed_db, [carlos_match])
    me = st.me_id(api, "ivy")
    keys = st.object_keys_of(committed_db, match_id)
    assert st.delete_account(api, "ivy").status_code in st.statscontract.DELETE_OK
    with committed_db.begin() as conn:  # the creation that committed after DELETE /me
        conn.execute(
            sa.text("UPDATE matches SET deleted_at = NULL WHERE id = :id"), {"id": match_id}
        )
    assert _live_matches(committed_db, me) == 1

    st.run_purge_once()
    assert _left(committed_db, [me, match_id]) == {}
    assert st.keys_still_stored(keys) == []
    assert st.rows_holding(committed_db, [carlos_match]) == carlos_rows
