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
    NothingToUndo,
    RallyNotFound,
    StaleMatch,
)
from racket.matches.scorebook.domain.projection import play
from racket.matches.scorebook.domain.values import OutcomeInput, RallyTimes
from racket.platform.errors import FieldError, ValidationFailed
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
        self,
        *,
        first_serving_side: Side,
        ends_switched: bool,
        ready: bool,
        expected_version: int,
        ctx: CommandContext,
    ) -> Scorebook:
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
            ctx,
            "game_started",
            game_number=game.number,
            field="first_serving_side",
            new_value=first_serving_side.value,  # scalar tag values only (§6, IT-02-09)
        )
        return replace(
            self,
            version=self.version + 1,
            games=(*self.games, game),
            changes=(*self.changes, change),
        )

    def tag(
        self,
        times: RallyTimes,
        outcome: OutcomeInput,
        *,
        ready: bool,
        expected_version: int,
        ctx: CommandContext,
    ) -> tuple[Scorebook, Rally]:
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
            id=ctx.new_id(),
            game_number=self.games[-1].number,
            seq=max((r.seq for r in self.rallies), default=0) + 1,
            times=times,
            outcome=outcome,
            created_version=self.version + 1,
        )
        book = replace(self, version=self.version + 1, rallies=(*self.rallies, rally))
        return book, rally

    # ------------------------------------------------------------ corrections (ST-031/032)
    def _rally(self, rally_id: uuid.UUID) -> Rally:
        found = next((r for r in self.rallies if r.id == rally_id), None)
        if found is None:
            raise RallyNotFound("no such rally in this match")
        return found

    def _with_rally(self, rally: Rally) -> tuple[Rally, ...]:
        return tuple(rally if r.id == rally.id else r for r in self.rallies)

    def correct(
        self,
        rally_id: uuid.UUID,
        field: str,
        value: Any,
        *,
        expected_version: int,
        ctx: CommandContext,
    ) -> Scorebook:
        """FR-052: change one field of one rally; the old and new value are audited. Later
        rallies are re-scored by the projection in the same step (FR-053, C-01)."""
        if expected_version != self.version:
            raise StaleMatch("version changed")
        if field not in CORRECTABLE:
            raise ValidationFailed(
                "field cannot be corrected", [FieldError("field", "field_invalid")]
            )
        rally = self._rally(rally_id)
        if field == "withdrawn":
            if value is not True or rally.withdrawn:
                raise ValidationFailed(
                    "only a kept rally can be withdrawn", [FieldError("value", "invalid")]
                )
            changed, kind, old = replace(rally, withdrawn=True), "withdrawal", False
        else:
            if rally.withdrawn:
                raise RallyNotFound("rally was withdrawn")
            changed, old = _changed(rally, field, value, self.format), _value(rally, field)
            kind = "correction"
            if field in ("start_ms", "end_ms"):
                changed.times.check_after(r.times for r in self.kept if r.id != rally.id)
        change = self._change(
            ctx,
            kind,
            rally_id=rally.id,
            game_number=rally.game_number,
            field=field,
            old_value=old,
            new_value=_value(changed, field),
        )
        return replace(
            self,
            version=self.version + 1,
            rallies=self._with_rally(changed),
            changes=(*self.changes, change),
        )

    def undo(self, *, expected_version: int, ctx: CommandContext) -> Scorebook:
        """Reverse the newest change not yet undone: a correction, withdrawal, resolution or
        game start, or the newest tag (which becomes a withdrawal). Audited (FR-052, C-04)."""
        if expected_version != self.version:
            raise StaleMatch("version changed")
        undone = {c.undoes for c in self.changes if c.kind == "undo"}
        open_changes = [c for c in self.changes if c.kind != "undo" and c.id not in undone]
        newest_change = max(open_changes, key=lambda c: c.version, default=None)
        newest_tag = max(self.kept, key=lambda r: r.created_version, default=None)
        if newest_tag is not None and (
            newest_change is None or newest_tag.created_version > newest_change.version
        ):
            change = self._change(
                ctx,
                "undo",
                rally_id=newest_tag.id,
                game_number=newest_tag.game_number,
                field="withdrawn",
                old_value=False,
                new_value=True,
            )
            rallies = self._with_rally(replace(newest_tag, withdrawn=True))
            return replace(
                self, version=self.version + 1, rallies=rallies, changes=(*self.changes, change)
            )
        target = newest_change
        if target is None:
            raise NothingToUndo("nothing to undo")
        book = replace(self, version=self.version + 1)
        if target.kind == "game_started":
            book = replace(
                book, games=tuple(g for g in self.games if g.number != target.game_number)
            )
        elif target.rally_id is not None and target.field is not None:
            rally = self._rally(target.rally_id)
            restored = (
                replace(rally, withdrawn=bool(target.old_value))
                if target.field == "withdrawn"
                else _changed(rally, target.field, target.old_value, self.format, validate=False)
            )
            book = replace(book, rallies=self._with_rally(restored))
        change = self._change(
            ctx,
            "undo",
            rally_id=target.rally_id,
            game_number=target.game_number,
            field=target.field,
            old_value=target.new_value,
            new_value=target.old_value,
            undoes=target.id,
        )
        return replace(book, changes=(*self.changes, change))

    def resolve(
        self,
        rally_id: uuid.UUID,
        decision: object,
        *,
        expected_version: int,
        ctx: CommandContext,
    ) -> Scorebook:
        """FR-053 (a), provisional (§8 Q1): a rally marked "needs your decision" is withdrawn
        or moved to the next game. Audited as a ``resolution``; undo reverses it."""
        if expected_version != self.version:
            raise StaleMatch("version changed")
        if decision not in DECISIONS:
            raise ValidationFailed("unknown decision", [FieldError("decision", "decision_invalid")])
        rally = self._rally(rally_id)
        marked = {row["rally_id"] for row in play(self).rows if row["marker"] is not None}
        if rally.withdrawn or str(rally.id) not in marked:
            raise ValidationFailed("no decision needed", [FieldError("decision", "not_needed")])
        old: int | bool
        if decision == "withdraw":
            field, old, changed = "withdrawn", False, replace(rally, withdrawn=True)
        else:
            target = rally.game_number + 1
            if target not in {g.number for g in self.games}:
                raise GameNotStarted("the next game is not started")
            field, old = "game_number", rally.game_number
            changed = replace(rally, game_number=target)
        change = self._change(
            ctx,
            "resolution",
            rally_id=rally.id,
            game_number=rally.game_number,
            field=field,
            old_value=old,
            new_value=_value(changed, field),
        )
        return replace(
            self,
            version=self.version + 1,
            rallies=self._with_rally(changed),
            changes=(*self.changes, change),
        )


DECISIONS = frozenset({"withdraw", "move_to_next_game"})
CORRECTABLE = frozenset(
    {
        "winning_side",
        "ending",
        "responsible_player",
        "fault_kind",
        "start_ms",
        "end_ms",
        "withdrawn",
    }
)


def _value(rally: Rally, field: str) -> Any:
    if field in ("start_ms", "end_ms"):
        return getattr(rally.times, field)
    if field in ("withdrawn", "game_number"):
        return getattr(rally, field)
    return rally.outcome.as_json()[field]


def _changed(rally: Rally, field: str, value: Any, format: str, *, validate: bool = True) -> Rally:
    if validate and value == _value(rally, field):
        raise ValidationFailed("value unchanged", [FieldError("value", "unchanged")])
    if field == "game_number":
        return replace(rally, game_number=int(value))
    if field in ("start_ms", "end_ms"):
        times = {"start_ms": rally.times.start_ms, "end_ms": rally.times.end_ms, field: value}
        return replace(rally, times=RallyTimes.parse(times["start_ms"], times["end_ms"]))
    body = rally.outcome.as_json() | {field: value}
    return replace(rally, outcome=OutcomeInput.parse(body, format=format))
