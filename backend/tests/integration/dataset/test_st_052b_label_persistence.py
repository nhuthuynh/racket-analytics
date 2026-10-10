"""ST-052b (FR-150, NFR-078; api-sprint-03 §5.2, §5.5): labeller role, team-held consent
record and label session persistence on real Postgres (migration 0017). Negative cases first.

1. Unknown accounts are refused by ``grant-labeller`` (exit 1) and nothing is stored; a refused
   consent (unknown match) stores nothing.
2. The role is removed with its account (FK cascade) and ``has_role`` ignores a deleted account.
3. One command at a time per match: the label session row is created empty once, and a second
   transaction cannot take its lock while the first holds it.
4. ``dataset.public.purge_match`` removes the consent record and the label session of that match
   only.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

pytestmark = [pytest.mark.integration]


def _admin(*argv: str) -> int:
    rc: int = st.LABELLER_ADMIN.load()(list(argv))
    return rc


def _count(engine: Any, sql: str, **params: Any) -> int:
    with engine.connect() as conn:
        return int(conn.execute(sa.text(sql), params).scalar_one())


def _match(api: ApiDriver, user: str, title: str) -> str:
    match_id = api.run(sb.create_doubles(api.as_user(user), title))
    return str(match_id)


def test_st_052b_unknown_ids_are_refused_and_nothing_is_stored(
    api: ApiDriver, committed_db: Any
) -> None:
    assert _admin("grant-labeller", "--account", str(uuid.uuid4())) == 1
    assert _admin("consent", "--match", str(uuid.uuid4()), "--record", "CONSENT-1") == 1
    assert _count(committed_db, "SELECT count(*) FROM account_roles") == 0
    assert _count(committed_db, "SELECT count(*) FROM label_consents") == 0


def test_st_052b_the_role_goes_with_its_account(api: ApiDriver, committed_db: Any) -> None:
    from racket.players import public as players

    ivy = st.me_id(api, "ivy")
    assert _admin("grant-labeller", "--account", ivy) == 0
    assert _admin("grant-labeller", "--account", ivy) == 0  # idempotent
    assert _count(committed_db, "SELECT count(*) FROM account_roles WHERE account_id = :a",
                  a=ivy) == 1  # fmt: skip
    assert st.delete_account(api, "ivy").status_code in st.statscontract.DELETE_OK
    with Session(bind=committed_db) as session:
        assert not players.has_role(session, uuid.UUID(ivy), "labeller")
    with committed_db.begin() as conn:
        conn.execute(sa.text("DELETE FROM accounts WHERE id = :a"), {"a": ivy})
    assert _count(committed_db, "SELECT count(*) FROM account_roles WHERE account_id = :a",
                  a=ivy) == 0  # fmt: skip


def test_st_052b_one_command_at_a_time_per_match(api: ApiDriver, committed_db: Any) -> None:
    from racket.dataset.repository import LabelRepository

    match_id = uuid.UUID(_match(api, "dana", "ST-052b lock"))
    owner = uuid.UUID(st.me_id(api, "dana"))
    now = datetime.now(UTC)
    with Session(bind=committed_db) as first:
        row = LabelRepository(first).lock_or_create(match_id, owner, now)
        assert (row.version, row.rallies, row.events) == (0, [], [])
        with Session(bind=committed_db) as second:
            second.execute(sa.text("SET LOCAL lock_timeout = '200ms'"))
            with pytest.raises(OperationalError):
                LabelRepository(second).lock_or_create(match_id, owner, now)
            second.rollback()
        LabelRepository(first).save(match_id, 1, [{"rally": 1}], [], now)
        first.commit()
    with Session(bind=committed_db) as again:
        row = LabelRepository(again).lock_or_create(match_id, owner, now)
        assert (row.version, row.rallies) == (1, [{"rally": 1}])
    assert _count(committed_db, "SELECT count(*) FROM label_sessions") == 1


def test_st_052b_purge_match_removes_only_that_matchs_label_rows(
    api: ApiDriver, committed_db: Any
) -> None:
    from racket.dataset import public as dataset
    from racket.dataset.repository import LabelRepository

    owner = uuid.UUID(st.me_id(api, "dana"))
    gone, kept = (_match(api, "dana", f"ST-052b {n}") for n in ("gone", "kept"))
    for match_id in (gone, kept):
        assert _admin("consent", "--match", match_id, "--record", "CONSENT-TEAM-001") == 0
    with Session(bind=committed_db) as session:
        for match_id in (gone, kept):
            LabelRepository(session).lock_or_create(uuid.UUID(match_id), owner, datetime.now(UTC))
        session.commit()
    with Session(bind=committed_db) as session:
        assert dataset.purge_match(session, uuid.UUID(gone)) == 2
        session.commit()
    total = ("SELECT (SELECT count(*) FROM label_consents WHERE match_id = :m)"
             " + (SELECT count(*) FROM label_sessions WHERE match_id = :m)")  # fmt: skip
    assert _count(committed_db, total, m=gone) == 0
    assert _count(committed_db, total, m=kept) == 2
