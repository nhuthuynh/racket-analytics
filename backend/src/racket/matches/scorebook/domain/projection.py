"""The score sheet: a pure projection of the scorebook's inputs (match-aggregate §5).

``project(book)`` folds the rules engine over the kept rallies, game by game, under the
book's pinned ``rules_version`` (FR-049, NFR-075). There is no incremental path: a
correction's "replay k..n" (FR-053) is this same function, so it equals a fresh fold by
construction (C-01). Rallies after a finished game, or in a game after an unfinished one,
are kept and marked ``needs_decision`` (C-02, C-03; provisional, ADR 0009). Never raises on
stored data. The sheet holds only str, int, bool and None, so its canonical bytes are stable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from racket.sports.pickleball.rules import (
    PRESETS,
    DomainError,
    GameState,
    RulesConfig,
    Side,
    apply,
    new_game,
    score_call,
)

if TYPE_CHECKING:
    from racket.matches.scorebook.domain.book import Scorebook

UNOFFICIAL_LABEL = "unofficial scoring (rules not yet verified)"  # FR-055
NEEDS_DECISION = "needs_decision"


def rules_for(rules_version: str, format: str) -> RulesConfig | None:
    """The preset of this (version, format) pair, or ``None``: never a silent default (§8 Q3)."""
    config = PRESETS.get(rules_version)
    return config if config is not None and config.format.value == format else None


@dataclass
class PlayedGame:
    number: int
    first_serving_side: Side
    ends_switched: bool
    state: GameState | None
    blocked: bool = False

    @property
    def over(self) -> bool:
        return self.state is not None and self.state.is_over


@dataclass
class Played:
    games: list[PlayedGame] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    winner: Side | None = None

    @property
    def needs_decision(self) -> bool:
        return any(row["marker"] == NEEDS_DECISION for row in self.rows)


def _row(number: int, rally: Any, corrected: bool) -> dict[str, Any]:
    out = rally.outcome.as_json()
    return {
        "number": number, "rally_id": str(rally.id), "game": rally.game_number,
        "start_ms": rally.times.start_ms, "end_ms": rally.times.end_ms,
        "winning_side": out["winning_side"], "ending": out["ending"],
        "responsible_player": out["responsible_player"], "fault_kind": out["fault_kind"],
        "corrected_by_user": corrected, "serving_side": None, "server": None,
        "score_before": None, "score_after": None, "marker": NEEDS_DECISION,
    }  # fmt: skip


def corrected_rallies(book: Scorebook) -> set[Any]:
    """Rallies with a correction or resolution that is not undone (FR-052 marker)."""
    undone = {c.undoes for c in book.changes if c.kind == "undo"}
    return {c.rally_id for c in book.changes
            if c.kind in ("correction", "resolution") and c.id not in undone}  # fmt: skip


def play(book: Scorebook) -> Played:
    config = rules_for(book.rules_version, book.format)
    corrected = corrected_rallies(book)
    by_game: dict[int, list[Any]] = {}
    for rally in sorted(book.kept, key=lambda r: (r.times.start_ms, r.seq)):
        by_game.setdefault(rally.game_number, []).append(rally)
    played, number, blocked = Played(), 0, config is None
    for game in sorted(book.games, key=lambda g: g.number):
        state = None if config is None else new_game(config, game.first_serving_side)
        current = PlayedGame(game.number, game.first_serving_side, game.ends_switched,
                             None if blocked else state, blocked)  # fmt: skip
        for rally in by_game.get(game.number, []):
            number += 1
            row = _row(number, rally, rally.id in corrected)
            played.rows.append(row)
            if blocked or state is None or state.is_over or config is None:
                continue  # C-02 / C-03: kept, marked, never scored
            after = apply(state, rally.outcome.to_engine(), config)
            if isinstance(after, DomainError):
                continue  # defensive: stored data the engine refuses is marked, not raised
            row.update(serving_side=state.serving_side.value, server=state.server_player,
                       score_before=score_call(state), score_after=score_call(after),
                       marker=None)  # fmt: skip
            state = after
        current.state = None if blocked else state
        played.games.append(current)
        if not current.over:
            blocked = True  # a later game cannot be scored before this one ends (C-03)
    to_win = book.best_of // 2 + 1
    for side in Side:
        if sum(1 for g in played.games if g.over and g.state and g.state.winner is side) >= to_win:
            played.winner = side
    return played


def project(book: Scorebook) -> dict[str, Any]:
    played = play(book)
    games = [
        {
            "number": g.number,
            "first_serving_side": g.first_serving_side.value,
            "ends_switched": g.ends_switched,
            "rules_version": book.rules_version,
            "score_a": None if g.state is None else g.state.score_a,
            "score_b": None if g.state is None else g.state.score_b,
            "winner": g.state.winner.value if g.state and g.state.winner else None,
        }
        for g in played.games
    ]
    return {
        "rules_version": book.rules_version,
        "unofficial": True,  # every rule of the only preset is unverified (FR-055, ADR 0009)
        "label": UNOFFICIAL_LABEL,
        "format": book.format,
        "best_of": book.best_of,
        "games": games,
        "rows": played.rows,
        "winner": None if played.winner is None else played.winner.value,
    }


def canonical_bytes(sheet: dict[str, Any]) -> bytes:
    """Sorted keys, no spaces, UTF-8: the byte form the golden replay compares (NFR-075)."""
    return json.dumps(sheet, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
