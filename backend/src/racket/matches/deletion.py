"""Deleting is two steps: hide now, purge later (ST-050, ST-051; deletion-and-purge.md §1;
ADR 0006, ADR 0042). Pure: the typed confirmation and the purge deadline the API states."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from racket.platform.errors import FieldError, ValidationFailed

CONFIRM = {"confirm": "delete"}  # api-sprint-03 §4.1 (DES FR-UX-90)
PURGE_WINDOW = timedelta(days=7)  # ADR 0006 interim: purged within 7 days (NFR-066 b)


def confirm_deletion(body: Any) -> None:
    """Exactly ``{"confirm": "delete"}``, else 422; any other key is ``unknown_field``. The
    value is compared, never echoed or logged."""
    if isinstance(body, Mapping) and any(key != "confirm" for key in body):
        raise ValidationFailed("unknown field", [FieldError(None, "unknown_field")])
    if not isinstance(body, Mapping) or body.get("confirm") != CONFIRM["confirm"]:
        raise ValidationFailed(
            "deletion not confirmed", [FieldError("confirm", "confirmation_required")]
        )


@dataclass(frozen=True, slots=True)
class Tombstone:
    deleted_at: datetime

    @property
    def purge_due_by(self) -> datetime:
        return self.deleted_at + PURGE_WINDOW

    def response(self) -> dict[str, Any]:
        due = self.purge_due_by.astimezone(UTC).isoformat(timespec="seconds")
        return {"deleted": True, "purge_due_by": due.replace("+00:00", "Z")}
