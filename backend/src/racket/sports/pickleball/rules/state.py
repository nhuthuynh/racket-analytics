"""Game state and its constructors (ST-020; scoring-engine.md §2.4-§2.5; QD-RE-03, QD-RE-06).

``GameState`` construction checks only what needs no config and raises ``ValueError`` (a
programming error). In-play states come from ``new_game`` or ``declare_state``, which apply
the config-dependent rules and return ``IllegalState`` instead of raising.

Doubles positions (QD-RE-03; SOD-05/SOD-06, ``@needs-verification``): players are slots
``A1``, ``A2``, ``B1``, ``B2``. A new or declared state puts ``A1`` and ``B1`` in the
right-hand court; the serving side's right-court player serves at server 1 and the partner at
server 2. Seam: ``tests/support/contract.py`` (Sprint 1 block).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from racket.sports.pickleball.rules.config import MatchFormat, RulesConfig, Side
from racket.sports.pickleball.rules.errors import IllegalState

# The definition of doubles side-out mechanics in this model, not a tunable rule
# (scoring-engine.md §1; IT-01-12 allowlists these names).
FIRST_SERVER = 1
SECOND_SERVER = 2
SERVER_NUMBERS = frozenset({FIRST_SERVER, SECOND_SERVER})

_PLAYERS: Mapping[Side, tuple[str, str]] = MappingProxyType(
    {Side.A: ("A1", "A2"), Side.B: ("B1", "B2")}
)


def partner(player: str) -> str:
    """The other player of ``player``'s pair."""
    for pair in _PLAYERS.values():
        if player in pair:
            first, second = pair
            return second if player == first else first
    raise ValueError(f"unknown player slot: {player!r}")


def _is_count(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


@dataclass(frozen=True, slots=True, kw_only=True)
class GameState:
    """One game's score, server and positions. Equality is by value."""

    score_a: int
    score_b: int
    serving_side: Side
    server_number: int | None  # None in singles (ST-035)
    winner: Side | None
    server_player: str
    right_court_a: str
    right_court_b: str

    def __post_init__(self) -> None:
        if not (_is_count(self.score_a) and _is_count(self.score_b)):
            raise ValueError("scores must be non-negative integers")
        if not isinstance(self.serving_side, Side):
            raise ValueError("serving_side must be a Side")
        if self.server_number is not None and (
            isinstance(self.server_number, bool) or self.server_number not in SERVER_NUMBERS
        ):
            raise ValueError("server_number must be 1, 2 or None")
        if self.winner is not None:
            if not isinstance(self.winner, Side):
                raise ValueError("winner must be a Side or None")
            if self.score_of(self.winner) <= self.score_of(self.winner.other):
                raise ValueError("the winner must have the higher score")
        if self.server_player not in _PLAYERS[self.serving_side]:
            raise ValueError("the server must play for the serving side")
        if self.right_court_a not in _PLAYERS[Side.A] or self.right_court_b not in _PLAYERS[Side.B]:
            raise ValueError("each side's right-court player must play for that side")

    @property
    def is_over(self) -> bool:
        return self.winner is not None

    def score_of(self, side: Side) -> int:
        return self.score_a if side is Side.A else self.score_b

    @property
    def right_court_player(self) -> Mapping[Side, str]:
        """The player standing in the right-hand court of each side."""
        return MappingProxyType({Side.A: self.right_court_a, Side.B: self.right_court_b})


def meets_game_over(score_a: int, score_b: int, config: RulesConfig) -> bool:
    """P5: the configured target is reached with the configured margin."""
    return max(score_a, score_b) >= config.points_to_win and abs(score_a - score_b) >= config.win_by


def _start_positions(serving_side: Side, server_number: int) -> dict[str, str]:
    right = {side: _PLAYERS[side][0] for side in Side}
    server = right[serving_side]
    return {
        "server_player": server if server_number == FIRST_SERVER else partner(server),
        "right_court_a": right[Side.A],
        "right_court_b": right[Side.B],
    }


def new_game(config: RulesConfig, first_server: Side) -> GameState:
    """0-0 with ``first_server`` serving; at server 2 when the config's first-service flag is
    set. The first server is an input, never inferred (QD-RE-11)."""
    if not isinstance(first_server, Side):
        raise ValueError("first_server must be a Side")
    number = SECOND_SERVER if config.first_service_single_server else FIRST_SERVER
    return GameState(
        score_a=0,
        score_b=0,
        serving_side=first_server,
        server_number=number,
        winner=None,
        **_start_positions(first_server, number),
    )


def declare_state(
    config: RulesConfig,
    *,
    serving_side: Side,
    serving_score: int,
    receiving_score: int,
    server_number: int,
) -> GameState | IllegalState:
    """A declared in-play state (mid-game starts, QD-RE-06; golden tables)."""
    if not isinstance(serving_side, Side):
        return IllegalState("serving side must be A or B")
    if not (_is_count(serving_score) and _is_count(receiving_score)):
        return IllegalState("scores must be non-negative integers")
    if config.format is MatchFormat.DOUBLES and (
        isinstance(server_number, bool) or server_number not in SERVER_NUMBERS
    ):
        return IllegalState("server number must be 1 or 2")
    by_side = {serving_side: serving_score, serving_side.other: receiving_score}
    score_a, score_b = by_side[Side.A], by_side[Side.B]
    if meets_game_over(score_a, score_b, config):
        return IllegalState("score already meets the game-over condition")
    return GameState(
        score_a=score_a,
        score_b=score_b,
        serving_side=serving_side,
        server_number=server_number,
        winner=None,
        **_start_positions(serving_side, server_number),
    )
