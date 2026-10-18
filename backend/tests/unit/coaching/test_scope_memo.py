"""Unit tests: the scope memo (FIX-04-2b; G04-02 c; coaching-plan §3 scope). ``GET /me/plan``
reuses the owner's ranking and citation facts only while the scope key it read (the owner's
live matches with their ``is_me`` side and scorebook version) is the one they were computed
for. Pure; negative cases first."""

from __future__ import annotations

import uuid

import pytest
from racket.coaching.plan.scope import ScopeMemo

pytestmark = [pytest.mark.unit, pytest.mark.coaching]

IVY, CARLOS = uuid.UUID(int=1), uuid.UUID(int=2)
M1, M2 = uuid.UUID(int=11), uuid.UUID(int=12)
KEY = ((M1, "A", 7),)


def test_an_owner_never_read_is_a_miss() -> None:
    assert ScopeMemo[str](capacity=4).get(IVY, KEY) is None


def test_a_changed_scorebook_version_is_a_miss() -> None:
    memo = ScopeMemo[str](capacity=4)
    memo.put(IVY, KEY, "facts at v7")
    assert memo.get(IVY, ((M1, "A", 8),)) is None


def test_a_new_or_deleted_match_or_a_changed_side_is_a_miss() -> None:
    memo = ScopeMemo[str](capacity=4)
    memo.put(IVY, KEY, "facts")
    assert memo.get(IVY, (*KEY, (M2, "A", 1))) is None
    assert memo.get(IVY, ()) is None
    assert memo.get(IVY, ((M1, "B", 7),)) is None


def test_another_owner_never_gets_the_facts_of_an_owner() -> None:
    memo = ScopeMemo[str](capacity=4)
    memo.put(IVY, KEY, "ivy's facts")
    assert memo.get(CARLOS, KEY) is None


def test_a_new_key_replaces_the_owners_old_entry() -> None:
    memo = ScopeMemo[str](capacity=4)
    memo.put(IVY, KEY, "old")
    memo.put(IVY, ((M1, "A", 8),), "new")
    assert memo.get(IVY, KEY) is None
    assert memo.get(IVY, ((M1, "A", 8),)) == "new"
    assert len(memo) == 1


def test_the_least_recently_read_owner_is_dropped_beyond_the_capacity() -> None:
    memo = ScopeMemo[str](capacity=2)
    owners = [uuid.UUID(int=100 + n) for n in range(3)]
    memo.put(owners[0], KEY, "0")
    memo.put(owners[1], KEY, "1")
    assert memo.get(owners[0], KEY) == "0"  # owner 1 is now the least recently read
    memo.put(owners[2], KEY, "2")
    assert memo.get(owners[1], KEY) is None
    assert (memo.get(owners[0], KEY), memo.get(owners[2], KEY)) == ("0", "2")
    assert len(memo) == 2


def test_the_same_key_is_a_hit() -> None:
    memo = ScopeMemo[str](capacity=4)
    memo.put(IVY, KEY, "facts")
    assert memo.get(IVY, ((M1, "A", 7),)) == "facts"


def test_a_capacity_below_one_is_refused() -> None:
    with pytest.raises(ValueError, match="capacity"):
        ScopeMemo[str](capacity=0)
