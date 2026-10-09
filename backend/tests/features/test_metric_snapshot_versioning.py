"""Binds tests/features/metric_snapshot_versioning.feature (ST-046a; FR-100, NFR-075; ADR 0040).

The sheet is built by the real projection (``tests.unit.analytics.sheets``), the snapshot by
``racket.analytics.snapshot`` and stored by ``SnapshotRepository`` in Postgres (migration 0014),
inside a transaction rolled back after each scenario.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import sqlalchemy as sa
from pytest_bdd import given, parsers, scenarios, then, when

from racket.analytics.repository import SnapshotRepository, metric_snapshots
from racket.analytics.snapshot import MetricSnapshot, SnapshotKey
from racket.analytics.starter_stats import starter_stats
from racket.analytics.uncertainty import InvalidPolicy
from racket.sports.pickleball.metrics import MetricDictionary, load_dictionary
from tests.unit.analytics.sheets import WORKED_EXAMPLE, one_game

scenarios("metric_snapshot_versioning.feature")

NOW = datetime(2026, 10, 9, 9, 0, tzinfo=UTC)
OWNER = uuid.UUID("22222222-2222-4222-8222-222222222222")


@pytest.fixture
def ctx(db_session: Any) -> dict[str, Any]:
    return {
        "match_id": uuid.uuid4(),
        "repo": SnapshotRepository(db_session),
        "session": db_session,
        "dictionary": load_dictionary(),
    }


def _snapshot(ctx: dict[str, Any], version: int, tags: Any = WORKED_EXAMPLE) -> MetricSnapshot:
    return MetricSnapshot.compute(
        match_id=ctx["match_id"],
        owner_id=OWNER,
        sheet=one_game(tags),
        sheet_version=version,
        dictionary=ctx["dictionary"],
        now=NOW + timedelta(seconds=version),
    )


@given(
    parsers.parse("the snapshot of the worked-example game at sheet version {version:d} is stored")
)
def stored_worked_example(ctx: dict[str, Any], version: int) -> None:
    ctx["stored"] = _snapshot(ctx, version)
    assert ctx["repo"].upsert(ctx["stored"]) is True


@given(
    parsers.parse(
        "the snapshot of the first {count:d} rallies at sheet version {version:d} is stored"
    )
)
def stored_prefix(ctx: dict[str, Any], count: int, version: int) -> None:
    assert ctx["repo"].upsert(_snapshot(ctx, version, WORKED_EXAMPLE[:count])) is True


@given("a metric dictionary where AN-05 needs 30 rallies and the other proportions need 20")
def odd_dictionary(ctx: dict[str, Any]) -> None:
    shipped: MetricDictionary = ctx["dictionary"]
    entries = tuple(
        replace(e, min_sample={"unit": "rallies", "n": 30}) if e.id == "AN-05" else e
        for e in shipped.entries
    )
    ctx["dictionary"] = replace(shipped, entries=entries)


@when(parsers.parse("a snapshot of the same match at sheet version {version:d} is written"))
def write_same_match(ctx: dict[str, Any], version: int) -> None:
    ctx["written"] = ctx["repo"].upsert(_snapshot(ctx, version, WORKED_EXAMPLE[:2]))


@when(
    parsers.parse("the snapshot of the worked-example game at sheet version {version:d} is written")
)
def write_worked_example(ctx: dict[str, Any], version: int) -> None:
    ctx["written"] = ctx["repo"].upsert(_snapshot(ctx, version))


@when(
    parsers.parse(
        'a snapshot of the same match under dictionary version "{dict_version}" '
        "at sheet version {version:d} is written"
    )
)
def write_other_dictionary(ctx: dict[str, Any], dict_version: str, version: int) -> None:
    snap = _snapshot(ctx, version)
    ctx["written"] = ctx["repo"].upsert(
        replace(snap, key=replace(snap.key, metric_def_version=dict_version))
    )


@when("the snapshot of the worked-example game is computed")
def compute(ctx: dict[str, Any]) -> None:
    try:
        ctx["snapshot"] = _snapshot(ctx, 15)
    except InvalidPolicy as exc:
        ctx["refused"] = exc


@then("nothing is written")
def nothing_written(ctx: dict[str, Any]) -> None:
    assert ctx["written"] is False


@then("the write is accepted")
def accepted(ctx: dict[str, Any]) -> None:
    assert ctx["written"] is True


@then(
    parsers.parse(
        "the stored snapshot is at sheet version {version:d} "
        "with the stats of the worked-example game"
    )
)
def stored_is(ctx: dict[str, Any], version: int) -> None:
    key = SnapshotKey(ctx["match_id"], ctx["dictionary"].version, "PROVISIONAL-UNVERIFIED")
    stored = ctx["repo"].get(key)
    assert stored is not None
    assert stored.sheet_version == version
    assert stored.stats == starter_stats(one_game(WORKED_EXAMPLE))


@then(parsers.parse('the computation is refused naming "{metric}"'))
def refused(ctx: dict[str, Any], metric: str) -> None:
    assert "snapshot" not in ctx
    assert metric in str(ctx["refused"])


@then(parsers.parse("the match has {count:d} stored snapshots"))
def stored_count(ctx: dict[str, Any], count: int) -> None:
    rows = (
        ctx["session"]
        .execute(sa.select(sa.func.count()).where(metric_snapshots.c.match_id == ctx["match_id"]))
        .scalar_one()
    )
    assert rows == count


@then(
    parsers.parse(
        'the snapshot keyed by the shipped dictionary and "{rules}" is at sheet version {version:d}'
    )
)
def keyed_by_shipped(ctx: dict[str, Any], rules: str, version: int) -> None:
    stored = ctx["repo"].get(SnapshotKey(ctx["match_id"], load_dictionary().version, rules))
    assert stored is not None
    assert stored.sheet_version == version
