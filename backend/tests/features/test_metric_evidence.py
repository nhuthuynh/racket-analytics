"""API binding of tests/features/metric_evidence.feature (QA-ACC-3 for ST-047; FR-103, NFR-038).
"A link that plays it" is the Sprint 2 rally media link answering a Range request with 206.
The 23-rally stat is "Rallies won when receiving" for side A in ``stats.no_score_script(46)``
(the server always loses: A receives 23 times and wins all 23). Red first: ``red_until`` ST-047.

Marker ``red_until`` ST-047 removed (ST-047-API, TCR row 2026-10-09 in
docs/sprints/03/decisions/ST-047-API.md): the route is served and every row passes, so the file joins the per-PR gate.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from pytest_bdd import given, scenarios, then, when

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

scenarios("metric_evidence.feature")


@pytest.fixture
def ctx(api: ApiDriver, monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[dict[str, Any]]:
    st.with_statuses(monkeypatch, tmp_path)
    match_id = st.tagged_example(api, "ivy", "Evidence")
    yield {
        "api": api,
        "match": match_id,
        "games": [{"first_serving_side": "A", "tags": st.WORKED_EXAMPLE}],
    }
    st.clear_dictionary_cache()


def _plays(ctx: dict[str, Any], rally_id: str) -> None:
    method, url = sb.path("media", match_id=ctx["match"], rally_id=rally_id)
    link = ctx["api"].request("ivy", method, url)
    assert link.status_code == 200, link.text
    with httpx.Client(timeout=10) as store:
        assert store.get(link.json()["url"], headers={"Range": "bytes=0-15"}).status_code == 206


@given('Ivy\'s stats show "Rallies won on serve" with "n = 7"')
def serve_n7(ctx: dict[str, Any]) -> None:
    got = st.stats_body(ctx["api"], "ivy", ctx["match"])[st.statscontract.METRICS_KEY]
    assert got["AN-01"]["A"]["n"] == 7
    ctx["metric"] = ("AN-01", "A")


@given("a stat is based on 23 rallies")
def based_on_23(ctx: dict[str, Any]) -> None:
    ctx["games"] = st.no_score_script(46)
    ctx["match"] = st.tag_games(ctx["api"], "ivy", ctx["games"], "Twenty-three")
    got = st.stats_body(ctx["api"], "ivy", ctx["match"])[st.statscontract.METRICS_KEY]
    assert got["AN-02"]["A"]["n"] == 23
    ctx["metric"] = ("AN-02", "A")


@when('she opens "Show me" on it')
@when('Ivy opens "Show me" on it')
def show_me(ctx: dict[str, Any]) -> None:
    metric, side = ctx["metric"]
    response = st.evidence(ctx["api"], "ivy", ctx["match"], metric, side)
    assert response.status_code == 200, response.text
    ctx["evidence"] = response.json()


@then("she sees the 7 rallies her side served, each with a link that plays it")
def seven_served(ctx: dict[str, Any]) -> None:
    refs = st.statslib.starter_stats(ctx["games"])["AN-01"]["A"]["rallies"]
    assert len(refs) == 7
    assert st.statslib.evidence_problems(ctx["evidence"], refs) == []
    for item in ctx["evidence"][st.statscontract.EVIDENCE_ITEMS]:
        _plays(ctx, item[st.statscontract.EVIDENCE_RALLY_ID])


@then('she sees 10 rallies and "See all 23"')
def ten_and_see_all(ctx: dict[str, Any]) -> None:
    assert len(ctx["evidence"][st.statscontract.EVIDENCE_ITEMS]) == 10
    assert ctx["evidence"][st.statscontract.EVIDENCE_TOTAL] == 23


@when("Ivy opens her stats")
def opens_stats(ctx: dict[str, Any]) -> None:
    ctx["stats"] = st.stats_body(ctx["api"], "ivy", ctx["match"])


@then('every stat shows its sample size and a working "Show me"')
def every_stat_checkable(ctx: dict[str, Any]) -> None:
    reference = st.statslib.starter_stats(ctx["games"])
    for metric, sides in ctx["stats"][st.statscontract.METRICS_KEY].items():
        # A metric is {"entry", "A", "B"} (api-sprint-03 §2.1); "entry" is the dictionary entry,
        # not a side. Both sides must be present (KeyError otherwise; port of origin/sprint-03).
        for side in ("A", "B"):
            got = sides[side]
            sizes = [got.get(k) for k in ("n", "count", "turns") if k in got]
            assert sizes, f"{metric} {side} shows no sample size (NFR-038 b)"
            refs = reference[metric][side]["rallies"]
            response = st.evidence(ctx["api"], "ivy", ctx["match"], metric, side)
            assert response.status_code == 200, f"{metric} {side}: {response.status_code}"
            assert st.statslib.evidence_problems(response.json(), refs) == [], (metric, side)
