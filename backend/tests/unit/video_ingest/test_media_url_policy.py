"""``MediaUrlPolicy`` (ST-037; FR-027; NFR-055 TTL ≤ 15 min, no session token in any URL).

sprint-02 §5 TDD order: 1. a TTL above 15 minutes is refused; 2. a URL never carries the
session token. Then the configuration: ``MEDIA_URL_TTL_SECONDS`` defaults to 5 minutes and a
value above 900 refuses to start (fail closed, ADR 0014).
"""

from __future__ import annotations

import pytest

from racket.platform.settings import ConfigurationError, Settings
from racket.video_ingest.domain import MediaUrlPolicy, UnsafeMediaUrl

pytestmark = pytest.mark.unit

BASE = {"APP_ENV": "test", "DATABASE_URL": "postgresql://u:p@h/d", "S3_BUCKET_MEDIA": "b"}
TOKEN = "s3cr3t-session-token-value-abcdefghijklmnop"


@pytest.mark.parametrize("ttl", [901, 3600, 0, -1, True])
def test_a_ttl_outside_1_to_900_seconds_is_refused(ttl: int) -> None:
    with pytest.raises(ValueError, match="TTL"):
        MediaUrlPolicy(ttl_seconds=ttl)


@pytest.mark.parametrize("ttl", [1, 300, 900])
def test_a_ttl_up_to_15_minutes_is_kept(ttl: int) -> None:
    assert MediaUrlPolicy(ttl_seconds=ttl).ttl_seconds == ttl


@pytest.mark.parametrize(
    "url",
    [
        f"https://localhost:3000/racket-media/originals/x.mp4?token={TOKEN}",
        f"https://localhost:3000/{TOKEN}/x.mp4",
        "https://localhost:3000/x.mp4?racket_session=abc",
        "https://localhost:3000/x.mp4?__Host-racket_session=abc",
    ],
)
def test_a_url_with_the_session_token_or_cookie_name_is_refused(url: str) -> None:
    with pytest.raises(UnsafeMediaUrl):
        MediaUrlPolicy(ttl_seconds=300).check(url, session_token=TOKEN)


@pytest.mark.parametrize("url", ["javascript:alert(1)", "ftp://h/x", "//evil.example/x", ""])
def test_only_http_or_https_urls_are_handed_out(url: str) -> None:
    with pytest.raises(UnsafeMediaUrl):
        MediaUrlPolicy(ttl_seconds=300).check(url, session_token=TOKEN)


def test_a_presigned_url_without_the_token_passes() -> None:
    url = "https://localhost:3000/racket-media/originals/ab.mp4?X-Amz-Signature=00ff"
    assert MediaUrlPolicy(ttl_seconds=300).check(url, session_token=TOKEN) == url


def test_the_media_ttl_defaults_to_five_minutes() -> None:
    assert Settings.from_env(BASE).media_url_ttl_seconds == 300


def test_a_configured_media_ttl_above_15_minutes_refuses_to_start() -> None:
    with pytest.raises(ConfigurationError, match="MEDIA_URL_TTL_SECONDS"):
        Settings.from_env(BASE | {"MEDIA_URL_TTL_SECONDS": "901"})


def test_the_public_media_endpoint_is_optional_and_read_from_the_environment() -> None:
    assert Settings.from_env(BASE).s3_public_endpoint_url is None
    got = Settings.from_env(BASE | {"S3_PUBLIC_ENDPOINT_URL": "https://localhost:3000/"})
    assert got.s3_public_endpoint_url == "https://localhost:3000"
