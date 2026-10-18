"""The scope memo (FIX-04-2b; G04-02 c; coaching-plan §3 scope).

The owner's weakness ranking and citation facts are a function of the scope: the owner's live
matches, each with its ``is_me`` side and scorebook version (every tag, correction or undo
bumps the version). ``GET /me/plan`` reads the scope key under the same share locks the live
read takes and reuses the facts only for an equal key; any other key is a miss and the facts are
read live. One entry per owner, least recently read dropped first; thread safe (sync routes run
in a thread pool). Per process: a key read from the database is the truth, so processes never
need to agree.
"""

from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from collections.abc import Hashable
from typing import Generic, TypeVar

ScopeKey = tuple[Hashable, ...]
_V = TypeVar("_V")


class ScopeMemo(Generic[_V]):
    def __init__(self, *, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._capacity = capacity
        self._entries: OrderedDict[uuid.UUID, tuple[ScopeKey, _V]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, owner_id: uuid.UUID, key: ScopeKey) -> _V | None:
        with self._lock:
            found = self._entries.get(owner_id)
            if found is None or found[0] != key:
                return None
            self._entries.move_to_end(owner_id)
            return found[1]

    def put(self, owner_id: uuid.UUID, key: ScopeKey, value: _V) -> None:
        with self._lock:
            self._entries[owner_id] = (key, value)
            self._entries.move_to_end(owner_id)
            while len(self._entries) > self._capacity:
                self._entries.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
