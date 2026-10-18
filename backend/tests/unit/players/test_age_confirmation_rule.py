"""Identity domain rule for FR-003 (ST-068a; api-sprint-04 §4; SEC-4 T4-AG-1, T4-AG-3).

Pure: no database, clock or framework. Negative cases first."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from racket.platform.errors import FieldError, ValidationFailed
from racket.players.domain import (
    AgeAnswer,
    AgeGate,
    AgeOutcome,
    pending_sign_in_expiry,
    under_age_message,
)

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("body", "error"),
    [
        ({}, FieldError("is_adult", "required")),
        (None, FieldError("is_adult", "required")),
        ({"is_adult": "true"}, FieldError("is_adult", "invalid")),
        ({"is_adult": 1}, FieldError("is_adult", "invalid")),
        ({"is_adult": False, "confirm": "yes"}, FieldError("confirm", "invalid")),
        ({"is_adult": True, "birth_date": "2010-01-01"}, FieldError(None, "unknown_field")),
        ([True], FieldError(None, "invalid")),
    ],
)
def test_a_malformed_answer_is_refused_with_one_field_code(body: object, error: FieldError) -> None:
    with pytest.raises(ValidationFailed) as refused:
        AgeAnswer.parse(body)

    assert refused.value.fields == (error,)


def test_under_age_on_an_existing_account_needs_the_typed_delete_confirmation() -> None:
    with pytest.raises(ValidationFailed) as refused:
        AgeAnswer.parse({"is_adult": False}).outcome(has_account=True)

    assert refused.value.fields == (FieldError("confirm", "confirmation_required"),)


def test_under_age_on_a_pending_sign_in_ends_it_and_ignores_confirm() -> None:
    assert AgeAnswer.parse({"is_adult": False}).outcome(has_account=False) is AgeOutcome.END_PENDING
    answer = AgeAnswer.parse({"is_adult": False, "confirm": "delete"})
    assert answer.outcome(has_account=False) is AgeOutcome.END_PENDING


def test_under_age_with_typed_confirmation_deletes_an_existing_account() -> None:
    answer = AgeAnswer.parse({"is_adult": False, "confirm": "delete"})

    assert answer.outcome(has_account=True) is AgeOutcome.DELETE_ACCOUNT


@pytest.mark.parametrize("has_account", [True, False])
def test_an_adult_answer_confirms(has_account: bool) -> None:
    assert AgeAnswer.parse({"is_adult": True}).outcome(has_account=has_account) is (
        AgeOutcome.CONFIRM
    )


def test_the_gate_refuses_an_unconfirmed_holder_only_when_on() -> None:
    assert AgeGate(enabled=True).admits(None) is False
    assert AgeGate(enabled=True).admits(NOW) is True
    assert AgeGate(enabled=False).admits(None) is True


def test_a_pending_sign_in_lives_at_most_a_day() -> None:
    assert pending_sign_in_expiry(NOW, timedelta(days=30)) == NOW + timedelta(hours=24)
    assert pending_sign_in_expiry(NOW, timedelta(hours=2)) == NOW + timedelta(hours=2)


@pytest.mark.parametrize("minimum", [18, 21])
def test_the_under_age_text_uses_the_configured_minimum(minimum: int) -> None:
    text = under_age_message(minimum)

    assert f"{minimum} or over" in text
    assert "We did not make an account for you." in text
    assert "birth" not in text.lower()
    assert "again" not in text.lower()
