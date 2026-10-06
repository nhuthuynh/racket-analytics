"""Object keys written by THIS test's in-process API and worker (QA-R3-02, retro A2).

Upload tests used to diff the whole bucket (``set(list_keys()) - before``). On a shared object
store a neighbouring test (or a parallel run) adds or removes objects in between, so those
assertions failed by order and neighbour, not by behaviour. ``WrittenKeys`` instead records the
key of every write made through ``ObjectStore`` (``put_bytes``, ``create_multipart``,
``upload_part``, ``complete_multipart``: the only S3 writes in ``racket.platform.storage``) while
the test runs, whatever generated the key, and reports which of those objects still exist.
Writes by other processes are not recorded, so neighbours can no longer change the result.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.support import contract

WRITE_METHODS = ("put_bytes", "create_multipart", "upload_part", "complete_multipart")


class WrittenKeys:
    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.written: list[str] = []
        store_class = contract.OBJECT_STORE.load()
        for name in WRITE_METHODS:
            monkeypatch.setattr(store_class, name, self._recording(getattr(store_class, name)))

    def _recording(self, real: Any) -> Any:
        def write(store: Any, key: str, *args: Any, **kwargs: Any) -> Any:
            if key not in self.written:
                self.written.append(key)
            return real(store, key, *args, **kwargs)

        return write

    def stored(self) -> set[str]:
        """The recorded keys whose object exists now."""
        store = contract.OBJECT_STORE.load().from_settings()
        return {key for key in self.written if store.size_of(key) is not None}
