"""ST-062 (FR-124; api-sprint-04 §3.1, §3.3): the follow-through request checks.

``parse_op_id`` checks the ``Idempotency-Key`` header of ``POST .../done`` (1-64 characters
``A-Z a-z 0-9 - _``). A refusal is a 422 with one closed field code and never echoes
the input (NFR-058). Negative cases first.
"""

from __future__ import annotations

import pytest

from racket.coaching.schemas import parse_op_id
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
