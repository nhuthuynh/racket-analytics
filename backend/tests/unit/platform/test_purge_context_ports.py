"""The purge's composition-root ports (``racket.platform.purge.ContextPorts``) with each
context's published port faked (PE-R3S3-03-ITS; deletion-and-purge.md §4.2; ADR 0045).

These are the decisions the pass makes between two contexts, which no context owns:

* T-DL-4 second net: an orphan snapshot is a snapshot whose match has **no** ``matches`` row.
  A tombstoned match is not an orphan (its own purge removes its snapshot). Every page of
  snapshot ids is checked, not only the first.
* T-AC-2 second net: every live match of a deleted account is tombstoned and logged.
* An account is due only when no match row of it is left, and is claimed only then.

Negative cases first. The live-stack ITs are
``tests/integration/test_pe_r3s3_03_deletion_and_purge_safety.py``.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from racket.platform import purge

pytestmark = [pytest.mark.unit]

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
SESSION = object()


def _ids(*n: int) -> list[uuid.UUID]:
    return [uuid.UUID(int=i) for i in n]


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Snapshot ids, ``matches`` rows (live and tombstoned) and accounts, behind fake ports."""
    state: dict[str, Any] = {
        "snapshots": [],
        "match_rows": set(),
        "tombstoned_accounts": [],
        "live_of": {},
        "owners_with_matches": set(),
        "pages": [],
        "claimable": set(),
    }

    def snapshot_match_ids(session: Any, after: uuid.UUID | None, limit: int) -> list[uuid.UUID]:
        state["pages"].append((after, limit))
        ids = sorted(state["snapshots"])
        if after is not None:
            ids = [i for i in ids if i > after]
        return ids[:limit]

    def existing_ids(session: Any, ids: list[uuid.UUID]) -> set[uuid.UUID]:
        return {i for i in ids if i in state["match_rows"]}

    def tombstoned_account_ids(session: Any, limit: int = 1000) -> list[uuid.UUID]:
        return list(state["tombstoned_accounts"])[:limit]

    def tombstone_owned_by(session: Any, owner: uuid.UUID, at: datetime) -> list[uuid.UUID]:
        assert at == NOW
        return list(state["live_of"].pop(owner, []))

    def owner_has_matches(session: Any, owner: uuid.UUID) -> bool:
        return owner in state["owners_with_matches"]

    def claim_for_purge(session: Any, account: uuid.UUID) -> bool:
        return account in state["claimable"]

    monkeypatch.setattr("racket.analytics.public.snapshot_match_ids", snapshot_match_ids)
    monkeypatch.setattr("racket.matches.public.existing_ids", existing_ids)
    monkeypatch.setattr("racket.players.public.tombstoned_account_ids", tombstoned_account_ids)
    monkeypatch.setattr("racket.matches.public.tombstone_owned_by", tombstone_owned_by)
    monkeypatch.setattr("racket.matches.public.owner_has_matches", owner_has_matches)
    monkeypatch.setattr("racket.players.public.claim_for_purge", claim_for_purge)
    return state


# ------------------------------------------------------------------ T-DL-4 second net
def test_no_snapshot_means_no_orphan(world: dict[str, Any]) -> None:
    assert purge.ContextPorts().orphan_snapshot_ids(SESSION) == []


def test_a_snapshot_of_a_live_or_tombstoned_match_is_not_an_orphan(world: dict[str, Any]) -> None:
    live, tombstoned = _ids(1, 2)
    world["snapshots"] = [live, tombstoned]
    world["match_rows"] = {live, tombstoned}  # a tombstone still has its matches row

    assert purge.ContextPorts().orphan_snapshot_ids(SESSION) == []


def test_a_snapshot_with_no_match_row_is_an_orphan(world: dict[str, Any]) -> None:
    live, gone = _ids(1, 2)
    world["snapshots"] = [live, gone]
    world["match_rows"] = {live}

    assert purge.ContextPorts().orphan_snapshot_ids(SESSION) == [gone]


def test_orphans_on_every_page_are_found(
    world: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(purge, "ORPHAN_PAGE", 2)
    ids = _ids(1, 2, 3, 4, 5)
    world["snapshots"] = ids
    world["match_rows"] = {ids[0], ids[2]}

    found = purge.ContextPorts().orphan_snapshot_ids(SESSION)

    assert found == [ids[1], ids[3], ids[4]]
    assert world["pages"] == [(None, 2), (ids[1], 2), (ids[3], 2), (ids[4], 2)]


# ------------------------------------------------------------------ T-AC-2 second net
def test_a_deleted_account_with_no_live_match_tombstones_nothing(world: dict[str, Any]) -> None:
    world["tombstoned_accounts"] = _ids(9)

    assert purge.ContextPorts().tombstone_deleted_accounts(SESSION, NOW) == []


def test_live_matches_of_a_deleted_account_are_tombstoned_and_logged(
    world: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    account = uuid.UUID(int=9)
    late = _ids(1, 2)
    world["tombstoned_accounts"] = [account]
    world["live_of"] = {account: late}

    with caplog.at_level(logging.INFO, logger="racket.purge"):
        caught = purge.ContextPorts().tombstone_deleted_accounts(SESSION, NOW)

    assert caught == late
    logged = [
        (r.event, r.match_id, r.user_id)  # type: ignore[attr-defined]
        for r in caplog.records
        if getattr(r, "event", None) == "match.deleted"
    ]
    assert logged == [("match.deleted", str(m), str(account)) for m in late]


# ------------------------------------------------------------------ account last
def test_an_account_with_a_match_row_left_is_not_due_nor_claimed(world: dict[str, Any]) -> None:
    account = uuid.UUID(int=9)
    world["tombstoned_accounts"] = [account]
    world["owners_with_matches"] = {account}
    world["claimable"] = {account}
    ports = purge.ContextPorts()

    assert ports.due_accounts(SESSION, 10) == []
    assert ports.claim_account(SESSION, account) is False


def test_an_account_with_no_match_row_left_is_due_and_claimed(world: dict[str, Any]) -> None:
    done, busy = uuid.UUID(int=9), uuid.UUID(int=8)
    world["tombstoned_accounts"] = [done, busy]
    world["owners_with_matches"] = {busy}
    world["claimable"] = {done}
    ports = purge.ContextPorts()

    assert ports.due_accounts(SESSION, 10) == [done]
    assert ports.claim_account(SESSION, done) is True
