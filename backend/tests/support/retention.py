"""Helpers for the FR-008 review-video retention tests (ST-069; api-sprint-04 §5; SEC-4 T4-RT).

The app is built after ``FEATURE_RETENTION_SETTING`` is set (the flag is read at start-up) on
the committed database, because the purge runs as its own process entry point
(``racket.platform.purge:main``) with its own sessions. Rows are read with plain SQL: the tests
never import the product's tables.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
import sqlalchemy as sa

from tests.support import contract
from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

RETENTION = "/me/retention"
FIELD = "review_video_delete_at"


def build_api(monkeypatch: pytest.MonkeyPatch, *, on: bool) -> ApiDriver:
    monkeypatch.setenv("FEATURE_RETENTION_SETTING", "true" if on else "false")
    return ApiDriver(contract.APP_FACTORY.load()())


def analysed_match(api: ApiDriver, user: str, title: str) -> str:
    """A tagged match whose video is received and probed (the R1 analysis, api-sprint-04 §5)."""
    match_id = st.tagged_example(api, user, title)
    st.probe_videos()
    return match_id


def run_purge(*options: str) -> int:
    rc: int = st.PURGE_MAIN.load()(["--once", *options])
    return rc


def video_key(engine: Any, match_id: str) -> str:
    with engine.connect() as conn:
        key = conn.execute(
            sa.text("SELECT object_key FROM upload_sessions WHERE match_id::text = :m"),
            {"m": match_id},
        ).scalar_one()
    return str(key)


def media_rows(engine: Any, match_id: str) -> int:
    with engine.connect() as conn:
        return int(
            conn.execute(
                sa.text("SELECT count(*) FROM media_assets WHERE match_id::text = :m"),
                {"m": match_id},
            ).scalar_one()
        )


def analysed_at(engine: Any, match_id: str) -> datetime:
    """The probe's success time: when the media facts were written (api-sprint-04 §5)."""
    with engine.connect() as conn:
        at = conn.execute(
            sa.text("SELECT created_at FROM media_facts WHERE match_id::text = :m"),
            {"m": match_id},
        ).scalar_one()
    return at.astimezone(UTC)  # type: ignore[no-any-return]


def stored(engine: Any, match_id: str) -> bool:
    return st.keys_still_stored([video_key(engine, match_id)]) != []


def video_link(api: ApiDriver, user: str, match_id: str) -> httpx.Response:
    method, url = sb.path("video", match_id=match_id)
    return api.request(user, method, url)


def fetch_status(url: str) -> int:
    """GET the signed link straight at the store (no proxy), first two bytes."""
    with httpx.Client(trust_env=False, timeout=30) as client:
        return client.get(url, headers={"Range": "bytes=0-1"}).status_code


def put_days(api: ApiDriver, user: str, days: Any) -> httpx.Response:
    return api.request(user, "PUT", RETENTION, json={"review_video_days": days})


def match_body(api: ApiDriver, user: str, match_id: str) -> dict[str, Any]:
    response = api.request(user, "GET", f"/matches/{match_id}")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def parse_utc(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)
