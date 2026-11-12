"""The projected-sheet memo (CI-NIGHTLY-PERF; NFR-010 dashboard, NFR-013; analytics-snapshots.md
§4.2). A dashboard read reuses the projected sheet of a match only for the scorebook version it
read under the match row share lock; any other version is a miss and the sheet is read live.
Negative cases first."""

from __future__ import annotations

import threading
import uuid

import pytest

from racket.matches.scorebook.memo import SheetMemo

pytestmark = [pytest.mark.unit]

M1, M2, M3 = (uuid.UUID(int=n) for n in (1, 2, 3))


def test_a_capacity_below_one_is_refused() -> None:
    with pytest.raises(ValueError):
        SheetMemo(capacity=0)


def test_an_unknown_match_is_a_miss() -> None:
    assert SheetMemo(capacity=2).get(M1, (1, "r1")) is None


def test_another_version_of_the_same_match_is_a_miss() -> None:
    memo = SheetMemo[dict[str, int]](capacity=2)
    memo.put(M1, (4, "r1"), {"rows": 4})
    assert memo.get(M1, (5, "r1")) is None
    assert memo.get(M1, (4, "r2")) is None


def test_another_match_never_gets_the_sheet() -> None:
    memo = SheetMemo[dict[str, int]](capacity=2)
    memo.put(M1, (4, "r1"), {"rows": 4})
    assert memo.get(M2, (4, "r1")) is None


def test_a_newer_version_replaces_the_older_one() -> None:
    memo = SheetMemo[str](capacity=2)
    memo.put(M1, (4, "r1"), "v4")
    memo.put(M1, (5, "r1"), "v5")
    assert memo.get(M1, (4, "r1")) is None
    assert memo.get(M1, (5, "r1")) == "v5"
    assert len(memo) == 1


def test_the_same_version_is_a_hit() -> None:
    memo = SheetMemo[str](capacity=2)
    memo.put(M1, (4, "r1"), "v4")
    assert memo.get(M1, (4, "r1")) == "v4"


def test_the_least_recently_read_match_goes_first() -> None:
    memo = SheetMemo[str](capacity=2)
    memo.put(M1, (1, "r1"), "m1")
    memo.put(M2, (1, "r1"), "m2")
    assert memo.get(M1, (1, "r1")) == "m1"  # M2 is now the least recently read
    memo.put(M3, (1, "r1"), "m3")
    assert memo.get(M2, (1, "r1")) is None
    assert memo.get(M1, (1, "r1")) == "m1"
    assert memo.get(M3, (1, "r1")) == "m3"
    assert len(memo) == 2


def test_parallel_readers_keep_the_capacity() -> None:
    memo = SheetMemo[int](capacity=8)
    ids = [uuid.UUID(int=n) for n in range(64)]

    def work(offset: int) -> None:
        for i, match_id in enumerate(ids):
            memo.put(match_id, (offset, "r1"), i)
            memo.get(ids[(i * 7) % len(ids)], (offset, "r1"))

    threads = [threading.Thread(target=work, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(memo) == 8
