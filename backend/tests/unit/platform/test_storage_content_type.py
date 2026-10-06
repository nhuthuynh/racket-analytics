"""QA-RV1-05: the store adapter can set the stored and the served content type (QA-S2-UI-03); the
caller (Capture & Media) says ``video/mp4`` for originals. No network: botocore signs locally,
and the multipart call is checked on a stubbed client."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from racket.platform.storage import ObjectStore, S3Config

pytestmark = [pytest.mark.unit]

CONFIG = S3Config("media", "http://127.0.0.1:9", "key", "secret", "us-east-1")


def test_the_presigned_get_asks_for_a_video_response_type() -> None:
    store = ObjectStore(CONFIG)
    url = store.presigned_get(
        "originals/x", 60, public_endpoint="https://localhost:3000", content_type="video/mp4"
    )
    assert parse_qs(urlsplit(url).query)["response-content-type"] == ["video/mp4"]
    plain = parse_qs(urlsplit(store.presigned_get("originals/x", 60)).query)
    assert "response-content-type" not in plain  # the probe's link is unchanged


def test_a_multipart_original_is_created_with_a_video_content_type() -> None:
    store = ObjectStore(CONFIG)
    calls: list[dict[str, Any]] = []

    class Client:
        def create_multipart_upload(self, **kwargs: Any) -> dict[str, str]:
            calls.append(kwargs)
            return {"UploadId": "u1"}

    store._client = Client()
    assert store.create_multipart("originals/x", content_type="video/mp4") == "u1"
    assert calls == [{"Bucket": "media", "Key": "originals/x", "ContentType": "video/mp4"}]
