"""IT-02-06 (ST-037; FR-027, NFR-055, NFR-069): the rally video link is a short-lived presigned
URL of the match video. Range requests return 206; a changed signature is refused; after its
TTL the link is refused; the session token is never in the URL; the start is the rally's.

API <-> object store, both real (dev-objectstore). The TTL is set to 2 s for this test.
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import pytest

from tests.support import contract
from tests.support import scorebook as sb
from tests.support.api import ApiDriver

TTL_S = 2


@pytest.fixture
def short_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEDIA_URL_TTL_SECONDS", str(TTL_S))


def _link(api: ApiDriver, match_id: str, rally_number: int) -> tuple[httpx.Response, str]:
    ivy = api.as_user("ivy")
    row = api.run(sb.sheet(ivy, match_id)).json()["rows"][rally_number - 1]
    method, url = sb.path("media", match_id=match_id, rally_id=row["rally_id"])
    return api.run(ivy.request(method, url)), str(row["start_ms"])


def _tampered(url: str) -> str:
    head, _, signature = url.rpartition("X-Amz-Signature=")
    sig, sep, rest = signature.partition("&")
    flipped = "0" if sig[-1] != "0" else "1"
    return f"{head}X-Amz-Signature={sig[:-1]}{flipped}{sep}{rest}"


def test_it_02_06_link_plays_from_the_rally_and_expires(short_ttl: None, api: ApiDriver) -> None:
    match_id = sb.ready_tagged_match(api, "ivy", title="IT-02-06")
    response, start_ms = _link(api, match_id, 3)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body[sb.tagcontract.MEDIA_START] == int(start_ms)
    assert 0 < body[sb.tagcontract.MEDIA_TTL] <= 900
    session = api.as_user("ivy").cookies.get(contract.SESSION_COOKIE_TEST) or ""
    assert sb.taglib.media_url_problems(body["url"], body[sb.tagcontract.MEDIA_TTL], session) == []

    url = body["url"]
    with httpx.Client(timeout=10) as store:
        ranged = store.get(url, headers={"Range": "bytes=0-1023"})
        assert ranged.status_code == 206, ranged.text[:200]
        assert len(ranged.content) == 1024
        assert ranged.content[4:8] == b"ftyp"  # the start of the uploaded MP4

        assert store.get(_tampered(url), headers={"Range": "bytes=0-15"}).status_code == 403

        time.sleep(TTL_S + 1.5)
        assert store.get(url, headers={"Range": "bytes=0-15"}).status_code == 403

    # Reopening the rally from the score sheet still works: a fresh link (FR-027).
    again, _ = _link(api, match_id, 3)
    assert again.status_code == 200
    with httpx.Client(timeout=10) as store:
        fresh = store.get(again.json()["url"], headers={"Range": "bytes=0-15"})
    assert fresh.status_code == 206


def test_it_02_06_a_ttl_above_15_minutes_is_refused_at_startup() -> None:
    settings = contract.SETTINGS.load()
    env = {"APP_ENV": "test", "DATABASE_URL": "postgresql://u:p@h/d", "S3_BUCKET_MEDIA": "b"}
    assert settings.from_env({**env, "MEDIA_URL_TTL_SECONDS": "900"}).media_url_ttl_seconds == 900
    with pytest.raises(contract.CONFIGURATION_ERROR.load()):
        settings.from_env({**env, "MEDIA_URL_TTL_SECONDS": "901"})


def test_it_02_06_no_media_link_before_the_video_is_received(api: ApiDriver) -> None:
    ivy = api.as_user("ivy")
    match_id = api.run(sb.create_doubles(ivy, "IT-02-06 no video"))
    method, url = sb.path(
        "media", match_id=match_id, rally_id="00000000-0000-4000-8000-000000000000"
    )
    response: Any = api.run(ivy.request(method, url))
    assert response.status_code in (404, 409), response.text
