"""PE-R3S3-03-ITS (PE-R3S3-03 / SEC-R3S3-02 / QA-R3S3-05; FR-006, FR-007, NFR-066 b, NFR-047;
threat notes T-DL-3, T-DL-4, T-AC-2, T-AC-3; deletion-and-purge.md §3.3, §4.2, §4.6, §6;
analytics-snapshots.md §4.2 invariant S8; ADR 0045): the deletion and purge safety ITs that
review round 3 found missing. Real app, Postgres and object store. Negative cases first.

T-DL-3, two owners and ``DELETE /me`` (extends ``test_st_050b_purge_refs_fail_closed``, which
covers ``DELETE /matches/{id}``):
  1. Ivy's media row is rewritten so that it names Carlos's original key. The pass
     refuses that match before any store call (exit 1, ``purge.failed`` stage ``objects``);
     Carlos's bytes, parts and rows are unchanged; Ivy's account tombstone stays.
  2. Each owner has a received match (original) and an open upload (one part, one staged
     chunk). After Ivy deletes her account, one pass leaves nothing of Ivy and Carlos's objects
     byte-for-byte (sha256), his open part and his rows unchanged.
T-DL-4, held recompute and orphan sweep:
  3. A recompute held across ``DELETE /matches/{id}`` and released after it writes no snapshot,
     nor after the pass.
  4. A recompute that holds the match ``FOR SHARE`` makes ``DELETE`` wait; its snapshot is then
     purged with the match.
  5. A snapshot row whose match row is gone is swept by one pass (``purge.orphan_swept``); a
     live match's snapshot stays.
T-AC-2:
  6. 20 x ``POST /matches`` racing ``DELETE /me``: every answer is 201 or 401, no live match of
     a deleted account exists even before the pass, one pass leaves no row of the account, and
     a create after the delete is a 401.
T-AC-3 (the magic-link half is ``test_st_051_lock_order``):
  7. A rally video link taken before ``DELETE /me`` returns 404 after the purge, and the match
     answers 404 to whoever signs in next.

The guarded code landed before these ITs, so they cannot be red first (TDD-order breach,
retro 3 M4). Each was shown to fail by mutating its guarded line once: see
docs/sprints/03/decisions/PE-R3S3-03-ITS.md. A new file, so no TCR row is needed.
"""

from __future__ import annotations

import threading
import uuid
from typing import Any

import pytest
import sqlalchemy as sa

from tests.support import purge_safety as ps
from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver, sign_in

RACING_CREATES = 20


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Any:
    st.with_statuses(monkeypatch, tmp_path)
    yield
    st.clear_dictionary_cache()


def _account_row(engine: Any, account_id: str) -> dict[str, Any] | None:
    with engine.connect() as conn:
        row = (
            conn.execute(
                sa.text("SELECT email, deleted_at FROM accounts WHERE id = :id"),
                {"id": account_id},
            )
            .mappings()
            .first()
        )
    return None if row is None else dict(row)


