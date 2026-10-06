"""``MatchState``: the score projection of a match (ST-021; scoring-engine.md §5; FR-045 (a)).

Best of 1 or 3. Who serves first and whether ends were switched are explicit inputs per game,
never inferred (QD-RE-11; ST-021b holds any rulebook default). A rally or a new game after the
match is decided returns ``MatchOver``. A match keeps the ``rules_version`` it started with
(QD-RE-02). Pure: imports only the rules engine (Published Language R5) and the stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Self

from racket.sports.pickleball.rules import (
    DomainError,
    GameState,
    IllegalState,
    RallyOutcome,
    RulesConfig,
    Side,
    apply,
    new_game,
)

BEST_OF_OPTIONS = frozenset({1, 3})


@dataclass(frozen=True, slots=True)
class MatchOver(DomainError):
    message: str = "match is over"


@dataclass(frozen=True, slots=True)
class GameRecord:
    number: int
    first_server: Side
    ends_switched: bool
    state: GameState


@dataclass(frozen=True, slots=True, kw_only=True)
class MatchState:
    best_of: int
    config: RulesConfig
    games: tuple[GameRecord, ...] = ()

    @classmethod
    def start(cls, *, best_of: int, config: RulesConfig) -> Self:
        if isinstance(best_of, bool) or best_of not in BEST_OF_OPTIONS:
            raise ValueError("best_of must be 1 or 3")
        if not isinstance(config, RulesConfig):
            raise ValueError("config must be a RulesConfig")
        return cls(best_of=best_of, config=config)

    @property
    def rules_version(self) -> str:
        return self.config.rules_version

    @property
    def games_to_win(self) -> int:
        return self.best_of // 2 + 1

    def games_won(self, side: Side) -> int:
        return sum(1 for game in self.games if game.state.winner is side)

    @property
    def winner(self) -> Side | None:
        for side in Side:
            if self.games_won(side) >= self.games_to_win:
                return side
        return None

    @property
    def is_over(self) -> bool:
        return self.winner is not None

    def start_game(self, *, first_server: Side, ends_switched: bool) -> MatchState | DomainError:
        """Open the next game with its first server and ends stated by the player."""
        if self.is_over:
            return MatchOver()
        if not isinstance(first_server, Side) or not isinstance(ends_switched, bool):
            return IllegalState("first server and ends switched must be stated")
        if self.games and not self.games[-1].state.is_over:
            return IllegalState("current game not finished")
        game = GameRecord(
            number=len(self.games) + 1,
            first_server=first_server,
            ends_switched=ends_switched,
            state=new_game(self.config, first_server),
        )
        return replace(self, games=(*self.games, game))

    def record_rally(self, game_number: int, outcome: RallyOutcome) -> MatchState | DomainError:
        """Apply one rally to game ``game_number`` (1-based)."""
        if isinstance(game_number, bool) or not isinstance(game_number, int) or game_number < 1:
            return IllegalState("game number must be a positive integer")
        if self.is_over or game_number > self.best_of:
            return MatchOver()
        if game_number > len(self.games):
            return IllegalState("game not started")
        game = self.games[game_number - 1]
        result = apply(game.state, outcome, self.config)
        if isinstance(result, DomainError):
            return result
        games = list(self.games)
        games[game_number - 1] = replace(game, state=result)
        return replace(self, games=tuple(games))
