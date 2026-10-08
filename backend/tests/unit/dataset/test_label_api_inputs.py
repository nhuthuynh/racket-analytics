"""Label bodies with a non-finite number are refused before storage (ST-052c; IT-03-12 rule L11):
Python's JSON reader accepts NaN and Infinity, PostgreSQL JSONB does not (a 500 otherwise)."""

from __future__ import annotations

import pytest

from racket.dataset.api import finite_json

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), {"a": [1, float("-inf")]}, [0.5, float("nan")]]
)
def test_a_non_finite_number_anywhere_is_not_finite_json(value: object) -> None:
    assert not finite_json(value)


@pytest.mark.parametrize("value", [1, 0.5, "x", None, True, {"a": [1, 2.5]}, [[0.0, 1e300]]])
def test_finite_json_values_pass(value: object) -> None:
    assert finite_json(value)
