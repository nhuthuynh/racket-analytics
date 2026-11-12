"""The projected-sheet memo (CI-NIGHTLY-PERF; NFR-010 dashboard, NFR-013; analytics-snapshots.md
§4.2).

The projected sheet of a match is a pure function of its scorebook, and every scorebook command
bumps the match ``version`` in the transaction that writes the rows (``ScorebookRepository.save``).
``lock_live_sheet`` reads ``(version, rules_version)`` under the match row share lock and reuses
the sheet only for an equal key; any other key is a miss and the scorebook is read live. One
entry per match, least recently read dropped first; thread safe (sync routes run in a thread
pool). Per process: a key read from the database is the truth, so processes never need to
agree. The same shape as Coaching's scope memo (``coaching/plan/scope.py``), kept per context
(context map rule 1).
"""

from __future__ import annotations

import threading
import uuid
from collections import OrderedDict
from collections.abc import Hashable
from typing import Generic, TypeVar

SheetKey = tuple[Hashable, ...]
_V = TypeVar("_V")


class SheetMemo(Generic[_V]):
    def __init__(self, *, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self._capacity = capacity
        self._entries: OrderedDict[uuid.UUID, tuple[SheetKey, _V]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, match_id: uuid.UUID, key: SheetKey) -> _V | None:
        with self._lock:
            found = self._entries.get(match_id)
            if found is None or found[0] != key:
                return None
            self._entries.move_to_end(match_id)
            return found[1]

    def put(self, match_id: uuid.UUID, key: SheetKey, value: _V) -> None:
        with self._lock:
            self._entries[match_id] = (key, value)
            self._entries.move_to_end(match_id)
            while len(self._entries) > self._capacity:
                self._entries.popitem(last=False)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
