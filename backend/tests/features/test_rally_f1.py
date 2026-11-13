"""Binds tests/features/rally_f1.feature (ST-084b; NFR-006.1-.4; ADR 0004, ADR 0060 row M11).

Pure domain: the real ``racket.dataset.rally_f1`` matcher on rallies written in the scenario as
``start-end`` seconds; no API, database or file.
"""

from __future__ import annotations

from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from racket.dataset.rally_f1 import Rally, match_rallies

scenarios("rally_f1.feature")


def _rallies(text: str) -> list[Rally]:
    out = []
    for part in text.split(","):
        start, end = part.strip().split("-")
        out.append(Rally(float(start), float(end)))
    return out


@pytest.fixture
def ctx() -> dict[str, Any]:
    return {}


@given(parsers.parse('the gold rallies "{text}"'))
def gold(ctx: dict[str, Any], text: str) -> None:
    ctx["gold"] = _rallies(text)


@given(parsers.parse('the predicted rallies "{text}"'))
def predicted(ctx: dict[str, Any], text: str) -> None:
    ctx["predicted"] = _rallies(text)


@when("the predictions are matched against the gold rallies")
def match(ctx: dict[str, Any]) -> None:
    ctx["result"] = match_rallies(ctx["predicted"], ctx["gold"])


@then(
    parsers.parse(
        "there are {tp:d} true positives, {fp:d} false positives and {fn:d} false negatives"
    )
)
def counts(ctx: dict[str, Any], tp: int, fp: int, fn: int) -> None:
    result = ctx["result"]
    assert (result.tp, result.fp, result.fn) == (tp, fp, fn)


@then(parsers.parse("the rally F1 is {pct:f} %"))
def f1_percent(ctx: dict[str, Any], pct: float) -> None:
    assert round(ctx["result"].f1_pct, 1) == pct
