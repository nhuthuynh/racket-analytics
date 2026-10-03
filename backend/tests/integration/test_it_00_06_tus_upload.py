"""IT-00-06 (API <-> object store, ST-008): tus creation, HEAD, PATCH in 3 chunks; the final
object's sha256 equals the source (AQS/STACK-06)."""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from tests.support import contract, tus
from tests.support.api import ApiDriver
from tests.support.flows import create_match
from tests.support.paths import SYNTHETIC_CLIP

pytestmark = [pytest.mark.red_until(story="ST-008"), pytest.mark.slow]


def test_three_chunk_upload_stores_identical_bytes(api: ApiDriver) -> None:
    data = SYNTHETIC_CLIP.read_bytes()
    ivy = api.as_user("ivy")
    store = contract.OBJECT_STORE.load().from_settings()
    before = set(store.list_keys())
    match_id = api.run(create_match(ivy, "IT-00-06"))

    upload = api.run(tus.start(ivy, match_id, len(data)))
    assert api.run(tus.offset(ivy, upload)) == 0
    api.run(tus.send_all(ivy, upload, data, chunks=3))
    assert api.run(tus.offset(ivy, upload)) == len(data)

    new_keys = set(store.list_keys()) - before
    assert len(new_keys) == 1, new_keys
    stored: Any = store.get_bytes(new_keys.pop())
    assert hashlib.sha256(stored).hexdigest() == hashlib.sha256(data).hexdigest()
