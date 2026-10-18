"""The SQL statements a block of requests sends, on every engine of the process (FIX-04-2b).

with statements() as sent:
    api.request("ivy", "GET", "/me/plan")
assert not reads_of(sent, "match_rallies")
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import sqlalchemy as sa

SCOREBOOK_TABLES = ("match_games", "match_rallies", "match_corrections")
_WRITE = re.compile(r"^\s*(INSERT|UPDATE|DELETE)\b", re.IGNORECASE)


@contextmanager
def statements() -> Iterator[list[str]]:
    sent: list[str] = []

    def record(conn: Any, cursor: Any, statement: str, *args: Any) -> None:
        sent.append(statement)

    sa.event.listen(sa.engine.Engine, "before_cursor_execute", record)
    try:
        yield sent
    finally:
        sa.event.remove(sa.engine.Engine, "before_cursor_execute", record)


def reads_of(sent: list[str], *tables: str) -> list[str]:
    """Statements that name any of ``tables`` after FROM or JOIN."""
    named = re.compile(r"\b(FROM|JOIN)\s+(" + "|".join(map(re.escape, tables)) + r")\b", re.I)
    return [s for s in sent if named.search(s)]


def writes(sent: list[str]) -> list[str]:
    return [s for s in sent if _WRITE.match(s)]
