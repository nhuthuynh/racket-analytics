"""CI-NIGHTLY-PERF read cost of the dashboard reads (NFR-010 "dashboard", NFR-013; G05 CI first;
analytics-snapshots.md §4.2 read repair, invariant S4/S8).

Root cause of the nightly 50 RPS miss (CI run 43007950254, main b7bf0b7: stats p95 310 ms,
evidence p99 1200 ms; decisions/CI-NIGHTLY-PERF.md): every ``GET .../stats`` and
``GET .../evidence`` of an unchanged match sent 9 statements, 5 of them only to re-read and
re-project the whole scorebook (ownership as a full aggregate with participants, the match head,
games, rallies, corrections) in the one GIL-bound API process. Near saturation every extra
round trip waits for the GIL again, so a correction burst turned into a 1.2 s tail on exactly
the routes that replay the scorebook. A read of an unchanged match now reuses the projected
sheet of the scorebook version it read under the match row share lock; any change (a tag,
correction or undo bumps the version, a deleted match is gone) is read live.

HTTP on Postgres, matches tagged through the API. Negative cases first.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from tests.support import stats as st
from tests.support.api import ApiDriver
from tests.support.statements import SCOREBOOK_TABLES, reads_of, statements, writes

pytestmark = [pytest.mark.needs_verification]

# Statements of a dashboard read whose match is unchanged: the session, the ownership check,
# the match head under the share lock and the snapshot (was 9).
READ_BUDGET = 4
METRIC, SIDE = "AN-01", "A"  # the dashboard read of the CI Locust baseline (G03-05)


@pytest.fixture
def published(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[None]:
    st.with_statuses(monkeypatch, tmp_path)
    yield
    st.clear_dictionary_cache()


@pytest.fixture
def example(api: ApiDriver, committed_db: Any, published: None) -> str:
    match_id = st.tagged_example(api, "ivy", "CI-NIGHTLY-PERF")
    st.stats_body(api, "ivy", match_id)  # the snapshot is current and the sheet was read once
    return match_id


def _evidence(api: ApiDriver, user: str, match_id: str) -> dict[str, Any]:
    response = st.evidence(api, user, match_id, METRIC, SIDE)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


# ------------------------------------------------------------------ a changed match is live
def test_a_correction_after_a_read_shows_in_the_next_stats_and_evidence(
    api: ApiDriver, example: str
) -> None:
    before = _evidence(api, "ivy", example)
    assert st.correct_rally_3(api, "ivy", example).status_code == 200
    body = st.stats_body(api, "ivy", example)
    assert st.stats_diffs(st.reference(st.corrected_example()), body) == []
    after = _evidence(api, "ivy", example)
    assert after["sheet_version"] == body["sheet_version"] > before["sheet_version"]


def test_a_deleted_match_after_a_read_is_not_found(api: ApiDriver, example: str) -> None:
    assert st.delete_match(api, "ivy", example).status_code in (200, 202, 204)
    assert st.stats(api, "ivy", example).status_code == 404
    assert st.evidence(api, "ivy", example, METRIC, SIDE).status_code == 404


def test_another_account_never_reads_a_match_the_owner_read(
    api: ApiDriver, example: str
) -> None:
    assert st.refusal(st.stats(api, "carlos", example))[:2] == (404, "not_found")
    refused = st.evidence(api, "carlos", example, METRIC, SIDE)
    assert st.refusal(refused)[:2] == (404, "not_found")


# ------------------------------------------------------------------ an unchanged match is cheap
def test_a_stats_read_of_an_unchanged_match_replays_no_scorebook(
    api: ApiDriver, example: str
) -> None:
    first = st.stats_body(api, "ivy", example)
    with statements() as sent:
        again = st.stats_body(api, "ivy", example)
    assert again == first
    assert reads_of(sent, *SCOREBOOK_TABLES) == []
    assert writes(sent) == []
    assert len(sent) <= READ_BUDGET, sent


def test_an_evidence_read_of_an_unchanged_match_replays_no_scorebook(
    api: ApiDriver, example: str
) -> None:
    first = _evidence(api, "ivy", example)
    with statements() as sent:
        again = _evidence(api, "ivy", example)
    assert again == first
    assert reads_of(sent, *SCOREBOOK_TABLES) == []
    assert writes(sent) == []
    assert len(sent) <= READ_BUDGET, sent
