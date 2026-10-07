"""IT-03-04 (ST-047; FR-103, FR-027, NFR-038, NFR-014): API <-> DB <-> object store, "Show me".

For every metric and side with n > 0 of the worked example: at most 10 items, ``total`` = n
("see all n"), every item is a rally behind the metric (the independent reference's list), no
rally twice, ordered by rally time. A limit above 10 is 422 ``limit``/``invalid``; an unknown
metric is 404 ``not_found`` and a bad side 422 ``side_invalid`` (api-sprint-03 §3.1), with the
route proven to exist first (QA-R1S3-05). The first item's rally video link (the Sprint 2 rally
media route) answers a Range request with 206 from the store.

Written red first (QA-ACC-3): ``red_until`` ST-047.

Marker ``red_until`` ST-047 removed (VR2-S3-01, TCR row 2026-10-07): the story is built and
every row passes, so the file is in the per-PR gate and the coverage selection.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import pytest

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

pytestmark = [pytest.mark.needs_verification]


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[None]:
    st.with_statuses(monkeypatch, tmp_path)
    yield
    st.clear_dictionary_cache()


@pytest.fixture
def example(api: ApiDriver, published: None) -> str:
    return st.tagged_example(api, "ivy", "IT-03-04")


def test_it_03_04_a_limit_above_ten_is_refused(api: ApiDriver, example: str) -> None:
    # api-sprint-03 §3.1: 422 limit/invalid; a missing route (404/405) is not it (QA-R1S3-05).
    response = st.evidence(api, "ivy", example, "AN-01", "A", limit=11)
    assert st.refusal(response) == (422, "validation_failed", [("limit", "invalid")]), response.text


def test_it_03_04_an_unknown_metric_or_side_is_a_4xx(api: ApiDriver, example: str) -> None:
    # Positive control first: the route exists, so the refusals below come from the contract.
    control = st.evidence(api, "ivy", example, "AN-01", "A")
    assert control.status_code == 200, control.text
    # api-sprint-03 §3.1: an unpublished metric id is 404 not_found; a bad side is 422.
    unknown = st.evidence(api, "ivy", example, "AN-99", "A")
    assert st.refusal(unknown) == (404, "not_found", []), unknown.text
    bad_side = st.evidence(api, "ivy", example, "AN-01", "C")
    assert st.refusal(bad_side) == (
        422,
        "validation_failed",
        [("side", "side_invalid")],
    ), bad_side.text


@pytest.mark.parametrize("side", st.SIDES)
@pytest.mark.parametrize("metric", st.METRICS)
def test_it_03_04_every_item_is_behind_the_metric_and_total_is_n(
    api: ApiDriver, example: str, metric: str, side: str
) -> None:
    refs = st.reference(st.WORKED_EXAMPLE)[metric][side]["rallies"]
    response = st.evidence(api, "ivy", example, metric, side)
    assert response.status_code == 200, response.text
    body = response.json()
    assert st.statslib.evidence_problems(body, refs) == []
    starts = [item["start_ms"] for item in body[st.statscontract.EVIDENCE_ITEMS]]
    assert starts == sorted(starts), "items are not in rally-time order"


def test_it_03_04_see_all_lists_every_rally(api: ApiDriver, example: str) -> None:
    refs = st.reference(st.WORKED_EXAMPLE)["AN-07"]["B"]["rallies"]
    assert len(refs) > 0
    response = st.evidence(api, "ivy", example, "AN-07", "B", limit=len(refs))
    assert response.status_code == 200, response.text
    body = response.json()
    assert sorted(i["number"] for i in body[st.statscontract.EVIDENCE_ITEMS]) == sorted(refs)[:10]
    assert body[st.statscontract.EVIDENCE_TOTAL] == len(refs)


def test_it_03_04_the_first_items_video_answers_range_with_206(
    api: ApiDriver, example: str
) -> None:
    response = st.evidence(api, "ivy", example, "AN-01", "A")
    assert response.status_code == 200, response.text
    body = response.json()
    rally_id = body[st.statscontract.EVIDENCE_ITEMS][0][st.statscontract.EVIDENCE_RALLY_ID]
    method, url = sb.path("media", match_id=example, rally_id=rally_id)
    link = api.request("ivy", method, url)
    assert link.status_code == 200, link.text
    with httpx.Client(timeout=10) as store:
        ranged = store.get(link.json()["url"], headers={"Range": "bytes=0-1023"})
    assert ranged.status_code == 206, ranged.text[:200]
    assert ranged.content[4:8] == b"ftyp"
