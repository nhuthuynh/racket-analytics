"""API binding of tests/features/deletion_and_purge_safety.feature (PE-R3S3-03-ITS; FR-006,
FR-007, NFR-066; threat notes T-DL-3, T-DL-4, T-AC-2, T-AC-3; ADR 0045). Real app, Postgres
and object store through ``tests.support.purge_safety``. The integration file
``test_pe_r3s3_03_deletion_and_purge_safety.py`` holds the heavier variants (corrupted rows,
the held ``FOR SHARE`` lock, 20 racing creates). A new file: no TCR row is needed.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.support import purge_safety as ps
from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

scenarios("deletion_and_purge_safety.feature")

RACING_CREATES = 6  # the scenario's light race; the IT runs 20


@pytest.fixture
def ctx(
    api: ApiDriver,
    committed_db: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    capfd: pytest.CaptureFixture[str],
) -> Iterator[dict[str, Any]]:
    st.with_statuses(monkeypatch, tmp_path)
    yield {"api": api, "db": committed_db, "mp": monkeypatch, "capfd": capfd}
    st.clear_dictionary_cache()


def _purge(ctx: dict[str, Any]) -> None:
    rc, ctx["lines"] = ps.purge(ctx["capfd"])
    assert rc == 0, [r for r in ctx["lines"] if r.get("event") == "purge.failed"]


def _delete_account_and_purge(ctx: dict[str, Any]) -> None:
    response = st.delete_account(ctx["api"], "ivy")
    assert response.status_code in st.statscontract.DELETE_OK, response.text
    _purge(ctx)


# ------------------------------------------------------------------ T-DL-3
@given("Ivy and Carlos each have a match with its video stored")
def two_owners(ctx: dict[str, Any]) -> None:
    api, db = ctx["api"], ctx["db"]
    ctx["ivy_id"] = st.me_id(api, "ivy")
    ctx["ivy"] = ps.received(api, "ivy", "purge safety ivy")
    ctx["carlos"] = ps.received(api, "carlos", "purge safety carlos")
    ctx["ivy_has"] = ps.holdings(db, ctx["ivy"])
    ctx["carlos_has"] = ps.holdings(db, ctx["carlos"])
    ctx["carlos_rows"] = st.rows_holding(db, [ctx["carlos"]])
    assert None not in ctx["carlos_has"]["objects"].values()


@when("Ivy deletes her account and the clean-up runs")
@when("she deletes her account and the clean-up runs")
def delete_account_and_purge(ctx: dict[str, Any]) -> None:
    _delete_account_and_purge(ctx)


@then("none of Ivy's matches, videos or profile remain stored")
def nothing_of_ivy(ctx: dict[str, Any]) -> None:
    assert ps.left(ctx["db"], [ctx["ivy_id"], ctx["ivy"]]) == {}
    gone = list(ctx["ivy_has"]["objects"])
    assert ps.digests(gone) == dict.fromkeys(gone)


@then("Carlos's video and match are exactly as they were")
def carlos_intact(ctx: dict[str, Any]) -> None:
    assert ps.holdings(ctx["db"], ctx["carlos"]) == ctx["carlos_has"]
    assert st.rows_holding(ctx["db"], [ctx["carlos"]]) == ctx["carlos_rows"]


# ------------------------------------------------------------------ T-DL-4
@given("Ivy has a tagged match whose stats update has not arrived yet")
def held_update(ctx: dict[str, Any]) -> None:
    with ps.held_recomputes(ctx["mp"]) as held:
        ctx["match"] = sb.ready_tagged_match(ctx["api"], "ivy", title="purge safety held")
    assert held
    ctx["held"] = held[-1]
    assert ps.snapshot_rows(ctx["db"], ctx["match"]) == 0


@when("she deletes the match and the stats update then arrives")
def delete_then_update(ctx: dict[str, Any]) -> None:
    response = st.delete_match(ctx["api"], "ivy", ctx["match"])
    assert response.status_code in st.statscontract.DELETE_OK, response.text
    ps.release(ctx["held"], ctx["db"])


@then("no stats are stored for the deleted match, before or after the clean-up")
def no_stats(ctx: dict[str, Any]) -> None:
    assert ps.snapshot_rows(ctx["db"], ctx["match"]) == 0
    _purge(ctx)
    ps.release(ctx["held"], ctx["db"])
    assert ps.snapshot_rows(ctx["db"], ctx["match"]) == 0
    assert ps.left(ctx["db"], [ctx["match"]]) == {}


@given("stats are stored for a match that no longer exists")
def orphan_stats(ctx: dict[str, Any]) -> None:
    ctx["orphan"] = str(uuid.uuid4())
    ps.insert_snapshot(ctx["db"], ctx["orphan"], st.me_id(ctx["api"], "ivy"))
    assert ps.snapshot_rows(ctx["db"], ctx["orphan"]) == 1


@when("the clean-up runs")
def clean_up(ctx: dict[str, Any]) -> None:
    _purge(ctx)


@then("those stats are gone and the sweep is logged with the match id")
def orphan_gone(ctx: dict[str, Any]) -> None:
    assert ps.snapshot_rows(ctx["db"], ctx["orphan"]) == 0
    swept = [r.get("match_id") for r in ps.events(ctx["lines"], "purge.orphan_swept")]
    assert swept == [ctx["orphan"]]


# ------------------------------------------------------------------ T-AC-2
@given("Ivy is creating several matches")
def creating(ctx: dict[str, Any]) -> None:
    ctx["ivy_id"] = st.me_id(ctx["api"], "ivy")


@when("she deletes her account while those requests are in flight")
def delete_during_creates(ctx: dict[str, Any]) -> None:
    deleted, ctx["creates"] = ps.race_creates_against_delete_me(ctx["api"], "ivy", RACING_CREATES)
    assert deleted == 202
    assert {status for status, _ in ctx["creates"]} <= {201, 401}, ctx["creates"]


@then("no match of hers is left live, and after the clean-up nothing of hers remains")
def nothing_left_after_race(ctx: dict[str, Any]) -> None:
    assert ps.live_matches_of_deleted_accounts(ctx["db"]) == 0
    _purge(ctx)
    created = [m for status, m in ctx["creates"] if status == 201 and m]
    assert ps.left(ctx["db"], [ctx["ivy_id"], *created]) == {}


# ------------------------------------------------------------------ T-AC-3
@given("Ivy copied the video link of a rally")
def copied_link(ctx: dict[str, Any]) -> None:
    match_id = sb.ready_tagged_match(ctx["api"], "ivy", title="purge safety link")
    ctx["link"] = ps.rally_link(ctx["api"], "ivy", match_id)
    assert ps.fetch(ctx["link"]) == 206


@then("the copied link answers not found")
def link_not_found(ctx: dict[str, Any]) -> None:
    assert ps.fetch(ctx["link"]) == 404
