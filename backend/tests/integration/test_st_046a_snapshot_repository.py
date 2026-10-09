"""ST-046a integration (FR-100, NFR-075, ADR 0040): ``SnapshotRepository`` over migration 0014
on a real Postgres. Negative cases first: an older or equal ``sheet_version`` never overwrites
the stored row (invariant S2), and the PUBLIC role gets nothing on ``metric_snapshots``.
One row per (match, metric_def_version, rules_version); 0014 is chained on 0013.
"""

from __future__ import annotations

import importlib.util
import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import sqlalchemy as sa

from racket import migrations
from racket.analytics.repository import SnapshotRepository
from racket.analytics.snapshot import MetricSnapshot, SnapshotKey
from racket.sports.pickleball.metrics import load_dictionary
from tests.unit.analytics.sheets import WORKED_EXAMPLE, a_serves_and_wins_25, one_game

NOW = datetime(2026, 10, 9, 9, 0, tzinfo=UTC)
OWNER = uuid.UUID("22222222-2222-4222-8222-222222222222")


def _snapshot(match_id: uuid.UUID, version: int, tags: Any = WORKED_EXAMPLE) -> MetricSnapshot:
    return MetricSnapshot.compute(
        match_id=match_id,
        owner_id=OWNER,
        sheet=one_game(tags),
        sheet_version=version,
        dictionary=load_dictionary(),
        now=NOW + timedelta(seconds=version),
    )


def test_st_046a_an_older_or_equal_sheet_version_never_overwrites(db_session: Any) -> None:
    repo = SnapshotRepository(db_session)
    match_id = uuid.uuid4()
    newest = _snapshot(match_id, 15)
    assert repo.upsert(newest) is True
    assert repo.upsert(_snapshot(match_id, 15, WORKED_EXAMPLE[:3])) is False  # same version again
    assert repo.upsert(_snapshot(match_id, 14, WORKED_EXAMPLE[:2])) is False  # a late event
    stored = repo.get(newest.key)
    assert stored is not None
    assert (stored.sheet_version, stored.computed_at) == (15, newest.computed_at)
    assert stored.stats == newest.stats


def test_st_046a_a_stored_snapshot_keeps_each_metrics_own_min_sample_flag(
    db_session: Any,
) -> None:
    """ADR 0041 / invariant S6 over Postgres: a dictionary with AN-05 n = 30 stores AN-05 of
    side A flagged at n = 25 and AN-01 not, under that dictionary's version."""
    shipped = load_dictionary()
    entries = tuple(
        replace(e, min_sample={"unit": "rallies", "n": 30}) if e.id == "AN-05" else e
        for e in shipped.entries
    )
    odd = replace(shipped, version="9.9", entries=entries)
    snap = MetricSnapshot.compute(
        match_id=uuid.uuid4(),
        owner_id=OWNER,
        sheet=a_serves_and_wins_25(),
        sheet_version=26,
        dictionary=odd,
        now=NOW,
    )
    repo = SnapshotRepository(db_session)
    assert repo.upsert(snap) is True
    stored = repo.get(SnapshotKey(snap.key.match_id, "9.9", "PROVISIONAL-UNVERIFIED"))
    assert stored is not None
    an05, an01 = stored.stats["AN-05"]["A"], stored.stats["AN-01"]["A"]
    assert (an05["n"], an05["low_sample"]) == (25, True)
    assert (an01["n"], an01["low_sample"]) == (25, False)


def test_st_046a_the_public_role_has_no_privilege_on_metric_snapshots(db_session: Any) -> None:
    table = db_session.execute(sa.text("SELECT to_regclass('metric_snapshots')")).scalar_one()
    assert table == "metric_snapshots"
    grants = db_session.execute(
        sa.text(
            "SELECT privilege_type FROM information_schema.role_table_grants "
            "WHERE table_name = 'metric_snapshots' AND grantee = 'PUBLIC'"
        )
    ).all()
    assert grants == []


def test_st_046a_a_negative_sheet_version_is_refused_by_the_table(db_session: Any) -> None:
    with (
        pytest.raises(sa.exc.IntegrityError, match="sheet_version_not_negative"),
        db_session.begin_nested(),
    ):
        SnapshotRepository(db_session).upsert(_snapshot(uuid.uuid4(), -1))


def test_st_046a_migration_0014_is_head_and_chained_on_0013(db_session: Any) -> None:
    path = Path(migrations.__file__).parent / "versions" / "0014_metric_snapshots.py"
    spec = importlib.util.spec_from_file_location("migration_0014", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert (module.revision, module.down_revision) == ("0014", "0013")
    version = db_session.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version >= "0014"
    pk = db_session.execute(
        sa.text(
            "SELECT a.attname FROM pg_index i JOIN pg_attribute a "
            "ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
            "WHERE i.indrelid = 'metric_snapshots'::regclass AND i.indisprimary"
        )
    ).scalars()
    assert set(pk) == {"match_id", "metric_def_version", "rules_version"}


def test_st_046a_a_newer_sheet_version_replaces_the_row(db_session: Any) -> None:
    repo = SnapshotRepository(db_session)
    match_id = uuid.uuid4()
    assert repo.upsert(_snapshot(match_id, 3, WORKED_EXAMPLE[:3])) is True
    newer = _snapshot(match_id, 15)
    assert repo.upsert(newer) is True
    stored = repo.get(newer.key)
    assert stored == newer


def test_st_046a_each_dictionary_and_rules_version_keeps_its_own_row(db_session: Any) -> None:
    repo = SnapshotRepository(db_session)
    match_id = uuid.uuid4()
    base = _snapshot(match_id, 15)
    other_dict = replace(base, key=replace(base.key, metric_def_version="9.9.9"), sheet_version=1)
    other_rules = replace(base, key=replace(base.key, rules_version="OTHER"), sheet_version=1)
    assert [repo.upsert(s) for s in (base, other_dict, other_rules)] == [True, True, True]
    for snap in (base, other_dict, other_rules):
        stored = repo.get(snap.key)
        assert stored is not None
        assert stored.sheet_version == snap.sheet_version
    assert repo.get(SnapshotKey(match_id, "0.0.0", "PROVISIONAL-UNVERIFIED")) is None


def test_st_046a_delete_for_match_and_match_ids_page_by_match(db_session: Any) -> None:
    repo = SnapshotRepository(db_session)
    ids = sorted(uuid.uuid4() for _ in range(3))
    for match_id in ids:
        repo.upsert(_snapshot(match_id, 1, WORKED_EXAMPLE[:1]))
    assert repo.match_ids(None, 2) == ids[:2]
    assert repo.match_ids(ids[1], 10) == ids[2:]
    assert repo.delete_for_match(ids[0]) == 1
    assert repo.match_ids(None, 10) == ids[1:]
    assert repo.get(_snapshot(ids[0], 1, WORKED_EXAMPLE[:1]).key) is None
