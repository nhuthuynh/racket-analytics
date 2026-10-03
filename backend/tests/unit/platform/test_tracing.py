"""traceparent validation (ST-005; W3C Trace Context; AQS/OPS-06). Pure string checks."""

from __future__ import annotations

import pytest

from racket.platform.tracing import valid_traceparent
from tests.support.tracing import MALFORMED_TRACEPARENTS, VALID_TRACEPARENT


@pytest.mark.parametrize("value", [*MALFORMED_TRACEPARENTS, None, "", VALID_TRACEPARENT + "-x"])
def test_malformed_or_oversized_headers_are_refused(value: str | None) -> None:
    assert valid_traceparent(value) is False


@pytest.mark.parametrize(
    "value",
    [VALID_TRACEPARENT, "01-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-00-future"],
)
def test_well_formed_headers_are_accepted(value: str) -> None:
    assert valid_traceparent(value) is True
