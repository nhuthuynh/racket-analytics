"""IT-02-15 (QA-RV1-05, QA-S2-UI-03): the match video is served as a video, not as
``application/octet-stream``. A browser that cannot decode the stream then reports a decode
error, not a format error, so V-01 says "this browser cannot play this video" instead of a
retry that fails again.

API <-> object store, both real (dev-objectstore): the original is stored with
``Content-Type: video/mp4`` and the presigned GET asks for it as the response type, so a link
signed before the fix (or an object stored before it) still plays as a video.
"""

from __future__ import annotations

from typing import Any

import httpx

from tests.support import scorebook as sb
from tests.support.api import ApiDriver


def test_it_02_15_the_match_video_is_served_as_video_mp4(api: ApiDriver) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(ivy, "IT-02-15"))
    api.run(sb.receive_video(ivy, match_id))
    method, url = sb.path("video", match_id=match_id)
    response: Any = api.run(ivy.request(method, url))
    assert response.status_code == 200, response.text
    with httpx.Client(timeout=10) as store:
        ranged = store.get(response.json()["url"], headers={"Range": "bytes=0-1023"})
    assert ranged.status_code == 206, ranged.text[:200]
    assert ranged.headers["content-type"] == "video/mp4"
    assert ranged.content[4:8] == b"ftyp"


def test_it_02_15_the_original_is_stored_with_a_video_content_type(
    api: ApiDriver, written_keys: Any
) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(ivy, "IT-02-15 stored"))
    api.run(sb.receive_video(ivy, match_id))
    keys = sorted(written_keys.stored())
    assert len(keys) == 1, keys
    store = api.app.state.object_store()
    head = store._client.head_object(Bucket=store.bucket, Key=keys[0])
    assert head["ContentType"] == "video/mp4"
