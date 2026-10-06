"""IT-03-01 (ST-044, ST-046; FR-100, FR-101, NFR-004): API <-> DB, the stats of a tagged match.

The coach's worked example (metric-dictionary §2) is tagged one rally at a time; after every
tag ``GET /matches/{id}/stats`` equals the independent reference ``statslib`` for the rallies so
far (k, n, value, Wilson bounds ±0.001, low-sample flag, by-player counts, runs, ending mix).
A 30-rally game is checked the same way. The response and the stored snapshot carry
``rules_version`` (PROVISIONAL-UNVERIFIED) and ``metric_def_version``; the response says
"unofficial scoring (rules not yet verified)" (FR-055, ADR 0023).

Every dictionary entry is published for this test (``stats.with_statuses``), so the numbers
are tested independently of COACH-1's data change; IT-03-03 tests the shipped statuses.
Written red first (QA-ACC-3): ``red_until`` ST-046.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
import sqlalchemy as sa

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver

pytestmark = [pytest.mark.red_until(story="ST-046"), pytest.mark.needs_verification]

WINNERS_30 = "BABBBABABABABBABAAAAAABABBBBBB"  # IT-02-01 (10-7-1 after rally 30, game not over)


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[dict[str, Any]]:
    data = st.with_statuses(monkeypatch, tmp_path)
    yield data
    st.clear_dictionary_cache()


def _check_envelope(body: dict[str, Any], dictionary: dict[str, Any]) -> None:
    assert body[st.statscontract.RULES_VERSION_KEY] == "PROVISIONAL-UNVERIFIED"
    assert body[st.statscontract.DEF_VERSION_KEY] == dictionary["version"]
    assert body["unofficial"] is True
    assert body["label"] == st.UNOFFICIAL


def test_it_03_01_a_match_with_no_rallies_has_every_metric_with_n_0_and_no_value(
    api: ApiDriver, published: dict[str, Any]
) -> None:
    match_id = sb.ready_match(api, "ivy", "IT-03-01 empty")
    body = st.stats_body(api, "ivy", match_id)
    _check_envelope(body, published)
    metrics = body[st.statscontract.METRICS_KEY]
    assert sorted(metrics) == list(st.METRICS)
    for metric in st.PROPORTIONS:
        for side in st.SIDES:
            got = metrics[metric][side]
            assert (got["n"], got["value"], got["low_sample"]) == (0, None, True), (metric, side)


def test_it_03_01_stats_equal_the_reference_after_every_tag_of_the_worked_example(
    api: ApiDriver, published: dict[str, Any]
) -> None:
    match_id = sb.ready_match(api, "ivy", "IT-03-01 worked example")
    client = api.as_user("ivy")
    for n in range(1, len(st.WORKED_EXAMPLE) + 1):
        api.run(sb.tag_all(client, match_id, st.WORKED_EXAMPLE[n - 1 : n]))
        body = st.stats_body(api, "ivy", match_id)
        diffs = st.stats_diffs(st.reference(st.WORKED_EXAMPLE[:n]), body)
        assert diffs == [], f"after rally {n}: {diffs}"
    _check_envelope(body, published)
    # the coach's hand count (metric-dictionary §2): A's serve win 4/7, receive 2/6
    an = body[st.statscontract.METRICS_KEY]
    assert (an["AN-01"]["A"]["k"], an["AN-01"]["A"]["n"]) == (4, 7)
    assert (an["AN-02"]["A"]["k"], an["AN-02"]["A"]["n"]) == (2, 6)


def test_it_03_01_a_thirty_rally_game_equals_the_reference(
    api: ApiDriver, published: dict[str, Any]
) -> None:
    plain = {"ending": "winner", "responsible_player": None, "fault_kind": None}
    tags = sb.taglib.with_times([{"winning_side": w, **plain} for w in WINNERS_30], 60_000)
    match_id = sb.ready_tagged_match(api, "ivy", tags=tags, title="IT-03-01 thirty")
    body = st.stats_body(api, "ivy", match_id)
    assert st.stats_diffs(st.reference(tags), body) == []


def test_it_03_01_the_snapshot_is_stored_with_its_versions(
    api: ApiDriver, committed_db: Any, published: dict[str, Any]
) -> None:
    match_id = st.tagged_example(api, "ivy", "IT-03-01 stored")
    body = st.stats_body(api, "ivy", match_id)
    with committed_db.connect() as conn:
        tables = (
            conn.execute(
                sa.text(
                    "SELECT table_name FROM information_schema.columns "
                    "WHERE table_schema = current_schema() "
                    "AND column_name IN ('match_id', 'metric_def_version', 'rules_version') "
                    "GROUP BY table_name HAVING count(*) = 3"
                )
            )
            .scalars()
            .all()
        )
        assert tables, "no snapshot table with match_id, metric_def_version and rules_version"
        stored = [
            row
            for table in tables
            for row in conn.execute(
                sa.text(
                    f'SELECT metric_def_version, rules_version FROM "{table}" '
                    "WHERE match_id::text = :m"
                ),
                {"m": match_id},
            ).all()
        ]
    assert stored, "the match has no stored snapshot"
    assert {tuple(r) for r in stored} == {
        (body[st.statscontract.DEF_VERSION_KEY], "PROVISIONAL-UNVERIFIED")
    }
