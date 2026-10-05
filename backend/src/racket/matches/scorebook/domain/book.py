"""``Scorebook``: the scored side of the ``Match`` aggregate (match-aggregate §2, §4).

It stores **inputs only**: game starts and, per rally, the times and the outcome input the
player tagged, plus the append-only change trail. The score is never stored; ``project``
derives it (FR-049). Every command checks the client's version first, returns
a new value (nothing is mutated, so a refused command leaves no trace) and bumps ``version``.
Pure: the clock and the id factory come in through ``CommandContext`` (ddd-guidelines §4.5).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Self

from racket.matches.scorebook.domain.errors import (
    DecisionNeeded,
    GameIsOver,
    GameNotOver,
    GameNotStarted,
    MatchIsOver,
    MatchNotReady,
    StaleMatch,
)
from racket.matches.scorebook.domain.projection import play
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

    # ------------------------------------------------------------ guards
    def _guard(self, *, ready: bool, expected_version: int) -> None:
        if expected_version != self.version:
            raise StaleMatch("version changed")
        if not ready:
            raise MatchNotReady("video not received")

    def _change(self, ctx: CommandContext, kind: str, **fields: Any) -> Change:
        return Change(ctx.new_id(), kind, self.version + 1, ctx.actor_id, ctx.at, **fields)

    # ------------------------------------------------------------ commands
    def start_game(
        self, *, first_serving_side: Side, ends_switched: bool, ready: bool,
        expected_version: int, ctx: CommandContext,
    ) -> Scorebook:  # fmt: skip
        """FR-045: the first serving side and the ends are stated, never inferred."""
        self._guard(ready=ready, expected_version=expected_version)
        played = play(self)
        if played.winner is not None or len(self.games) >= self.best_of:
            raise MatchIsOver("match is decided")
        if self.games and not played.games[-1].over:
            raise GameNotOver("current game not finished")
        if not isinstance(first_serving_side, Side) or not isinstance(ends_switched, bool):
            raise ValueError("first serving side and ends must be stated")
        game = GameStart(len(self.games) + 1, first_serving_side, ends_switched, self.version + 1)
        change = self._change(
            ctx, "game_started", game_number=game.number,
            new_value={"first_serving_side": first_serving_side.value,
                       "ends_switched": ends_switched},
        )  # fmt: skip
        return replace(self, version=self.version + 1, games=(*self.games, game),
                       changes=(*self.changes, change))  # fmt: skip

    def tag(
        self, times: RallyTimes, outcome: OutcomeInput, *, ready: bool, expected_version: int,
        ctx: CommandContext,
    ) -> tuple[Scorebook, Rally]:  # fmt: skip
        """Append one rally to the current game (I1, I5, I6, I7). The tag is the original
        fact, so it has no audit row; undoing it is audited (match-aggregate §4)."""
        self._guard(ready=ready, expected_version=expected_version)
        played = play(self)
        if played.winner is not None:
            raise MatchIsOver("match is decided")
        if not self.games:
            raise GameNotStarted("no game started")
        if played.needs_decision:
            raise DecisionNeeded("rallies wait for the player's decision")
        if played.games[-1].over:
            raise GameIsOver("current game is over")
        times.check_after(r.times for r in self.kept)
        rally = Rally(
            id=ctx.new_id(), game_number=self.games[-1].number,
            seq=max((r.seq for r in self.rallies), default=0) + 1, times=times,
            outcome=outcome, created_version=self.version + 1,
        )  # fmt: skip
        book = replace(self, version=self.version + 1, rallies=(*self.rallies, rally))
        return book, rally
