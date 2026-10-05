"""Self-test of the ``written_keys`` fixture (QA-R3-02; testing-strategy rule 8: a checker
needs a positive control). A neighbour's write (another process, simulated with a second raw
S3 client) must not show up; this test's own writes, through ``ObjectStore``, must."""

from __future__ import annotations

import uuid

import pytest

from tests.support import contract
from tests.support.written_keys import WrittenKeys

pytestmark = pytest.mark.slow


def test_own_writes_are_seen_and_a_neighbours_are_not(written_keys: WrittenKeys) -> None:
    store = contract.OBJECT_STORE.load().from_settings()
    mine, neighbours = f"test-own/{uuid.uuid4().hex}", f"test-neighbour/{uuid.uuid4().hex}"
    store._client.put_object(Bucket=store.bucket, Key=neighbours, Body=b"x")  # not recorded
    try:
        store.put_bytes(mine, b"y")
        assert written_keys.stored() == {mine}
        store.delete(mine)
        assert written_keys.stored() == set()  # deleted objects drop out
        assert written_keys.written == [mine]
    finally:
        store.delete(neighbours)
        store.delete(mine)


def test_a_multipart_upload_is_recorded(written_keys: WrittenKeys) -> None:
    store = contract.OBJECT_STORE.load().from_settings()
    key = f"test-own/{uuid.uuid4().hex}"
    upload_id = store.create_multipart(key)
    etag = store.upload_part(key, upload_id, 1, b"z" * 10)
    store.complete_multipart(key, upload_id, [(1, etag)])
    try:
        assert written_keys.stored() == {key}
    finally:
        store.delete(key)
