"""Match & Scoring's published events (context map R6; analytics-snapshots.md §4.1)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScoreSheetChanged:
    """A scorebook command committed: the sheet of ``match_id`` is now at ``sheet_version``.
    Stands for ``RallyScored`` and ``ScoreCorrected``; ids and a version only, never content."""

    match_id: uuid.UUID
    sheet_version: int
    owner_id: uuid.UUID
    kind: str
