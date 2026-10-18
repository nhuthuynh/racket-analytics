"""ST-062 (FR-124; api-sprint-04 §3.1, §3.3): the follow-through request checks.

``parse_op_id`` checks the ``Idempotency-Key`` header of ``POST .../done`` (1-64 characters
``A-Z a-z 0-9 - _``); ``parse_swap_body`` the closed ``{"reason"}`` body of ``.../swap`` (optional,
1-200 characters after trim). A refusal is a 422 with one closed field code and never echoes
the input (NFR-058). Negative cases first.
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.coaching.schemas import REASON_MAX, parse_op_id, parse_swap_body
from racket.platform.errors import FieldError, ValidationFailed

pytestmark = pytest.mark.unit


def _fields(exc: pytest.ExceptionInfo[ValidationFailed]) -> list[FieldError]:
    return list(exc.value.fields)


@pytest.mark.parametrize(
    ("header", "code"),
    [
        (None, "required"),
        ("", "required"),
        ("x" * 65, "invalid"),
        ("has space", "invalid"),
        ("semi;colon", "invalid"),
        ("é-accent", "invalid"),
        ("line\nbreak", "invalid"),
    ],
)
def test_a_missing_or_malformed_idempotency_key_is_refused(header: str | None, code: str) -> None:
    with pytest.raises(ValidationFailed) as exc:
        parse_op_id(header)
    assert _fields(exc) == [FieldError("Idempotency-Key", code)]
    assert header is None or not header or header not in str(exc.value)


@pytest.mark.parametrize("key", ["a", "x" * 64, "3f0c1d2e-9a7b-4c1d-8e2f-0a1b2c3d4e5f", "op_1-A"])
def test_a_well_formed_idempotency_key_is_the_op_id(key: str) -> None:
    assert parse_op_id(key) == key


@pytest.mark.parametrize(
    ("body", "fields"),
    [
        ([], [FieldError(None, "invalid")]),
        ("too hard", [FieldError(None, "invalid")]),
        ({"reason": "ok", "why": "x"}, [FieldError(None, "unknown_field")]),
        ({"reason": 3}, [FieldError("reason", "invalid")]),
        ({"reason": "   "}, [FieldError("reason", "invalid")]),
        ({"reason": ""}, [FieldError("reason", "invalid")]),
        ({"reason": "x" * 201}, [FieldError("reason", "too_long")]),
    ],
)
def test_a_bad_swap_body_is_refused_with_its_field_code(body: Any, fields: list[FieldError]) -> None:
    with pytest.raises(ValidationFailed) as exc:
        parse_swap_body(body)
    assert _fields(exc) == fields


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        (None, None),
        ({}, None),
        ({"reason": None}, None),
        ({"reason": "  Too hard on my wrist  "}, "Too hard on my wrist"),
        ({"reason": "x" * 200}, "x" * 200),
        ({"reason": " " + "y" * 200 + " "}, "y" * 200),  # 200 after trim
    ],
)
def test_a_good_swap_body_gives_the_trimmed_reason(body: Any, reason: str | None) -> None:
    assert REASON_MAX == 200
    assert parse_swap_body(body) == reason
