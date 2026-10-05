"""Sprint 1 review round 1, PE-R1-01: an oversized ``Upload-Length`` must never reset a match
that already has its video or an upload in progress (api-sprint-01 §6.3 check order).

Real Postgres, object store and the in-process worker.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.support import contract, media, tus_ext
from tests.support.api import ApiDriver
from tests.support.flows import create_match

pytestmark = [pytest.mark.slow]

TWELVE_GB = 12 * 1000**3


def _match(api: ApiDriver, match_id: str) -> dict[str, Any]:
    response = api.request("ivy", "GET", contract.MATCH.format(match_id=match_id))
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


def test_pe_r1_01_oversized_creation_on_a_received_video_leaves_the_match_unchanged(
    api: ApiDriver,
) -> None:
    ivy = api.as_user("ivy")
    data = media.valid_clip_bytes()
    match_id = api.run(create_match(ivy, "PE-R1-01 received"))
    upload = api.run(tus_ext.start(ivy, match_id, data, filename="match.mp4"))
    assert api.run(tus_ext.patch(ivy, upload, 0, data)).status_code == 204
    contract.WORKER_RUN_UNTIL_IDLE.load()()
    before = _match(api, match_id)
    assert before["status"] == "video_received"

    response = api.run(tus_ext.create(ivy, match_id, b"\x00" * 16, length=TWELVE_GB))

    assert response.status_code == 409
    after = _match(api, match_id)
    assert after["status"] == "video_received"
    assert after["media"] == before["media"]
    assert after["rejection"] is None


def test_pe_r1_01_oversized_creation_during_an_upload_leaves_the_upload_in_place(
    api: ApiDriver,
) -> None:
    ivy = api.as_user("ivy")
    data = media.valid_clip_bytes()
    match_id = api.run(create_match(ivy, "PE-R1-01 receiving"))
    api.run(tus_ext.start(ivy, match_id, data, filename="match.mp4"))
    before = _match(api, match_id)
    assert before["upload"] is not None

    response = api.run(tus_ext.create(ivy, match_id, b"\x00" * 16, length=TWELVE_GB))

    assert response.status_code == 409
    after = _match(api, match_id)
    assert after["status"] == before["status"]
    assert after["upload"] == before["upload"]
    assert after["rejection"] is None
