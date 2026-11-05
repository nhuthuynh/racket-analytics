"""Migration round trip (ST-082; REL-1.3; ADR 0058 rule 7). Red-first stub: not built yet."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from racket.platform.db import MIGRATIONS_DIR
from tests.support.db import create_session_database, drop_session_database


def missing_downgrades(versions_dir: Path) -> list[str]:
    raise NotImplementedError("ST-082: missing_downgrades")


def revisions(script_location: Path = MIGRATIONS_DIR) -> list[tuple[str, str | None]]:
    raise NotImplementedError("ST-082: revisions")


def migrate(url: str, target: str, *, down: bool = False) -> None:
    raise NotImplementedError("ST-082: migrate")


@contextmanager
def scratch_database(base_url: str) -> Iterator[str]:
    url = create_session_database(base_url)
    try:
        yield url
    finally:
        drop_session_database(url, base_url)


def seed(url: str) -> None:
    raise NotImplementedError("ST-082: seed")


@dataclass(frozen=True)
class Step:
    revision: str
    back_at: str | None
    schema_equal: bool
    lost_rows: dict[str, tuple[int, int]]


def round_trip(url: str) -> list[Step]:
    raise NotImplementedError("ST-082: round_trip")
