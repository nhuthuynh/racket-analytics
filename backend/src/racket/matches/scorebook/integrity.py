"""Confirmed-corrections fingerprint (ST-076b; NFR-045.3; ADR 0058 rule 4 step 10).

The correction trail is append-only (match-aggregate I8; migrations 0010, 0011), so every
committed row is a confirmed correction. Its fingerprint is the row count and the SHA-256 of
one canonical JSON line per row (sorted keys, UTC timestamps, ids as text), in the stable
order ``(match_id, version, id)``. Equal before a backup and after its restore means no
confirmed correction was lost or changed.

Only the corrections of live matches count (``matches.deleted_at IS NULL``): ADR 0058 rule 4
runs the purge (step 9) before this check (step 10), and the purge cascades a tombstoned
match's trail, so those rows are meant to be gone after a correct restore.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from racket.matches.repository import matches
from racket.matches.scorebook.repository import match_corrections


@dataclass(frozen=True)
class Fingerprint:
    """Unpacks as ``count, sha256``."""

    count: int
    sha256: str

    def __iter__(self) -> Iterator[Any]:
        return iter((self.count, self.sha256))


def _canonical(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("a correction timestamp has no time zone")
        return value.astimezone(UTC).isoformat()
    return value


def _line(row: Mapping[Any, Any]) -> str:
    fields = {str(key): _canonical(value) for key, value in row.items()}
    return json.dumps(fields, sort_keys=True, separators=(",", ":"))


def fingerprint_of(rows: Iterable[Mapping[Any, Any]]) -> Fingerprint:
    """Pure: the fingerprint of stored correction rows, whatever order they come in."""
    keyed = sorted(((str(r["match_id"]), int(r["version"]), str(r["id"])), _line(r)) for r in rows)
    digest = hashlib.sha256()
    for _, line in keyed:
        digest.update(line.encode() + b"\n")
    return Fingerprint(len(keyed), digest.hexdigest())


def corrections_fingerprint(session: Session) -> Fingerprint:
    """(count, sha256) over every confirmed correction of a live match, every column, in one
    snapshot. A tombstoned match's trail is left out: the purge before this check removes it."""
    live = sa.select(matches.c.id).where(matches.c.deleted_at.is_(None))
    query = sa.select(match_corrections).where(match_corrections.c.match_id.in_(live))
    rows = session.execute(query).mappings()
    return fingerprint_of(rows)
