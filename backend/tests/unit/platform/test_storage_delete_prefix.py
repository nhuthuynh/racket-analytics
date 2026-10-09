"""SEC-S3-TM-01 / T-DL-3 (deletion-and-purge.md §4.6 (4)): ``delete_prefix`` refuses every prefix
but one upload's staging folder before it lists anything. A spy client records the calls."""

from __future__ import annotations

from typing import Any

import pytest

from racket.platform.storage import ObjectStore, S3Config, UnsafeObjectKey

pytestmark = [pytest.mark.unit]

CONFIG = S3Config("media", "http://127.0.0.1:9", "key", "secret", "us-east-1")
HEX = "0123456789abcdef0123456789abcdef"


class Spy:
    def __init__(self, keys: list[str]) -> None:
        self.keys = keys
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get_paginator(self, name: str) -> Any:
        spy = self

        class Pages:
            def paginate(self, **kwargs: Any) -> Any:
                spy.calls.append(("list", kwargs))
                prefix = kwargs.get("Prefix", "")
                return [{"Contents": [{"Key": k} for k in spy.keys if k.startswith(prefix)]}]

        return Pages()

    def delete_object(self, **kwargs: Any) -> None:
        self.calls.append(("delete", kwargs))


def _store(keys: list[str]) -> tuple[ObjectStore, Spy]:
    store = ObjectStore(CONFIG)
    spy = Spy(keys)
    store._client = spy
    return store, spy


@pytest.mark.parametrize(
    "prefix",
    ["", "staging/", "originals/", "staging/../x/", f"staging/{HEX[:31]}/",
     f"staging/{HEX.upper()}/", f"staging/{HEX}", f"staging/{HEX}/x", f"originals/{HEX}/",
     f"/staging/{HEX}/", f"staging/{HEX}//"],
)  # fmt: skip
def test_an_unsafe_prefix_is_refused_before_any_store_call(prefix: str) -> None:
    store, spy = _store([f"staging/{HEX}/{0:020d}", f"originals/{HEX}"])
    with pytest.raises(UnsafeObjectKey):
        store.delete_prefix(prefix)
    assert spy.calls == []


def test_one_uploads_staging_folder_is_listed_and_deleted() -> None:
    other = "f" * 32
    store, spy = _store(
        [f"staging/{HEX}/{0:020d}", f"staging/{HEX}/{1024:020d}", f"staging/{other}/{0:020d}"]
    )
    assert store.delete_prefix(f"staging/{HEX}/") == 2
    deleted = [c[1]["Key"] for c in spy.calls if c[0] == "delete"]
    assert deleted == [f"staging/{HEX}/{0:020d}", f"staging/{HEX}/{1024:020d}"]


def test_a_listed_key_outside_the_prefix_stops_the_delete() -> None:
    store, _ = _store([])

    class Lying(Spy):
        def get_paginator(self, name: str) -> Any:
            class Pages:
                def paginate(self, **kwargs: Any) -> Any:
                    return [{"Contents": [{"Key": "originals/" + HEX}]}]

            return Pages()

    store._client = Lying([])
    with pytest.raises(UnsafeObjectKey):
        store.delete_prefix(f"staging/{HEX}/")


def test_an_empty_folder_is_a_success() -> None:
    store, _ = _store([])
    assert store.delete_prefix(f"staging/{HEX}/") == 0
