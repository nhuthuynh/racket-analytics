"""API binding of tests/features/metric_dictionary_stats.feature (QA-ACC-3 for ST-043; FR-102,
FR-055). The domain rules of the dictionary are bound by test_metric_dictionary.py (ST-043).
"How is this measured?" is the entry's plain-language definition in the stats response (the
browser shows it, E2E-03-03). Written red first: ``red_until`` ST-046 (the stats route).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.support import stats as st
from tests.support.api import ApiDriver

pytestmark = [pytest.mark.red_until(story="ST-046")]

scenarios("metric_dictionary_stats.feature")


@pytest.fixture
def ctx(api: ApiDriver, monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> Iterator[dict[str, Any]]:
    yield {"api": api, "monkeypatch": monkeypatch, "tmp_path": tmp_path}
    st.clear_dictionary_cache()


@given('metric AN-05 has status "draft"')
def an05_draft(ctx: dict[str, Any]) -> None:
    ctx["dictionary"] = st.with_statuses(ctx["monkeypatch"], ctx["tmp_path"], draft=("AN-05",))
    ctx["match"] = st.tagged_example(ctx["api"], "ivy", "Draft")


@given("AN-02 is coach-reviewed")
def an02_reviewed(ctx: dict[str, Any]) -> None:
    ctx["dictionary"] = st.with_statuses(ctx["monkeypatch"], ctx["tmp_path"])
    ctx["match"] = st.tagged_example(ctx["api"], "ivy", "Reviewed")


@given("the rules preset contains an unverified rule")
def unverified(ctx: dict[str, Any]) -> None:
    ctx["dictionary"] = st.with_statuses(ctx["monkeypatch"], ctx["tmp_path"])
    ctx["match"] = st.tagged_example(ctx["api"], "ivy", "Unofficial")


@when("Ivy opens her stats")
@when('Ivy opens "How is this measured?" on "Rallies won when receiving"')
def opens(ctx: dict[str, Any]) -> None:
    ctx["stats"] = st.stats_body(ctx["api"], "ivy", ctx["match"])


@then("AN-05 is not shown")
def an05_hidden(ctx: dict[str, Any]) -> None:
    assert "AN-05" not in ctx["stats"][st.statscontract.METRICS_KEY]
    assert "AN-05" not in json.dumps(ctx["stats"])
    assert "AN-01" in ctx["stats"][st.statscontract.METRICS_KEY]  # positive control


@then("she sees its definition in plain words")
def definition(ctx: dict[str, Any]) -> None:
    entry = next(e for e in ctx["dictionary"]["entries"] if e["id"] == "AN-02")
    shown = json.dumps(ctx["stats"][st.statscontract.METRICS_KEY]["AN-02"], ensure_ascii=False)
    assert entry["definition"] in shown


@then('she sees "unofficial scoring (rules not yet verified)"')
def unofficial(ctx: dict[str, Any]) -> None:
    assert ctx["stats"]["unofficial"] is True
    assert ctx["stats"]["label"] == st.UNOFFICIAL
