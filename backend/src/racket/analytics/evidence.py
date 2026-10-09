"""The "Show me" list: the rallies behind one metric and side (ST-047; FR-103; api-sprint-03 §3.1;
analytics-snapshots.md §5.4). Pure: the caller passes the sheet rows and the numbers from the
same snapshot, so numbers and rally ids always come from one sheet version.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from racket.platform.errors import FieldError, ValidationFailed

EVIDENCE_MAX = 10  # FR-103 "up to 10"
_ITEM_KEYS = ("number", "rally_id", "game", "start_ms", "end_ms")


def _small_int(raw: str, digits: int) -> int | None:
    return int(raw) if raw.isascii() and raw.isdigit() and len(raw) <= digits else None


@dataclass(frozen=True, slots=True)
class EvidenceQuery:
    side: str
    limit: int
    offset: int

    @classmethod
    def parse(cls, *, side: str | None, limit: str | None, cursor: str | None) -> EvidenceQuery:
        problems = []
        if side not in ("A", "B"):
            problems.append(FieldError("side", "side_invalid"))
        size = EVIDENCE_MAX if limit is None else _small_int(limit, 2)
        if size is None or not 1 <= size <= EVIDENCE_MAX:
            problems.append(FieldError("limit", "invalid"))
        offset = 0 if cursor is None else _small_int(cursor, 9)
        if offset is None:
            problems.append(FieldError("cursor", "invalid"))
        if problems:
            raise ValidationFailed("evidence query is not valid", problems)
        return cls(str(side), int(size or EVIDENCE_MAX), int(offset or 0))


def evidence_page(
    rows: Sequence[Mapping[str, Any]], numbers: Sequence[int], query: EvidenceQuery
) -> tuple[list[dict[str, Any]], int, str | None]:
    """(items of this page in rally-time order, total n, next cursor or ``None``)."""
    wanted = set(numbers)
    behind = sorted(
        (r for r in rows if r.get("number") in wanted),
        key=lambda r: (r["start_ms"], r["number"]),
    )
    page = behind[query.offset : query.offset + query.limit]
    after = query.offset + len(page)
    cursor = str(after) if after < len(behind) else None
    return [{k: r[k] for k in _ITEM_KEYS} for r in page], len(numbers), cursor
