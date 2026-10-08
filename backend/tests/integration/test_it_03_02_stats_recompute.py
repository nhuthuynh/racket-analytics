"""IT-03-02 (ST-046; FR-100, NFR-017 analogue, ddd-guidelines §4.1): Events <-> DB.

* A correction (``ScoreCorrected``) recomputes the stats: rally 3 of the worked example
  switched to side A changes AN-02 for A from 2/6 to 2/5 (decision-log 2026-10-06), and the
  stats equal the corrected reference within 5 s.
* The same event delivered twice gives one snapshot version (idempotent).
* A failure in the recompute does not roll back the tag (separate transaction, after the
  scoring commit) and is retried: the rally stays stored and the stats become current.

The event-consumer seam is the QA proposal ``racket.analytics.snapshot:handle`` until PE-2
names it (analytics-snapshots.md); a different name is a seam change, not a test change.
Written red first (QA-ACC-3): ``red_until`` ST-046.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Iterator
from typing import Any

import pytest
import sqlalchemy as sa

from tests.support import scorebook as sb
from tests.support import stats as st
from tests.support.api import ApiDriver
from tests.support.contract import Seam

pytestmark = [pytest.mark.red_until(story="ST-046"), pytest.mark.needs_verification]

CURRENT_WITHIN_S = 5.0  # NFR-017 analogue (scorecard G03-02)
SNAPSHOT_REPLAY = Seam(
    "racket.analytics.snapshot:replay_latest_event",
    "ST-046",
    "replay_latest_event(session, match_id) delivers the match's latest scoring event again "
    "to the snapshot consumer (test seam; PE-2 names the consumer)",
)
STARTER_STATS = Seam("racket.analytics.starter_stats:starter_stats", "ST-044")


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[None]:
    st.with_statuses(monkeypatch, tmp_path)
    yield
    st.clear_dictionary_cache()


def _until_current(api: ApiDriver, match_id: str, expected: dict[str, Any]) -> list[str]:
    deadline = time.monotonic() + CURRENT_WITHIN_S
    diffs: list[str] = ["never read"]
    while time.monotonic() < deadline:
        response = st.stats(api, "ivy", match_id)
        if response.status_code == 200:
            diffs = st.stats_diffs(expected, response.json())
            if not diffs:
                return []
        time.sleep(0.1)
    return diffs


def _snapshot_versions(engine: Any, match_id: str) -> int:
    with engine.connect() as conn:
        tables = (
            conn.execute(
                sa.text(
                    "SELECT table_name FROM information_schema.columns "
                    "WHERE table_schema = current_schema() "
                    "AND column_name IN ('match_id', 'metric_def_version') "
                    "GROUP BY table_name HAVING count(*) = 2"
                )
            )
            .scalars()
            .all()
        )
        assert tables, "no snapshot table"
        return sum(
            int(
                conn.execute(
                    sa.text(f'SELECT count(*) FROM "{t}" WHERE match_id::text = :m'),
                    {"m": match_id},
                ).scalar_one()
            )
            for t in tables
        )


def test_it_03_02_a_correction_recomputes_the_stats(api: ApiDriver, published: None) -> None:
    match_id = st.tagged_example(api, "ivy", "IT-03-02 correction")
    before = st.stats_body(api, "ivy", match_id)[st.statscontract.METRICS_KEY]["AN-02"]["A"]
    assert (before["k"], before["n"]) == (2, 6)
    response = st.correct_rally_3(api, "ivy", match_id)
    assert response.status_code == 200, response.text
    assert _until_current(api, match_id, st.reference(st.corrected_example())) == []
    after = st.stats_body(api, "ivy", match_id)[st.statscontract.METRICS_KEY]["AN-02"]["A"]
    assert (after["k"], after["n"]) == (2, 5)


def test_it_03_02_the_same_event_twice_gives_one_snapshot_version(
    api: ApiDriver, committed_db: Any, published: None
) -> None:
    match_id = st.tagged_example(api, "ivy", "IT-03-02 twice")
    st.stats_body(api, "ivy", match_id)
    versions = _snapshot_versions(committed_db, match_id)
    assert versions >= 1
    with committed_db.begin() as conn:
        SNAPSHOT_REPLAY.load()(conn, match_id)
    assert _snapshot_versions(committed_db, match_id) == versions
    body = st.stats_body(api, "ivy", match_id)
    assert st.stats_diffs(st.reference(st.WORKED_EXAMPLE), body) == []


def test_it_03_02_a_failing_recompute_keeps_the_tag_and_is_retried(
    api: ApiDriver, monkeypatch: pytest.MonkeyPatch, published: None
) -> None:
    match_id = sb.ready_match(api, "ivy", "IT-03-02 failure")
    target = STARTER_STATS.load()
    calls = {"n": 0}

    def fails_once(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("injected recompute failure (IT-03-02)")
        return target(*args, **kwargs)

    import racket.analytics.starter_stats as module

    monkeypatch.setattr(module, "starter_stats", fails_once)
    for name in ("racket.analytics.snapshot", "racket.analytics.api"):
        loaded = sys.modules.get(name)
        if loaded is not None and hasattr(loaded, "starter_stats"):
            monkeypatch.setattr(loaded, "starter_stats", fails_once)

    first = st.WORKED_EXAMPLE[:1]
    responses = api.run(sb.tag_all(api.as_user("ivy"), match_id, first))
    assert responses[0].status_code == 201  # the tag commits although the recompute failed
    rows = sb.sheet_body(api, "ivy", match_id)["rows"]
    assert len(rows) == 1
    assert calls["n"] >= 1, "the recompute was never called, so the failure was not injected"
    assert _until_current(api, match_id, st.reference(first)) == []
