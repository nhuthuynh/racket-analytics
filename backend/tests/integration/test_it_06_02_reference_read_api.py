"""IT-06-02 (ST-170b; FR-170.R4, NFR-050.10; SEC-6 T6-PL-3, T6-PL-4, T6-PL-6, §8 row 2).

The reference read API over the real app, Postgres session and the committed reference tree
``backend/tests/fixtures/references-api`` (three readable entries, one ``draft``):

* ``GET /reference-sets/current`` lists only ``coach-reviewed`` and ``verified`` entries, each with
  its source_type, citation, version and provenance label (FR-170.R4, R5).
* ``GET /reference-sets/{version}/entries/{entry_id}``: a draft id answers 404 with the same body
  as an unknown id, for every signed-in user (T6-PL-3; the §8 BOLA row for content with no
  owner); a ``coach-reviewed`` id of the same version answers 200 (positive control).
* Signed-in only (401); ``Cache-Control: no-store`` on 200 and 404 (T6-PL-6); no write route:
  every write method answers 405 (T6-PL-4).
* A tree that fails the lint serves nothing (fail closed); no set serves 404.

Red first: before ST-170b neither route exists, so the reviewed entry's positive control fails.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from tests.regression.bola import all_routes
from tests.support.api import async_client, lifespan, sign_in
from tests.support.no_store import cache_control
from tests.support.reference_api import (
    CURRENT,
    DRAFT_ID,
    ENTRY,
    FIXTURE_ROOT,
    LABELS,
    READABLE_IDS,
    REVIEWED_ID,
    WRITE_METHODS,
    entry_url,
    point_at,
    without_support_ref,
)
from tests.support.references import entry, reference_doc, write_lock, write_version

ENTRY_FIELDS = {
    "id", "pattern_id", "definition_version", "better_direction", "interval_method",
    "level_band", "format", "source_type", "provenance_label", "citation_id", "status",
    "version", "value", "band", "n", "k", "interval",
}  # fmt: skip


@pytest.fixture
async def users(app: Any) -> AsyncIterator[dict[str, httpx.AsyncClient]]:
    async with lifespan(app), async_client(app) as ivy, async_client(app) as carlos:
        await sign_in(ivy, "ivy")
        await sign_in(carlos, "carlos")
        yield {"ivy": ivy, "carlos": carlos}


async def test_it_06_02_a_draft_by_id_is_the_404_of_an_unknown_id(
    users: dict[str, httpx.AsyncClient],
) -> None:
    for client in users.values():
        reviewed = await client.get(entry_url(REVIEWED_ID))
        assert reviewed.status_code == 200, reviewed.text  # positive control
        draft = await client.get(entry_url(DRAFT_ID))
        unknown = await client.get(entry_url("REF-AN99-D-INT"))
        assert draft.status_code == unknown.status_code == 404
        assert without_support_ref(draft.json()) == without_support_ref(unknown.json())
        assert DRAFT_ID not in draft.text


async def test_it_06_02_current_lists_only_reviewed_and_verified_entries(
    users: dict[str, httpx.AsyncClient],
) -> None:
    response = await users["ivy"].get(CURRENT)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["set"], body["version"]) == ("pb-reference", 1)
    assert [e["id"] for e in body["entries"]] == list(READABLE_IDS)
    assert {e["status"] for e in body["entries"]} == {"coach-reviewed", "verified"}
    assert DRAFT_ID not in response.text
    for item in body["entries"]:
        assert set(item) == ENTRY_FIELDS
        assert item["source_type"] == "judgment"
        assert item["provenance_label"] == LABELS["judgment"]
        assert item["citation_id"] in ("SRC-0001", "SRC-0002")
        assert item["version"] == 1
        assert item["interval"] == item["band"]
        assert item["n"] is None


async def test_it_06_02_an_entry_by_id_is_the_entry_of_the_list(
    users: dict[str, httpx.AsyncClient],
) -> None:
    listed = (await users["ivy"].get(CURRENT)).json()["entries"]
    one = await users["carlos"].get(entry_url("REF-AN13-D-INT"))
    assert one.status_code == 200, one.text
    same = next(e for e in listed if e["id"] == one.json()["id"])
    assert one.json() == {"set": "pb-reference", **same}


@pytest.mark.parametrize("version", ["2", "0", "one", "1.0", "-1"])
async def test_it_06_02_an_unknown_or_malformed_version_is_the_same_404(
    users: dict[str, httpx.AsyncClient], version: str
) -> None:
    client = users["ivy"]
    response = await client.get(entry_url(REVIEWED_ID, version))
    unknown = await client.get(entry_url("REF-AN99-D-INT"))
    assert response.status_code == 404
    assert without_support_ref(response.json()) == without_support_ref(unknown.json())


async def test_it_06_02_anonymous_callers_are_refused(app: Any) -> None:
    async with lifespan(app), async_client(app) as anonymous:
        for url in (CURRENT, entry_url(REVIEWED_ID), entry_url(DRAFT_ID)):
            response = await anonymous.get(url)
            assert response.status_code == 401, url
            assert cache_control(response.headers) == ["no-store"], url


async def test_it_06_02_answers_are_never_cached(users: dict[str, httpx.AsyncClient]) -> None:
    client = users["ivy"]
    for url in (CURRENT, entry_url(REVIEWED_ID), entry_url(DRAFT_ID)):
        response = await client.get(url)
        assert cache_control(response.headers) == ["no-store"], url


async def test_it_06_02_there_is_no_write_route(
    app: Any, users: dict[str, httpx.AsyncClient]
) -> None:
    reference_routes = {(m, p) for m, p in all_routes(app) if p.startswith("/reference-sets")}
    assert reference_routes == {("GET", CURRENT), ("GET", ENTRY)}
    for method in WRITE_METHODS:
        for url in (CURRENT, entry_url(REVIEWED_ID)):
            response = await users["ivy"].request(method, url, json={"status": "verified"})
            assert response.status_code == 405, (method, url)
    assert (await users["ivy"].get(entry_url(REVIEWED_ID))).json()["status"] == "coach-reviewed"


async def test_it_06_02_current_is_the_newest_version_and_old_entries_stay_readable(
    users: dict[str, httpx.AsyncClient], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "references"
    write_version(root, reference_doc([entry()], version=1))
    write_version(root, reference_doc([entry(band=[0.5, 0.7])], version=2))
    point_at(monkeypatch, root)
    client = users["ivy"]
    current = (await client.get(CURRENT)).json()
    assert (current["version"], current["entries"][0]["band"]) == (2, [0.5, 0.7])
    old = await client.get(entry_url("REF-AN09-D-INT", 1))
    assert old.status_code == 200, old.text
    assert (old.json()["version"], old.json()["band"]) == (1, [0.45, 0.7])


async def test_it_06_02_a_tree_that_fails_the_lint_serves_nothing(
    users: dict[str, httpx.AsyncClient], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "references"
    write_version(root, reference_doc([entry(source={"citation_id": "SRC-9999"})]))
    point_at(monkeypatch, root)
    client = users["ivy"]
    assert (await client.get(CURRENT)).status_code == 404
    assert (await client.get(entry_url("REF-AN09-D-INT"))).status_code == 404


async def test_it_06_02_no_reference_set_is_404(
    users: dict[str, httpx.AsyncClient], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "references"
    write_lock(root, {})
    point_at(monkeypatch, root)
    response = await users["ivy"].get(CURRENT)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_it_06_02_the_suite_serves_the_committed_fixture_tree() -> None:
    """Positive control for the tests above: they read the fixture tree, not a guess."""
    assert (FIXTURE_ROOT / "pb-reference" / "v1.json").is_file()
    assert (FIXTURE_ROOT / "references.lock").is_file()
