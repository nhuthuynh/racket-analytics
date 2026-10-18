"""The player's review video choice (ST-069; FR-008; OQ-07; api-sprint-04 §5; T4-RT-1).

Negative cases first: the body is closed and holds only ``review_video_days``; a value is one of
the configured choices exactly (no strings, floats or booleans); one field code, never an echo
of the input. Then every configured choice, ``null`` meaning "until I delete"."""

from __future__ import annotations

from typing import Any

import pytest

from racket.platform.errors import ValidationFailed
from racket.players.domain import RetentionChoice

pytestmark = [pytest.mark.unit]

CHOICES = (30, 90, 365, None)


def _codes(body: Any) -> list[tuple[str | None, str]]:
    with pytest.raises(ValidationFailed) as caught:
        RetentionChoice.parse(body, CHOICES)
    return [(f.field, f.code) for f in caught.value.fields]


@pytest.mark.parametrize("body", [None, [], "30", 30])
def test_a_body_that_is_not_an_object_is_invalid(body: Any) -> None:
    assert _codes(body) == [(None, "invalid")]


def test_an_unknown_key_is_refused_so_no_account_id_can_be_named() -> None:
    assert _codes({"review_video_days": 30, "account_id": "x"}) == [(None, "unknown_field")]


def test_the_days_are_required() -> None:
    assert _codes({}) == [("review_video_days", "required")]


@pytest.mark.parametrize("value", [60, 0, -30, "30", 30.0, True, False, [30], {"d": 30}, "none"])
def test_a_value_outside_the_choices_is_unknown(value: Any) -> None:
    assert _codes({"review_video_days": value}) == [("review_video_days", "unknown_value")]


def test_a_choice_not_configured_is_unknown() -> None:
    with pytest.raises(ValidationFailed):
        RetentionChoice.parse({"review_video_days": None}, (30, 90))


@pytest.mark.parametrize("value", CHOICES)
def test_every_configured_choice_is_accepted(value: int | None) -> None:
    assert RetentionChoice.parse({"review_video_days": value}, CHOICES).days == value
