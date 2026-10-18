"""When a review video is deleted (FR-008 user rule; ADR 0006; api-sprint-04 §5). Pure.

R1 has no normalised 720p proxy yet (FR-089 normalisation is R2), so the review video the player
plays is the stored upload. Its deletion date is the analysed time (R1: the probe's success
time) plus the owner's chosen days; "until I delete" (``None``) and a video not analysed yet have
no date. The date always follows the owner's current choice: a longer choice keeps only what is
not yet purged (T4-RT-4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class ReviewVideoSchedule:
    days: int | None  # None: until I delete it

    def __post_init__(self) -> None:
        if self.days is not None and (
            isinstance(self.days, bool) or not isinstance(self.days, int) or self.days < 1
        ):
            raise ValueError("retention is whole days of at least 1")

    def delete_at(self, analysed_at: datetime | None) -> datetime | None:
        if analysed_at is None or self.days is None:
            return None
        if analysed_at.tzinfo is None:
            raise ValueError("the analysed time needs a time zone")
        return analysed_at + timedelta(days=self.days)

    def is_due(self, analysed_at: datetime | None, now: datetime) -> bool:
        """Due from the deletion date on (the date has come, so the video goes)."""
        date = self.delete_at(analysed_at)
        return date is not None and now >= date