# ------------------------------------------------------------------ T-DL-3
def test_t_dl_3_a_rewritten_key_naming_the_other_owners_video_stops_the_account_purge(
    api: ApiDriver,
    committed_db: Any,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    ivy_id = st.me_id(api, "ivy")
    ivy = ps.received(api, "ivy", "T-DL-3 ivy")
    carlos = ps.received(api, "carlos", "T-DL-3 carlos")
    carlos_open = ps.open_upload(api, "carlos", "T-DL-3 carlos open")
    (carlos_key,) = st.object_keys_of(committed_db, carlos)
    carlos_has = [ps.holdings(committed_db, m) for m in (carlos, carlos_open)]
    assert carlos_has[0]["objects"][carlos_key] is not None  # positive control: it is stored
    assert st.delete_account(api, "ivy").status_code in st.statscontract.DELETE_OK
    with committed_db.begin() as conn:  # a corrupted row: Ivy's media names Carlos's video
        conn.execute(
            sa.text("UPDATE media_assets SET object_key = :k WHERE match_id::text = :m"),
            {"k": carlos_key, "m": ivy},
        )
    ivy_rows = st.rows_holding(committed_db, [ivy])
    carlos_rows = st.rows_holding(committed_db, [carlos, carlos_open])
    calls = ps.spy_store(monkeypatch)

    rc, lines = ps.purge(capfd)

    assert calls == [], f"the purge called the store for a refused match: {calls}"
    assert rc == 1, f"purge --once exit {rc}: a refused match must fail the pass"
    failed = [
        (r.get("match_id"), r.get("stage"), r.get("error"))
        for r in ps.events(lines, "purge.failed")
    ]
    assert failed == [(ivy, "objects", "UnsafeObjectRef")], failed
    now = [ps.holdings(committed_db, m) for m in (carlos, carlos_open)]
    assert now == carlos_has, "Carlos's objects changed"
    assert st.rows_holding(committed_db, [carlos, carlos_open]) == carlos_rows
    assert st.rows_holding(committed_db, [ivy]) == ivy_rows, "a refused match keeps its rows"
    account = _account_row(committed_db, ivy_id)
    assert account is not None, "the account went before its match"
    assert account["deleted_at"] is not None


def test_t_dl_3_deleting_one_owner_leaves_the_other_owners_objects_byte_for_byte(
    api: ApiDriver, committed_db: Any, capfd: pytest.CaptureFixture[str]
) -> None:
    ivy_id = st.me_id(api, "ivy")
    ivy = [ps.received(api, "ivy", "T-DL-3 ivy"), ps.open_upload(api, "ivy", "T-DL-3 ivy open")]
    carlos = [
        ps.received(api, "carlos", "T-DL-3 carlos"),
        ps.open_upload(api, "carlos", "T-DL-3 carlos open"),
    ]
    ivy_has = [ps.holdings(committed_db, m) for m in ivy]
    carlos_has = [ps.holdings(committed_db, m) for m in carlos]
    for has in (*ivy_has, *carlos_has):  # positive controls: every object is there
        assert has["objects"], has
        assert None not in has["objects"].values(), has
    assert list(carlos_has[1]["parts"].values()) == [[1]]  # his open upload holds one part
    carlos_rows = st.rows_holding(committed_db, carlos)

    assert st.delete_account(api, "ivy").status_code in st.statscontract.DELETE_OK
    rc, lines = ps.purge(capfd)

    assert rc == 0, [r for r in lines if r.get("level") in ("error", "ERROR")]
    assert [ps.holdings(committed_db, m) for m in carlos] == carlos_has, "Carlos's objects changed"
    assert st.rows_holding(committed_db, carlos) == carlos_rows, "Carlos's rows changed"
    assert ps.left(committed_db, [ivy_id, *ivy]) == {}
    gone = [k for has in ivy_has for k in has["objects"]]
    assert ps.digests(gone) == dict.fromkeys(gone), "an object of Ivy is still stored"
    assert _account_row(committed_db, ivy_id) is None


# ------------------------------------------------------------------ T-DL-4
def test_t_dl_4_a_recompute_held_across_the_delete_writes_no_snapshot(
    api: ApiDriver,
    committed_db: Any,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    published: None,
) -> None:
    with ps.held_recomputes(monkeypatch) as held:
        match_id = sb.ready_tagged_match(api, "ivy", title="T-DL-4 held")
    assert held, "no recompute was held, so the test proves nothing"
    assert ps.snapshot_rows(committed_db, match_id) == 0  # nothing computed yet
    assert st.delete_match(api, "ivy", match_id).status_code in st.statscontract.DELETE_OK

    ps.release(held[-1], committed_db)  # the late recompute arrives after the delete commit

    assert ps.snapshot_rows(committed_db, match_id) == 0, "a snapshot of a deleted match"
    rc, _ = ps.purge(capfd)
    assert rc == 0
    ps.release(held[-1], committed_db)  # ... or only after the pass
    assert ps.snapshot_rows(committed_db, match_id) == 0, "a snapshot after the purge"
    assert ps.left(committed_db, [match_id]) == {}


def test_t_dl_4_a_recompute_holding_the_match_makes_the_delete_wait_then_both_go(
    api: ApiDriver,
    committed_db: Any,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
    published: None,
) -> None:
    from racket.analytics.repository import SnapshotRepository

    with ps.held_recomputes(monkeypatch) as held:
        match_id = sb.ready_tagged_match(api, "ivy", title="T-DL-4 lock")
    assert held, "no recompute was held, so the test proves nothing"
    seen: dict[str, Any] = {}
    in_upsert, go_on = threading.Event(), threading.Event()
    real_upsert = SnapshotRepository.upsert

    def paused_upsert(self: Any, snapshot: Any) -> None:  # the recompute pauses before writing
        seen["pid"] = self.session.execute(sa.text("SELECT pg_backend_pid()")).scalar_one()
        in_upsert.set()
        go_on.wait(15)
        real_upsert(self, snapshot)

    def watch() -> None:  # DELETE must queue behind the recompute's FOR SHARE lock
        seen["waited"] = ps.wait_until(lambda: ps.blocked_by(committed_db, seen["pid"]), 5)
        go_on.set()

    monkeypatch.setattr(SnapshotRepository, "upsert", paused_upsert)
    recompute = threading.Thread(target=ps.release, args=(held[-1], committed_db))
    recompute.start()
    assert in_upsert.wait(10), "the recompute never reached its write"
    watcher = threading.Thread(target=watch)
    watcher.start()
    try:
        deleted = st.delete_match(api, "ivy", match_id)
    finally:
        go_on.set()
        watcher.join(15)
        recompute.join(15)

    assert seen.get("waited"), "DELETE did not wait for the recompute holding the match"
    assert deleted.status_code in st.statscontract.DELETE_OK, deleted.text
    assert ps.snapshot_rows(committed_db, match_id) == 1  # written before the tombstone
    rc, _ = ps.purge(capfd)
    assert rc == 0
    assert ps.snapshot_rows(committed_db, match_id) == 0
    assert ps.left(committed_db, [match_id]) == {}


def test_t_dl_4_a_snapshot_whose_match_is_gone_is_swept_and_a_live_ones_stays(
    api: ApiDriver,
    committed_db: Any,
    capfd: pytest.CaptureFixture[str],
    published: None,
) -> None:
    owner = st.me_id(api, "ivy")
    live = sb.ready_tagged_match(api, "ivy", title="T-DL-4 live")
    st.stats_body(api, "ivy", live)  # the live match has its snapshot
    live_rows = ps.snapshot_rows(committed_db, live)
    assert live_rows >= 1
    orphan = str(uuid.uuid4())  # no matches row has this id
    ps.insert_snapshot(committed_db, orphan, owner)
    assert ps.snapshot_rows(committed_db, orphan) == 1

    rc, lines = ps.purge(capfd)

    assert rc == 0
    assert ps.snapshot_rows(committed_db, orphan) == 0, "the orphan snapshot survived the pass"
    swept = [r.get("match_id") for r in ps.events(lines, "purge.orphan_swept")]
    assert swept == [orphan], swept
    assert ps.snapshot_rows(committed_db, live) == live_rows, "a live match lost its snapshot"


# ------------------------------------------------------------------ T-AC-2
def test_t_ac_2_creates_racing_delete_me_leave_no_match_behind(
    api: ApiDriver, committed_db: Any, capfd: pytest.CaptureFixture[str]
) -> None:
    ivy_id = st.me_id(api, "ivy")
    carlos = ps.received(api, "carlos", "T-AC-2 carlos")
    carlos_rows = st.rows_holding(committed_db, [carlos])

    deleted, creates = ps.race_creates_against_delete_me(api, "ivy", RACING_CREATES)

    assert deleted == 202
    assert sorted({status for status, _ in creates}) <= [201, 401], creates
    assert ps.live_matches_of_deleted_accounts(committed_db) == 0, (
        "a create committed after DELETE /me: a live match of a deleted account"
    )
    created = [m for status, m in creates if status == 201 and m]
    rc, _ = ps.purge(capfd)
    assert rc == 0
    assert ps.left(committed_db, [ivy_id, *created]) == {}
    assert _account_row(committed_db, ivy_id) is None
    assert st.rows_holding(committed_db, [carlos]) == carlos_rows
    late = api.run(api.as_user("ivy").post("/matches", json=sb.doubles_body("too late")))
    assert late.status_code == 401, late.text


# ------------------------------------------------------------------ T-AC-3
def test_t_ac_3_a_rally_link_taken_before_delete_me_is_a_404_after_the_purge(
    api: ApiDriver, committed_db: Any, capfd: pytest.CaptureFixture[str]
) -> None:
    ivy_id = st.me_id(api, "ivy")
    match_id = sb.ready_tagged_match(api, "ivy", title="T-AC-3")
    link = ps.rally_link(api, "ivy", match_id)
    assert ps.fetch(link) == 206  # positive control: the link plays

    assert st.delete_account(api, "ivy").status_code in st.statscontract.DELETE_OK
    rc, _ = ps.purge(capfd)

    assert rc == 0
    assert ps.fetch(link) == 404, "the old rally link still reaches the video"
    assert ps.left(committed_db, [ivy_id, match_id]) == {}
    api.run(sign_in(api.as_user("ivy"), "ivy"))  # Ivy again: a new, empty account (PM-1)
    method, url = st.statscontract.path("match", match_id=match_id)
    again = api.request("ivy", method, url)
    assert again.status_code == 404, again.text
