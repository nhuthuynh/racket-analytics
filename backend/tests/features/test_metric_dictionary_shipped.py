"""Binds tests/features/metric_dictionary_shipped.feature (GS-AN-1-V2; ST-043 round 2; FR-102).

Domain binding: the steps load the shipped dictionary through ``MetricDictionary`` and read the
coach's status rows from ``docs/domain/metric-dictionary.md`` (``tests.support.metric_status``).
The negative scenarios set one status on one side only, on copies; nothing is written.
"""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from racket.sports.pickleball.metrics import METRICS_PATH, MetricDictionary
from tests.support.metric_status import mismatches, recorded_statuses

scenarios("metric_dictionary_shipped.feature")


def _shipped_data() -> dict[str, Any]:
    return copy.deepcopy(json.loads(METRICS_PATH.read_text(encoding="utf-8")))


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {"recorded": recorded_statuses(), "dictionary": MetricDictionary.parse(_shipped_data())}


@given(parsers.parse('the coach records "{entry_id}" as "{status}"'))
def coach_records(ctx: dict[str, Any], entry_id: str, status: str) -> None:
    ctx["recorded"] = {entry_id: status}


@given(parsers.parse('the shipped dictionary has "{entry_id}" as "{status}"'))
def shipped_has(ctx: dict[str, Any], entry_id: str, status: str) -> None:
    data = _shipped_data()
    data["entries"] = [e for e in data["entries"] if e["id"] == entry_id]
    data["entries"][0]["status"] = status
    ctx["dictionary"] = MetricDictionary.parse(data)


@given("the coach's status rows in the metric dictionary document")
def coach_rows(ctx: dict[str, Any]) -> None:
    ctx["recorded"] = recorded_statuses()
    assert sorted(ctx["recorded"]) == [f"AN-0{i}" for i in range(1, 8)]


@given("the shipped dictionary")
def shipped(ctx: dict[str, Any]) -> None:
    ctx["dictionary"] = MetricDictionary.parse(_shipped_data())


@when("the shipped statuses are compared with the coach's record")
def compare(ctx: dict[str, Any]) -> None:
    shipped_statuses = {e.id: e.status for e in ctx["dictionary"].entries}
    ctx["differences"] = mismatches(shipped_statuses, ctx["recorded"])


@then(parsers.parse('the difference "{difference}" is reported'))
def difference_reported(ctx: dict[str, Any], difference: str) -> None:
    assert ctx["differences"] == [difference]


@then("no difference is reported")
def no_difference(ctx: dict[str, Any]) -> None:
    assert ctx["differences"] == []


@then(parsers.parse('the published metrics are "{ids}"'))
def published_are(ctx: dict[str, Any], ids: str) -> None:
    assert [e.id for e in ctx["dictionary"].published()] == ids.split(", ")
