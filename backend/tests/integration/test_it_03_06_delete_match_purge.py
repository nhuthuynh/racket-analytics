"""IT-03-06 (ST-050; FR-006, NFR-066 a/b, ADR 0006): API <-> DB <-> object store, delete a match.

Negative cases first: Carlos's DELETE of Ivy's match is a 404 and changes nothing; a DELETE
without the typed confirmation (DES FR-UX-90) is a 4xx and deletes nothing. Then Ivy deletes:
every read of the match answers 404 at once (match, stats, evidence, score sheet, video, rally
media) and the list no longer shows it; a second DELETE does not fail (idempotent). After one
purge pass no row in any table of the schema holds the match id (information-schema inventory,
so a new table is caught; risk row in sprint-03 §10) and no object the database knew for the
match is left in the store.

Written red first (QA-ACC-3): ``red_until`` ST-050.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

pytestmark = [pytest.mark.red_until(story="ST-050")]


def _reads(match_id: str, rally_id: str) -> list[tuple[str, str]]:
    return [
        st.statscontract.path("match", match_id=match_id),
        st.statscontract.path("stats", match_id=match_id),
        st.statscontract.path("evidence", match_id=match_id, metric_id="AN-01", side="A"),
        sb.path("sheet", match_id=match_id),
        sb.path("video", match_id=match_id),
        sb.path("media", match_id=match_id, rally_id=rally_id),
        sb.path("history", match_id=match_id),
    ]


def _listed(api: ApiDriver, user: str, match_id: str) -> bool:
    response = st.request(api, user, "matches")
    assert response.status_code == 200, response.text
    body = response.json()
    items = body["items"] if isinstance(body, dict) else body
    return any(item["id"] == match_id for item in items)


def test_it_03_06_someone_elses_match_is_a_404_and_nothing_changes(
    api: ApiDriver, committed_db: Any
) -> None:
    match_id = st.tagged_example(api, "ivy", "IT-03-06 bola")
    before = st.rows_holding(committed_db, [match_id])
    response = st.delete_match(api, "carlos", match_id)
    assert response.status_code == 404, response.text
    assert st.rows_holding(committed_db, [match_id]) == before
    assert _listed(api, "ivy", match_id)


@pytest.mark.parametrize("body", [{}, {"confirm": "yes"}, {"confirm": "keep"}, None])
def test_it_03_06_no_typed_confirmation_deletes_nothing(
    api: ApiDriver, committed_db: Any, body: Any
) -> None:
    match_id = st.tagged_example(api, "ivy", "IT-03-06 confirm")
    before = st.rows_holding(committed_db, [match_id])
    method, url = st.statscontract.path("delete_match", match_id=match_id)
    kwargs = {} if body is None else {"json": body}
    response = api.request("ivy", method, url, **kwargs)
    assert 400 <= response.status_code < 500, response.text
    assert st.rows_holding(committed_db, [match_id]) == before
    assert _listed(api, "ivy", match_id)


def test_it_03_06_delete_hides_at_once_and_the_purge_leaves_nothing(
    api: ApiDriver, committed_db: Any
) -> None:
    match_id = st.tagged_example(api, "ivy", "IT-03-06 purge")
    rally_id = sb.sheet_body(api, "ivy", match_id)["rows"][0]["rally_id"]
    keys = st.object_keys_of(committed_db, match_id)
    assert keys, "positive control: the match has stored objects before deletion"
    assert st.keys_still_stored(keys) == keys

    response = st.delete_match(api, "ivy", match_id)
    assert response.status_code in st.statscontract.DELETE_OK, response.text
    for method, url in _reads(match_id, rally_id):
        got = api.request("ivy", method, url)
        assert got.status_code == 404, f"{method} {url}: {got.status_code}"
    assert not _listed(api, "ivy", match_id)
    again = st.delete_match(api, "ivy", match_id)
    assert again.status_code in (*st.statscontract.DELETE_OK, 404), again.text

    st.run_purge_once()
    left = {k: n for k, n in st.rows_holding(committed_db, [match_id]).items() if n}
    assert left == {}, f"rows still hold the match after the purge: {left}"
    assert st.keys_still_stored(keys) == []


def test_it_03_06_the_purge_leaves_other_matches_alone(api: ApiDriver, committed_db: Any) -> None:
    gone = st.tagged_example(api, "ivy", "IT-03-06 gone")
    kept = st.tagged_example(api, "ivy", "IT-03-06 kept")
    kept_rows = st.rows_holding(committed_db, [kept])
    kept_keys = st.object_keys_of(committed_db, kept)
    assert st.delete_match(api, "ivy", gone).status_code in st.statscontract.DELETE_OK
    st.run_purge_once()
    assert st.rows_holding(committed_db, [kept]) == kept_rows
    assert st.keys_still_stored(kept_keys) == kept_keys
    assert sb.sheet_body(api, "ivy", kept)["rows"]
