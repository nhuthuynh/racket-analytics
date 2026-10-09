"""The delete confirmation and the purge deadline (ST-050, ST-051; api-sprint-03 §4.1-§4.2;
ADR 0006, ADR 0042). Negative cases first: anything but exactly ``{"confirm": "delete"}``."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from racket.matches.deletion import PURGE_WINDOW, Tombstone, confirm_deletion
from racket.platform.errors import ValidationFailed

pytestmark = [pytest.mark.unit]


def _fields(exc: pytest.ExceptionInfo[ValidationFailed]) -> list[tuple[Any, str]]:
    return [(f.field, f.code) for f in exc.value.fields]


@pytest.mark.parametrize(
    "body",
    [None, {}, [], "delete", 1, True, {"confirm": "yes"}, {"confirm": "DELETE"},
     {"confirm": "delete "}, {"confirm": None}, {"confirm": ["delete"]}, {"confirm": "del\x00ete"},
     {"confirm": "\ud800"}],
)  # fmt: skip
def test_anything_but_the_typed_confirmation_is_refused(body: Any) -> None:
    with pytest.raises(ValidationFailed) as exc:
        confirm_deletion(body)
    assert _fields(exc) == [("confirm", "confirmation_required")]


def test_an_unknown_key_is_refused_as_unknown_field() -> None:
    with pytest.raises(ValidationFailed) as exc:
        confirm_deletion({"confirm": "delete", "also": 1})
    assert _fields(exc) == [(None, "unknown_field")]


def test_the_typed_confirmation_is_accepted() -> None:
    confirm_deletion({"confirm": "delete"})


def test_everything_is_purged_within_seven_days_of_the_deletion() -> None:
    at = datetime(2026, 10, 7, 9, 15, tzinfo=UTC)
    tombstone = Tombstone(at)
    assert PURGE_WINDOW.days == 7
    assert tombstone.purge_due_by == datetime(2026, 10, 14, 9, 15, tzinfo=UTC)
    assert tombstone.response() == {"deleted": True, "purge_due_by": "2026-10-14T09:15:00Z"}
