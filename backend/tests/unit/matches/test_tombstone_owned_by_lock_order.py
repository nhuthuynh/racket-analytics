"""SQA-051-01 (ST-051; deletion-and-purge.md §3.1 global lock order): ``tombstone_owned_by``
(``DELETE /me`` step 3 and the purge's second net) locks each match's upload row before it
writes the match row, as ``DELETE /matches/{id}`` and the completing tus PATCH do; otherwise
the two deadlock. No I/O: the session and the upload port are recorders. Negative case first.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from racket.matches import public as matches_public

pytestmark = [pytest.mark.unit]

AT = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
OWNER = uuid.uuid4()


class _Result:
    def __init__(self, ids: list[uuid.UUID]) -> None:
        self.ids = ids

    def scalars(self) -> list[uuid.UUID]:
        return self.ids


class _Session:
    """``SELECT`` of the live ids answers ``live``; an ``UPDATE`` of one match answers it."""

    def __init__(self, calls: list[str], live: list[uuid.UUID], gone: set[uuid.UUID]) -> None:
        self.calls, self.live, self.gone = calls, live, gone

    def execute(self, statement: Any) -> _Result:
        if statement.is_select:
            self.calls.append("read_live_ids")
            return _Result(self.live)
        ids = [v for k, v in statement.compile().params.items() if k.startswith("id")]
        if not ids:  # every match of the owner in one statement, no upload row locked first
            self.calls.append("update_all_matches")
            return _Result([m for m in self.live if m not in self.gone])
        match_id = ids[0]
        self.calls.append(f"update_match:{match_id}")
        return _Result([] if match_id in self.gone else [match_id])


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    recorded: list[str] = []
    monkeypatch.setattr(
        matches_public, "lock_upload_of_match",
        lambda session, m: recorded.append(f"lock_upload:{m}"), raising=False,
    )  # fmt: skip
    monkeypatch.setattr(
        matches_public, "close_for_deleted_match",
        lambda session, m, at: recorded.append(f"close_upload:{m}"),
    )  # fmt: skip
    return recorded


def test_a_match_tombstoned_meanwhile_is_neither_returned_nor_closed(calls: list[str]) -> None:
    gone = uuid.uuid4()
    ids = matches_public.tombstone_owned_by(_Session(calls, [gone], {gone}), OWNER, AT)  # type: ignore[arg-type]
    assert ids == []
    assert calls == ["read_live_ids", f"lock_upload:{gone}", f"update_match:{gone}"]


def test_each_upload_row_is_locked_before_its_match_row(calls: list[str]) -> None:
    first, second = sorted([uuid.uuid4(), uuid.uuid4()])
    ids = matches_public.tombstone_owned_by(_Session(calls, [second, first], set()), OWNER, AT)  # type: ignore[arg-type]
    assert ids == [first, second]
    assert calls == [
        "read_live_ids",
        f"lock_upload:{first}", f"update_match:{first}", f"close_upload:{first}",
        f"lock_upload:{second}", f"update_match:{second}", f"close_upload:{second}",
    ]  # fmt: skip
