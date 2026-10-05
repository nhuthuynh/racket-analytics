"""``Scorebook``: the scored side of the ``Match`` aggregate (match-aggregate §2, §4).

It stores **inputs only**: game starts and, per rally, the times and the outcome input the
player tagged, plus the append-only change trail. The score is never stored; ``project``
derives it (FR-049). Commands (ST-027, ST-031, ST-032) return a new value and bump
``version`` by one.
Pure: the clock and the id factory come in through ``CommandContext`` (ddd-guidelines §4.5).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

from racket.matches.scorebook.domain.values import OutcomeInput, RallyTimes
from racket.sports.pickleball.rules import Side

BEST_OF = frozenset({1, 3})


@dataclass(frozen=True, slots=True)
class CommandContext:
    actor_id: uuid.UUID
    at: datetime
    new_id: Callable[[], uuid.UUID] = uuid.uuid4


@dataclass(frozen=True, slots=True)
class GameStart:
    number: int
    first_serving_side: Side
    ends_switched: bool
    created_version: int


@dataclass(frozen=True, slots=True)
class Rally:
    id: uuid.UUID
    game_number: int
    seq: int
    times: RallyTimes
    outcome: OutcomeInput
    created_version: int
    withdrawn: bool = False


@dataclass(frozen=True, slots=True)
class Change:
    """One audit row (I8): who changed what, when; never updated or deleted (FR-052)."""

    id: uuid.UUID
    kind: str  # game_started | correction | withdrawal | undo | resolution
    version: int
    actor_id: uuid.UUID
    at: datetime
    rally_id: uuid.UUID | None = None
    game_number: int | None = None
    field: str | None = None
    old_value: Any = None
    new_value: Any = None
    undoes: uuid.UUID | None = None


@dataclass(frozen=True, slots=True)
class Scorebook:
    rules_version: str
    format: str
    best_of: int
    version: int = 0
    games: tuple[GameStart, ...] = ()
    rallies: tuple[Rally, ...] = ()
    changes: tuple[Change, ...] = ()

    @classmethod
    def new(cls, *, rules_version: str, format: str, best_of: int = 3) -> Self:
        if isinstance(best_of, bool) or best_of not in BEST_OF:
            raise ValueError("best_of must be 1 or 3")
        return cls(rules_version=rules_version, format=format, best_of=best_of)

    @property
    def kept(self) -> tuple[Rally, ...]:
        """The rallies on the sheet: a withdrawn rally stays stored but is not shown."""
        return tuple(r for r in self.rallies if not r.withdrawn)
