"""Evidence behind a metric (ST-047; FR-103; api-sprint-03 §3.1). Negative cases first."""

from __future__ import annotations

from typing import Any

import pytest

from racket.analytics.evidence import EvidenceQuery, evidence_page
from racket.platform.errors import ValidationFailed

pytestmark = [pytest.mark.unit]


def _fields(exc: pytest.ExceptionInfo[ValidationFailed]) -> list[tuple[Any, str]]:
    return [(f.field, f.code) for f in exc.value.fields]


@pytest.mark.parametrize("limit", ["11", "0", "-1", "ten", "1.5", "", "9999999999"])
def test_a_limit_outside_1_to_10_is_refused(limit: str) -> None:
    with pytest.raises(ValidationFailed) as exc:
        EvidenceQuery.parse(side="A", limit=limit, cursor=None)
    assert _fields(exc) == [("limit", "invalid")]


@pytest.mark.parametrize("side", [None, "", "C", "a", "AB"])
def test_a_side_other_than_a_or_b_is_refused(side: str | None) -> None:
    with pytest.raises(ValidationFailed) as exc:
        EvidenceQuery.parse(side=side, limit=None, cursor=None)
    assert _fields(exc) == [("side", "side_invalid")]


@pytest.mark.parametrize("cursor", ["", "x", "-1", "1" * 12])
def test_a_cursor_that_is_not_ours_is_refused(cursor: str) -> None:
    with pytest.raises(ValidationFailed) as exc:
        EvidenceQuery.parse(side="B", limit="10", cursor=cursor)
    assert _fields(exc) == [("cursor", "invalid")]


def test_every_problem_is_reported_at_once() -> None:
    with pytest.raises(ValidationFailed) as exc:
        EvidenceQuery.parse(side="C", limit="11", cursor="x")
    assert _fields(exc) == [("side", "side_invalid"), ("limit", "invalid"), ("cursor", "invalid")]


def test_the_defaults() -> None:
    assert EvidenceQuery.parse(side="A", limit=None, cursor=None) == EvidenceQuery("A", 10, 0)


def _row(number: int, start: int) -> dict[str, Any]:
    return {"number": number, "rally_id": f"r{number}", "game": 1, "start_ms": start,
            "end_ms": start + 500, "winning_side": "A"}  # fmt: skip


ROWS = [_row(n, 1000 * n) for n in range(1, 31)]


def test_rallies_not_behind_the_metric_are_never_listed() -> None:
    items, total, cursor = evidence_page(ROWS, [3, 5, 7], EvidenceQuery("A", 10, 0))
    assert [i["number"] for i in items] == [3, 5, 7]
    assert (total, cursor) == (3, None)
    assert items[0] == {"number": 3, "rally_id": "r3", "game": 1, "start_ms": 3000,
                        "end_ms": 3500}  # fmt: skip


def test_total_is_n_and_pages_hold_at_most_the_limit_in_rally_time_order() -> None:
    behind = list(range(23, 0, -1))  # any order in, video order out
    first, total, cursor = evidence_page(ROWS, behind, EvidenceQuery("A", 10, 0))
    assert total == 23
    assert [i["number"] for i in first] == list(range(1, 11))
    second, _, cursor2 = evidence_page(ROWS, behind, EvidenceQuery("A", 10, int(cursor or 0)))
    third, _, cursor3 = evidence_page(ROWS, behind, EvidenceQuery("A", 10, int(cursor2 or 0)))
    assert [i["number"] for i in second + third] == list(range(11, 24))
    assert cursor3 is None


def test_a_number_missing_from_the_sheet_is_never_invented() -> None:
    items, total, _ = evidence_page(ROWS[:2], [1, 2, 99], EvidenceQuery("A", 10, 0))
    assert [i["number"] for i in items] == [1, 2]
    assert total == 3  # n stays the metric's n
