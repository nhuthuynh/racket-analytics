"""Binds tests/features/stats_contract_doc.feature (PE-DESIGN-3; PE-R2S3-04, ADR 0033 rule 2).

The table is the real `docs/architecture/api-sprint-03.md` §2.1, read by the same parser as the
unit test (`tests.unit.analytics.test_stats_contract_doc.contract_fields`); the negative scenarios
edit that text before parsing, so the parser and the comparison are both exercised. The served
fields are `racket.analytics.starter_stats` over the projected worked example. No I/O besides
reading the contract file.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from racket.analytics.starter_stats import METRICS, starter_stats
from tests.unit.analytics.sheets import WORKED_EXAMPLE, one_game
from tests.unit.analytics.test_stats_contract_doc import CONTRACT, contract_fields

scenarios("stats_contract_doc.feature")


def mismatches(documented: dict[str, set[str]], served: dict[str, Any]) -> list[str]:
    """Metric ids whose documented per-side fields differ from the served ones (either side)."""
    out = []
    for metric in METRICS:
        for side in ("A", "B"):
            if documented[metric] != set(served[metric][side]) - {"rallies"}:
                out.append(metric)
                break
    return out


def _edit_row(text: str, metric: str, edit: Any) -> str:
    lines = text.splitlines()
    hits = [i for i, line in enumerate(lines) if line.startswith(f"| {metric} |")]
    assert len(hits) == 1, (metric, hits)
    edited = edit(lines[hits[0]])
    assert edited != lines[hits[0]], f"the {metric} row was not changed"  # the edit took effect
    lines[hits[0]] = edited
    return "\n".join(lines)


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given("the shipped api-sprint-03 per-side table")
def shipped(ctx: dict[str, Any]) -> None:
    ctx["text"] = CONTRACT.read_text(encoding="utf-8")


@given(parsers.parse('the api-sprint-03 per-side table with "{field}" removed from "{metric}"'))
def removed(ctx: dict[str, Any], field: str, metric: str) -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    pattern = re.compile(rf"`{re.escape(field)}`(?: \([^)]*\))?, ")
    ctx["text"] = _edit_row(text, metric, lambda line: pattern.sub("", line, count=1))


@given(parsers.parse('the api-sprint-03 per-side table with "{field}" added to "{metric}"'))
def added(ctx: dict[str, Any], field: str, metric: str) -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    ctx["text"] = _edit_row(text, metric, lambda line: line.rstrip(" |") + f", `{field}` |")


@given(parsers.parse('a per-side table with rows for "{metrics}" only'))
def partial(ctx: dict[str, Any], metrics: str) -> None:
    ctx["text"] = f"### 2.1\n| {metrics} | `k`, `n` |\n### 2.2\n"


@when("the table is read")
def read(ctx: dict[str, Any]) -> None:
    try:
        ctx["fields"] = contract_fields(ctx["text"])
    except ValueError as exc:
        ctx["error"] = str(exc)


@when("the table is compared with the starter stats of the worked example")
def compare(ctx: dict[str, Any]) -> None:
    ctx["fields"] = contract_fields(ctx["text"])
    ctx["mismatches"] = mismatches(ctx["fields"], starter_stats(one_game(WORKED_EXAMPLE)))


@then(parsers.parse('the comparison fails, naming "{metric}"'))
def fails(ctx: dict[str, Any], metric: str) -> None:
    assert ctx["mismatches"] == [metric]


@then(parsers.parse('it is refused, naming "{metric}"'))
def refused(ctx: dict[str, Any], metric: str) -> None:
    assert "fields" not in ctx
    assert metric in ctx["error"]


@then("the comparison passes for every metric and side")
def passes(ctx: dict[str, Any]) -> None:
    assert ctx["mismatches"] == []


@then(parsers.parse('"{metric}" documents "{field}"'))
def documents(ctx: dict[str, Any], metric: str, field: str) -> None:
    assert field in ctx["fields"][metric]
