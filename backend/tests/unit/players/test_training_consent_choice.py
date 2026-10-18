"""The player's training-data opt-in (ST-070; FR-009; api-sprint-04 §6; SEC-4 T4-CS-4).

Negative cases first: the body is closed and holds only ``opt_in``; the value is a JSON boolean
exactly (no strings, numbers or null); one field code, never an echo of the input. Then both
values."""

from __future__ import annotations

from typing import Any

import pytest

from racket.platform.errors import ValidationFailed
from racket.players.domain import TrainingConsentChoice

pytestmark = [pytest.mark.unit]


def _codes(body: Any) -> list[tuple[str | None, str]]:
    with pytest.raises(ValidationFailed) as caught:
        TrainingConsentChoice.parse(body)
    return [(f.field, f.code) for f in caught.value.fields]


@pytest.mark.parametrize("body", [None, [], "true", True, 1])
def test_a_body_that_is_not_an_object_is_invalid(body: Any) -> None:
    assert _codes(body) == [(None, "invalid")]


def test_an_unknown_key_is_refused_so_no_account_id_can_be_named() -> None:
    assert _codes({"opt_in": True, "account_id": "x"}) == [(None, "unknown_field")]


def test_the_choice_is_required() -> None:
    assert _codes({}) == [("opt_in", "required")]


@pytest.mark.parametrize("value", ["true", "false", 1, 0, None, 1.0, [True], {"v": True}])
def test_only_a_json_boolean_is_accepted(value: Any) -> None:
    assert _codes({"opt_in": value}) == [("opt_in", "invalid")]


def test_the_refusal_never_echoes_the_input() -> None:
    with pytest.raises(ValidationFailed) as caught:
        TrainingConsentChoice.parse({"opt_in": "secret-value"})
    assert "secret-value" not in str(caught.value)


@pytest.mark.parametrize("value", [True, False])
def test_both_values_are_accepted(value: bool) -> None:
    assert TrainingConsentChoice.parse({"opt_in": value}).opt_in is value
