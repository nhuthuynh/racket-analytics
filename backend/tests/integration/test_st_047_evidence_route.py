"""ST-047 integration (FR-103, NFR-038, NFR-051; api-sprint-03 §3.1): ``GET
/matches/{match_id}/stats/{metric_id}/evidence`` over the real app, Postgres and store.

Negative cases first: an unpublished metric id (``draft`` in the dictionary) gets the same 404
``not_found`` as an unknown one, and a cursor that is not ours is 422 ``cursor``/``invalid``.
Then "see all n" by cursor: following ``next_cursor`` over a 23-rally stat lists every rally once,
at most 10 per page, in rally-time order, with ``total`` = 23 on every page, the last page has no
cursor, and each page is ``Cache-Control: no-store`` with the stats route's ``sheet_version``.
IT-03-04 covers the first page per metric and side; IT-03-05 the cross-account 404.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from tests.support import stats as st
from tests.support.api import ApiDriver


def _strip(response: Any) -> tuple[int, Any]:
    body = response.json() if response.content else None
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        body["error"].pop("support_ref", None)
    return response.status_code, body


@pytest.fixture
def an05_draft(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[None]:
    st.with_statuses(monkeypatch, tmp_path, draft=("AN-05",))
    yield
    st.clear_dictionary_cache()


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[None]:
    st.with_statuses(monkeypatch, tmp_path)
    yield
    st.clear_dictionary_cache()


def test_st_047_a_draft_metric_gets_the_same_404_as_an_unknown_one(
    api: ApiDriver, an05_draft: None
) -> None:
    match_id = st.tagged_example(api, "ivy", "ST-047 draft")
    draft = st.evidence(api, "ivy", match_id, "AN-05", "A")
    unknown = st.evidence(api, "ivy", match_id, "AN-99", "A")
    assert st.refusal(draft) == (404, "not_found", []), draft.text
    assert _strip(draft) == _strip(unknown)
    assert "items" not in draft.text
    control = st.evidence(api, "ivy", match_id, "AN-01", "A")
    assert control.status_code == 200, control.text


def test_st_047_a_cursor_that_is_not_ours_is_refused(api: ApiDriver, published: None) -> None:
    match_id = st.tagged_example(api, "ivy", "ST-047 cursor")
    _, url = st.statscontract.path("evidence", match_id=match_id, metric_id="AN-01", side="A")
    response = api.request("ivy", "GET", url + "&cursor=not-ours")
    assert st.refusal(response) == (422, "validation_failed", [("cursor", "invalid")]), (
        response.text
    )


def test_st_047_see_all_n_by_cursor_lists_every_rally_once_in_rally_time_order(
    api: ApiDriver, published: None
) -> None:
    games = st.no_score_script(46)
    match_id = st.tag_games(api, "ivy", games, "ST-047 see all")
    refs = st.statslib.starter_stats(games)["AN-02"]["A"]["rallies"]
    assert len(refs) == 23
    sheet_version = st.stats_body(api, "ivy", match_id)["sheet_version"]
    _, first = st.statscontract.path("evidence", match_id=match_id, metric_id="AN-02", side="A")

    items: list[dict[str, Any]] = []
    sizes: list[int] = []
    url: str | None = first
    while url is not None:
        response = api.request("ivy", "GET", url)
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        body = response.json()
        assert body[st.statscontract.EVIDENCE_TOTAL] == 23
        assert body["sheet_version"] == sheet_version
        page = body[st.statscontract.EVIDENCE_ITEMS]
        sizes.append(len(page))
        items += page
        url = None if body["next_cursor"] is None else f"{first}&cursor={body['next_cursor']}"
        assert len(sizes) <= 3, "the cursor does not end"

    assert sizes == [10, 10, 3]
    assert sorted(i["number"] for i in items) == sorted(refs)
    assert len({i[st.statscontract.EVIDENCE_RALLY_ID] for i in items}) == 23
    starts = [(i["start_ms"], i["number"]) for i in items]
    assert starts == sorted(starts), "pages are not in rally-time order"
