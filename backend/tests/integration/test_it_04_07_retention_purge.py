"""IT-04-07 retention purge (ST-069; FR-008; NFR-066; ADR 0006, ADR 0042; api-sprint-04 §5;
SEC-4 T4-RT-1..T4-RT-4): API <-> DB <-> object store <-> purge entry point.

Negative cases first: with ``FEATURE_RETENTION_SETTING`` off the routes are 404, the match
carries no added field and a purge 400 days later deletes nothing; "until I delete" and the
default 90 days keep a 31-day-old video; another account's setting never shortens Ivy's; a store
failure keeps the media row (objects first). Then the period passes: the review video object is
404 at the store, its media row is gone, and stats, score sheet and plan answer 200."""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest

from tests.support import retention as rt
from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

PLAN_BODY = {"minutes_per_session": 60, "sessions_per_week": 2, "players_available": 4,
             "equipment": ["full_court"], "level": "intermediate"}  # fmt: skip


@pytest.fixture
def on(monkeypatch: pytest.MonkeyPatch, committed_db: Any) -> Iterator[ApiDriver]:
    driver = rt.build_api(monkeypatch, on=True)
    yield driver
    driver.close()


@pytest.fixture
def off(monkeypatch: pytest.MonkeyPatch, committed_db: Any) -> Iterator[ApiDriver]:
    driver = rt.build_api(monkeypatch, on=False)
    yield driver
    driver.close()


def _error(response: Any) -> tuple[int, str, list[tuple[Any, Any]]]:
    body = response.json()["error"]
    fields = [(f.get("field"), f.get("code")) for f in body.get("fields") or []]
    return response.status_code, body["code"], fields


# ------------------------------------------------------------------ flag off (negative first)
def test_it_04_07_flag_off_routes_404_no_field_and_the_purge_deletes_nothing(
    off: ApiDriver, committed_db: Any
) -> None:
    match_id = rt.analysed_match(off, "ivy", "IT-04-07 off")
    assert off.request("ivy", "GET", rt.RETENTION).status_code == 404
    assert rt.put_days(off, "ivy", 30).status_code == 404
    assert rt.FIELD not in rt.match_body(off, "ivy", match_id)
    listed = off.request("ivy", "GET", "/matches").json()["items"]
    assert listed
    assert all(rt.FIELD not in item for item in listed)
    assert rt.run_purge("--now-offset-days", "400") == 0
    assert rt.stored(committed_db, match_id)
    assert rt.media_rows(committed_db, match_id) == 1


def test_it_04_07_the_setting_needs_a_session_and_a_closed_body(on: ApiDriver) -> None:
    assert on.request("anonymous", "GET", rt.RETENTION).status_code == 401
    assert on.request("anonymous", "PUT", rt.RETENTION, json={"review_video_days": 30}
                      ).status_code == 401  # fmt: skip
    bad = [
        ({}, ("review_video_days", "required")),
        ({"review_video_days": 60}, ("review_video_days", "unknown_value")),
        ({"review_video_days": "30"}, ("review_video_days", "unknown_value")),
        ({"review_video_days": True}, ("review_video_days", "unknown_value")),
        ({"review_video_days": 30.0}, ("review_video_days", "unknown_value")),
        ({"review_video_days": 30, "account_id": "x"}, (None, "unknown_field")),
        ([30], (None, "invalid")),
    ]
    for body, field in bad:
        response = on.request("ivy", "PUT", rt.RETENTION, json=body)
        assert _error(response) == (422, "validation_failed", [field]), (body, response.text)
    got = on.request("ivy", "GET", rt.RETENTION)
    assert got.status_code == 200
    assert got.json() == {"review_video_days": 90, "choices": [30, 90, 365, None]}
    assert got.headers["Cache-Control"] == "no-store"


def test_it_04_07_until_i_delete_and_the_default_keep_a_31_day_old_video(
    on: ApiDriver, committed_db: Any
) -> None:
    forever = rt.analysed_match(on, "ivy", "IT-04-07 forever")
    default = rt.analysed_match(on, "carlos", "IT-04-07 default")
    put = rt.put_days(on, "ivy", None)
    assert put.status_code == 200, put.text
    assert put.json()["review_video_days"] is None
    assert rt.match_body(on, "ivy", forever)[rt.FIELD] is None
    assert rt.run_purge("--now-offset-days", "400") == 0
    assert rt.stored(committed_db, forever)
    assert rt.run_purge("--now-offset-days", "31") == 0
    assert rt.stored(committed_db, default)
    assert rt.run_purge("--now-offset-days", "91") == 0
    assert not rt.stored(committed_db, default)
    assert rt.stored(committed_db, forever)


