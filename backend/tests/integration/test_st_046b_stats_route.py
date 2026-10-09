"""ST-046b integration (FR-100, NFR-051; api-sprint-03 §2.1; ADR 0041): ``GET
/matches/{match_id}/stats`` over the real app and Postgres. Negative cases first: another
account, an unknown and a malformed id all get the same 404 and no stats. Then the body: the
versions, the unofficial label, ``Cache-Control: no-store``, and ``low_sample_rule`` taken from
the digested dictionary (one source, ADR 0041), so a changed rule shows in the response.
"""

from __future__ import annotations

import json
import uuid
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


def test_st_046b_another_account_an_unknown_or_malformed_id_get_the_same_404(
    api: ApiDriver,
) -> None:
    match_id = st.tagged_example(api, "ivy", "ST-046b BOLA")
    api.as_user("carlos")
    attacker = st.stats(api, "carlos", match_id)
    unknown = st.stats(api, "carlos", str(uuid.uuid4()))
    malformed = api.request("carlos", "GET", "/matches/not-a-uuid/stats")
    assert attacker.status_code == 404, attacker.text
    assert _strip(attacker) == _strip(unknown) == _strip(malformed)
    assert "metrics" not in attacker.text


def test_st_046b_the_body_carries_the_versions_the_label_and_no_store(api: ApiDriver) -> None:
    from racket.sports.pickleball import metrics

    st.clear_dictionary_cache()
    match_id = st.tagged_example(api, "ivy", "ST-046b body")
    response = st.stats(api, "ivy", match_id)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["match_id"] == match_id
    assert body["metric_def_version"] == metrics.load_dictionary().version
    assert isinstance(body["rules_version"], str) and body["rules_version"]
    assert body["unofficial"] is True
    assert body["label"] == st.UNOFFICIAL
    assert body["sheet_version"] >= 1


@pytest.fixture
def wider_rule(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[float]:
    """The shipped dictionary with its interval-width rule changed to 0.25 (a copy)."""
    from racket.sports.pickleball import metrics

    data = json.loads(metrics.METRICS_PATH.read_text(encoding="utf-8"))
    data["low_sample"] = {"max_interval_width": 0.25}
    path = tmp_path / "metrics.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(metrics, "METRICS_PATH", path)
    metrics.load_dictionary.cache_clear()
    yield 0.25
    metrics.load_dictionary.cache_clear()


def test_st_046b_low_sample_rule_is_the_dictionarys_own(
    api: ApiDriver, wider_rule: float
) -> None:
    match_id = st.tagged_example(api, "ivy", "ST-046b rule")
    body = st.stats_body(api, "ivy", match_id)
    assert body["low_sample_rule"] == {"max_interval_width": wider_rule}
