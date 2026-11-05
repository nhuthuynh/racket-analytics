"""ST-076b (NFR-045.3): the confirmed-corrections fingerprint over stored rows is (count,
SHA-256) in a stable order. Pure: rows in, fingerprint out; no database (IT-05-04 has it).
The session query is pinned here with a fake session and the compiled Postgres SQL, so the
nightly mutation step (unit tests only) covers the live-match filter (PR #209 review round 2)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, cast

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session

from racket.matches.scorebook.integrity import (
    Fingerprint,
    corrections_fingerprint,
    fingerprint_of,
)

pytestmark = pytest.mark.unit

EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
M1 = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
M2 = uuid.UUID("00000000-0000-0000-0000-0000000000a2")
AT = datetime(2026, 11, 5, 9, 30, 0, 123456, tzinfo=UTC)


def row(n: int, *, match_id: uuid.UUID = M1, version: int | None = None, **over: Any) -> dict:
    base = {
        "id": uuid.UUID(int=n),
        "match_id": match_id,
        "version": n if version is None else version,
        "kind": "correction",
        "actor_id": uuid.UUID(int=99),
        "at": AT + timedelta(seconds=n),
        "rally_id": uuid.UUID(int=1000 + n),
        "game_number": 1,
        "field": "ending",
        "old_value": "fault",
        "new_value": "winner",
        "undoes": None,
    }
    return {**base, **over}


def test_empty_table_is_count_zero_and_the_digest_of_no_bytes() -> None:
    assert fingerprint_of([]) == Fingerprint(0, EMPTY_SHA256)


def test_fingerprint_unpacks_as_count_and_sha256() -> None:
    count, digest = fingerprint_of([row(1)])
    assert count == 1
    assert len(digest) == 64
    assert int(digest, 16) >= 0


def test_one_row_hashes_its_canonical_json_line() -> None:
    expected_line = json.dumps(
        {
            "actor_id": str(uuid.UUID(int=99)),
            "at": "2026-11-05T09:30:01.123456+00:00",
            "field": "ending",
            "game_number": 1,
            "id": str(uuid.UUID(int=1)),
            "kind": "correction",
            "match_id": str(M1),
            "new_value": "winner",
            "old_value": "fault",
            "rally_id": str(uuid.UUID(int=1001)),
            "undoes": None,
            "version": 1,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    assert (
        fingerprint_of([row(1)]).sha256
        == hashlib.sha256((expected_line + "\n").encode()).hexdigest()
    )


def test_order_of_the_input_rows_does_not_change_the_fingerprint() -> None:
    rows = [row(1), row(2), row(3, match_id=M2, version=1), row(4, match_id=M2, version=2)]
    assert fingerprint_of(rows) == fingerprint_of(list(reversed(rows)))
    assert fingerprint_of(rows) == fingerprint_of([rows[2], rows[0], rows[3], rows[1]])


def test_rows_are_ordered_by_match_then_version_then_id() -> None:
    a, b = row(1, match_id=M2, version=1), row(2, match_id=M1, version=5)
    c = row(3, match_id=M1, version=5, id=uuid.UUID(int=0))  # same version, lower id
    chained = hashlib.sha256()
    for r in (c, b, a):  # M1 v5 id0, M1 v5 id2, M2 v1
        chained.update(_line(r))
    assert fingerprint_of([a, b, c]).sha256 == chained.hexdigest()


def _line(r: dict) -> bytes:
    """Recomputes one canonical line the way the module is specified to (sorted keys)."""
    out = {k: (str(v) if isinstance(v, uuid.UUID) else v) for k, v in r.items()}
    out["at"] = r["at"].astimezone(UTC).isoformat()
    return (json.dumps(out, sort_keys=True, separators=(",", ":")) + "\n").encode()


def test_a_missing_row_changes_count_and_digest() -> None:
    rows = [row(1), row(2), row(3)]
    full, lost = fingerprint_of(rows), fingerprint_of(rows[:2])
    assert lost.count == full.count - 1
    assert lost.sha256 != full.sha256


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("kind", "undo"),
        ("actor_id", uuid.UUID(int=98)),
        ("at", AT + timedelta(microseconds=1)),
        ("rally_id", None),
        ("game_number", 2),
        ("field", "winning_side"),
        ("old_value", {"side": "A"}),
        ("new_value", None),
        ("undoes", uuid.UUID(int=7)),
        ("version", 9),
        ("match_id", M2),
        ("id", uuid.UUID(int=55)),
    ],
)
def test_any_changed_column_changes_the_digest(field: str, value: Any) -> None:
    assert fingerprint_of([row(1, **{field: value})]).sha256 != fingerprint_of([row(1)]).sha256


def test_same_instant_in_another_time_zone_is_the_same_row() -> None:
    plus_two = timezone(timedelta(hours=2))
    shifted = row(1, at=(AT + timedelta(seconds=1)).astimezone(plus_two))
    assert fingerprint_of([shifted]) == fingerprint_of([row(1)])


def test_key_order_inside_json_values_does_not_change_the_digest() -> None:
    one = row(1, new_value={"a": 1, "b": [1, 2]})
    two = row(1, new_value={"b": [1, 2], "a": 1})
    assert fingerprint_of([one]) == fingerprint_of([two])


def test_a_naive_timestamp_is_refused() -> None:
    with pytest.raises(ValueError, match="time zone"):
        fingerprint_of([row(1, at=datetime(2026, 11, 5, 9, 30))])


LIVE_CORRECTIONS_SQL = (
    "SELECT match_corrections.id, match_corrections.match_id, match_corrections.version, "
    "match_corrections.kind, match_corrections.actor_id, match_corrections.at, "
    "match_corrections.rally_id, match_corrections.game_number, match_corrections.field, "
    "match_corrections.old_value, match_corrections.new_value, match_corrections.undoes "
    "FROM match_corrections "
    "WHERE match_corrections.match_id IN "
    "(SELECT matches.id FROM matches WHERE matches.deleted_at IS NULL)"
)


class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeSession:
    """Records each statement it is asked to run and answers with the given rows."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.statements: list[Any] = []

    def execute(self, statement: Any) -> _FakeResult:
        self.statements.append(statement)
        return _FakeResult(self.rows)


def _sql(statement: Any) -> str:
    compiled = statement.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    return " ".join(str(compiled).split())


def test_session_query_reads_every_column_of_the_corrections_of_live_matches_only() -> None:
    session = _FakeSession([])
    corrections_fingerprint(cast(Session, session))
    assert len(session.statements) == 1  # one statement, one snapshot
    assert _sql(session.statements[0]) == LIVE_CORRECTIONS_SQL


def test_session_rows_are_fingerprinted_as_stored_rows() -> None:
    rows = [row(2), row(1), row(3, match_id=M2, version=1)]
    assert corrections_fingerprint(cast(Session, _FakeSession(rows))) == fingerprint_of(rows)


def test_an_empty_session_result_is_count_zero() -> None:
    empty = corrections_fingerprint(cast(Session, _FakeSession([])))
    assert empty == Fingerprint(0, EMPTY_SHA256)
