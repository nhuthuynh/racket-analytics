"""IT-03-03 (ST-043; FR-102, NFR-075): only coach-reviewed or verified metrics reach the API.

* A ``draft`` entry is absent from the stats response; a ``coach-reviewed`` one is present
  with its plain-language definition (shown by "How is this measured?").
* With the dictionary as shipped, the response holds exactly the published entries: none while
  every entry is ``draft`` (fail closed, scorecard §4.0), all seven once COACH-1 is done.

Written red first (QA-ACC-3): ``red_until`` ST-046 (the API part of ST-043 lands with it).

Marker ``red_until`` ST-046 removed (ST-046b, TCR row 2026-10-09 in
docs/sprints/03/decisions/ST-046b.md): the stats route is built and every row passes, so the
file is in the per-PR gate and the coverage selection.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest

from tests.support import stats as st
from tests.support.api import ApiDriver


@pytest.fixture
def an05_draft(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[dict[str, Any]]:
    data = st.with_statuses(monkeypatch, tmp_path, draft=("AN-05",))
    yield data
    st.clear_dictionary_cache()


def test_it_03_03_a_draft_entry_is_absent_and_a_reviewed_one_carries_its_definition(
    api: ApiDriver, an05_draft: dict[str, Any]
) -> None:
    match_id = st.tagged_example(api, "ivy", "IT-03-03 draft")
    body = st.stats_body(api, "ivy", match_id)
    metrics = body[st.statscontract.METRICS_KEY]
    assert "AN-05" not in metrics
    assert "AN-05" not in json.dumps(body)  # not hidden somewhere else in the body either
    assert "AN-02" in metrics
    an02 = next(e for e in an05_draft["entries"] if e["id"] == "AN-02")
    shown = json.dumps(metrics["AN-02"], ensure_ascii=False)
    assert an02["definition"] in shown, "the plain-language definition is not in the response"


def test_it_03_03_the_shipped_dictionary_decides_what_is_shown(api: ApiDriver) -> None:
    from racket.sports.pickleball import metrics as dictionary

    st.clear_dictionary_cache()
    published = sorted(e.id for e in dictionary.load_dictionary().published())
    match_id = st.tagged_example(api, "ivy", "IT-03-03 shipped")
    shown = sorted(st.stats_body(api, "ivy", match_id)[st.statscontract.METRICS_KEY])
    assert shown == published