def test_it_04_07_another_accounts_setting_never_shortens_mine(
    on: ApiDriver, committed_db: Any
) -> None:
    """T4-RT-1: Ivy 30 days, Carlos 365; a pass 31 days later deletes only Ivy's video."""
    ivy = rt.analysed_match(on, "ivy", "IT-04-07 ivy")
    carlos = rt.analysed_match(on, "carlos", "IT-04-07 carlos")
    assert rt.put_days(on, "ivy", 30).status_code == 200
    assert rt.put_days(on, "carlos", 365).status_code == 200
    assert rt.run_purge("--now-offset-days", "31") == 0
    assert not rt.stored(committed_db, ivy)
    assert rt.media_rows(committed_db, ivy) == 0
    assert rt.stored(committed_db, carlos)
    assert rt.media_rows(committed_db, carlos) == 1


def test_it_04_07_a_store_failure_keeps_the_media_row_and_the_next_pass_finishes(
    on: ApiDriver, committed_db: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T4-RT-2 (ADR 0042): objects first, then the media row."""
    match_id = rt.analysed_match(on, "ivy", "IT-04-07 store failure")
    assert rt.put_days(on, "ivy", 30).status_code == 200
    store_cls = st.OBJECT_STORE.load()
    real_delete = store_cls.delete

    def failing_delete(self: Any, key: str) -> None:
        raise ConnectionError("injected store failure (IT-04-07)")

    monkeypatch.setattr(store_cls, "delete", failing_delete)
    rc = None
    with contextlib.suppress(Exception):  # the failure may surface as an exception or rc 1
        rc = rt.run_purge("--now-offset-days", "31")
    assert rc in (None, 1)
    assert rt.stored(committed_db, match_id)
    assert rt.media_rows(committed_db, match_id) == 1
    monkeypatch.setattr(store_cls, "delete", real_delete)
    assert rt.run_purge("--now-offset-days", "31") == 0
    assert not rt.stored(committed_db, match_id)
    assert rt.media_rows(committed_db, match_id) == 0


# ------------------------------------------------------------------ the period passes
def test_it_04_07_retention_passes_object_404_stats_sheet_and_plan_200(
    on: ApiDriver, committed_db: Any
) -> None:
    match_id = rt.analysed_match(on, "ivy", "IT-04-07 passes")
    rows_before = sb.sheet_body(on, "ivy", match_id)["rows"]
    assert on.request("ivy", "POST", "/me/plan", json=PLAN_BODY).status_code == 201
    assert rt.put_days(on, "ivy", 30).status_code == 200
    shown = rt.match_body(on, "ivy", match_id)[rt.FIELD]
    expected = rt.analysed_at(committed_db, match_id) + timedelta(days=30)
    assert abs(rt.parse_utc(shown) - expected) < timedelta(seconds=1), shown
    link = rt.video_link(on, "ivy", match_id)
    assert link.status_code == 200, link.text
    url = link.json()["url"]
    assert rt.fetch_status(url) == 206

    assert rt.run_purge("--now-offset-days", "29") == 0  # not yet due
    assert rt.stored(committed_db, match_id)
    assert rt.run_purge("--now-offset-days", "31") == 0

    assert rt.fetch_status(url) == 404
    assert not rt.stored(committed_db, match_id)
    assert rt.media_rows(committed_db, match_id) == 0
    assert rt.video_link(on, "ivy", match_id).status_code == 409
    assert st.stats(on, "ivy", match_id).status_code == 200
    assert sb.sheet_body(on, "ivy", match_id)["rows"] == rows_before
    assert on.request("ivy", "GET", "/me/plan").status_code == 200
    assert rt.match_body(on, "ivy", match_id)[rt.FIELD] is None

    # T4-RT-4: a longer setting after the purge does not bring the video back.
    assert rt.put_days(on, "ivy", 365).status_code == 200
    assert not rt.stored(committed_db, match_id)
    assert rt.match_body(on, "ivy", match_id)[rt.FIELD] is None
