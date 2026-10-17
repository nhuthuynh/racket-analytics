"""Weakness ranking (ST-055; FR-120, FR-109; ADR 0003; coaching-plan.md §3).

Pure domain: standard library only. The values come from the COACH-4 catalogue
(docs/domain/weakness-catalogue.md): its cells (§2), points conceded (§3), ranking and
tie-break (§4) and primary metric (§5). The player's side is ``side`` ("A" or "B").

* ``attribute`` turns the counted rallies of one match into the side's ``RallyLoss`` values,
  one per rally the side lost, and checks conservation (FR-109) before returning them.
* ``rank`` groups losses by weakness and ranks them by rallies lost (the same games divide
  every weakness, so integer counts decide), ties in catalogue order.

The serve/receive split follows the side-out rule (DOM G1 R2), UNVERIFIED until P7: the unit
is provisional (OQ-08) and the ranking says so.
"""

from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Literal

UNIT = "rallies_lost_per_game"
NO_TAGGED_MATCH = "no_tagged_match"
UNATTRIBUTED = "unattributed"
SIDES = ("A", "B")
Phase = Literal["serve", "receive"]


class WeaknessConservationBroken(AssertionError):
    """FR-109 is violated: a lost rally is missing, counted twice or in the wrong phase."""


@dataclass(frozen=True, slots=True)
class CatalogueEntry:
    """A weakness of the catalogue (§2) and its target metrics (§5)."""

    id: str
    name: str
    order: int


CATALOGUE: tuple[CatalogueEntry, ...] = (
    CatalogueEntry("unforced_errors", "Unforced errors", 1),
    CatalogueEntry("serve_faults", "Serve faults", 2),
    CatalogueEntry("other_faults", "Other faults", 3),
    CatalogueEntry("errors_under_pressure", "Errors under pressure", 4),
    CatalogueEntry("opponent_winners", "Opponent winners against you", 5),
)
_BY_ID = {entry.id: entry for entry in CATALOGUE}


@dataclass(frozen=True, slots=True)
class RallyFact:
    """One counted rally of a match, as Coaching reads it (translated by the ACL)."""

    rally_id: str
    game: int
    serving_side: str
    winning_side: str
    ending: str
    fault_kind: str | None
    responsible_player: str | None
    point_to: str | None  # the side that scored, None when only the serve moved


@dataclass(frozen=True, slots=True)
class RallyLoss:
    """A rally the player's side lost, attributed exactly once (FR-109)."""

    match_id: uuid.UUID
    rally_id: str
    game_key: tuple[uuid.UUID, int]
    phase: Phase
    category: str  # a catalogue weakness id, or UNATTRIBUTED
    conceded_point: bool
    responsible_player: str | None


@dataclass(frozen=True, slots=True)
class Weakness:
    """A ranked weakness: rallies lost over the scope, split serve/receive (ADR 0003)."""

    id: str
    name: str
    rank: int
    metric_id: str
    plan_target: str
    catalogue_order: int
    lost: int
    lost_on_serve: int
    lost_on_receive: int
    conceded: int
    games: int

    @property
    def per_game(self) -> Fraction:
        return Fraction(self.lost, self.games)

    @property
    def on_serve_per_game(self) -> Fraction:
        return Fraction(self.lost_on_serve, self.games)

    @property
    def on_receive_per_game(self) -> Fraction:
        return Fraction(self.lost_on_receive, self.games)

    @property
    def conceded_per_game(self) -> Fraction:
        return Fraction(self.conceded, self.games)


@dataclass(frozen=True, slots=True)
class WeaknessRanking:
    """The player's weaknesses, best first; empty with a ``reason`` when nothing is in scope."""

    unit: str
    provisional: bool
    side_out_verified: bool
    games: int
    rallies: int
    weaknesses: tuple[Weakness, ...]
    skipped_matches: int
    lost_on_serve: int
    lost_on_receive: int
    unattributed: int
    reason: str | None


def category(fact: RallyFact) -> str:
    """Catalogue §2: the weakness of a rally the side lost (rule 0.2 makes the loser
    responsible for its own errors and faults; a winner is the other side's shot)."""
    if fact.ending == "unforced_error":
        return "unforced_errors"
    if fact.ending == "forced_error":
        return "errors_under_pressure"
    if fact.ending == "fault":
        return "serve_faults" if fact.fault_kind == "serve" else "other_faults"
    if fact.ending == "winner":
        return "opponent_winners"
    return UNATTRIBUTED


def attribute(match_id: uuid.UUID, side: str, facts: Iterable[RallyFact]) -> tuple[RallyLoss, ...]:
    """The rallies ``side`` lost in one match, each attributed once; conservation checked."""
    if side not in SIDES:
        raise ValueError(f"side must be one of {SIDES}, not {side!r}")
    facts = tuple(facts)
    losses = tuple(
        RallyLoss(
            match_id=match_id,
            rally_id=f.rally_id,
            game_key=(match_id, f.game),
            phase="serve" if f.serving_side == side else "receive",
            category=category(f),
            conceded_point=f.point_to is not None and f.point_to != side,
            responsible_player=f.responsible_player,
        )
        for f in facts
        if f.winning_side != side
    )
    check_conservation(match_id, side, facts, losses)
    return losses


def check_conservation(
    match_id: uuid.UUID, side: str, facts: Sequence[RallyFact], losses: Sequence[RallyLoss]
) -> None:
    """Per game and phase, the attributed losses are exactly the rallies ``side`` lost."""
    want: Counter[tuple[int, str, str]] = Counter(
        (f.game, "serve" if f.serving_side == side else "receive", f.rally_id)
        for f in facts
        if f.winning_side != side
    )
    got: Counter[tuple[int, str, str]] = Counter(
        (loss.game_key[1], loss.phase, loss.rally_id)
        for loss in losses
        if loss.match_id == match_id
    )
    if got == want and len(losses) == sum(want.values()):
        return
    problems = sorted(
        {f"game {game} {phase}" for game, phase, _ in (want - got) + (got - want)}
    ) or ["losses of another match"]
    raise WeaknessConservationBroken(
        f"match {match_id} side {side}: lost rallies not attributed once in " + ", ".join(problems)
    )


def _metric(weakness_id: str, serve: int, receive: int) -> tuple[str, str]:
    """Catalogue §5: (metric id, plan target); the half with more losses picks, ties serve."""
    serve_half = serve >= receive
    if weakness_id == "unforced_errors":
        return "AN-04", "AN-04"
    if weakness_id == "serve_faults" and serve_half:
        return "AN-05", "AN-05"
    if weakness_id in ("serve_faults", "other_faults"):
        return "AN-07", "AN-07:fault"
    if weakness_id == "errors_under_pressure":
        return "AN-07", "AN-07:forced-error"
    return ("AN-01", "AN-01") if serve_half else ("AN-02", "AN-02")


def rank(
    losses: Iterable[RallyLoss],
    games: int,
    *,
    rallies: int,
    skipped_matches: int = 0,
    side_out_verified: bool = False,
) -> WeaknessRanking:
    """Rank the weaknesses of ``losses`` over ``games`` games in scope (catalogue §4)."""
    losses = tuple(losses)
    if games < 0 or (games == 0 and losses):
        raise ValueError(f"{len(losses)} lost rallies need games in scope, got {games} games")
    tally: dict[str, Counter[str]] = {}
    for loss in losses:
        counts = tally.setdefault(loss.category, Counter())
        counts[loss.phase] += 1
        counts["conceded"] += loss.conceded_point
    entries = sorted(
        (_BY_ID[c] for c in tally if c in _BY_ID),
        key=lambda e: (-(tally[e.id]["serve"] + tally[e.id]["receive"]), e.order, e.id),
    )
    weaknesses = tuple(
        Weakness(
            id=e.id,
            name=e.name,
            rank=position,
            metric_id=_metric(e.id, tally[e.id]["serve"], tally[e.id]["receive"])[0],
            plan_target=_metric(e.id, tally[e.id]["serve"], tally[e.id]["receive"])[1],
            catalogue_order=e.order,
            lost=tally[e.id]["serve"] + tally[e.id]["receive"],
            lost_on_serve=tally[e.id]["serve"],
            lost_on_receive=tally[e.id]["receive"],
            conceded=tally[e.id]["conceded"],
            games=games,
        )
        for position, e in enumerate(entries, start=1)
    )
    unattributed = tally.get(UNATTRIBUTED, Counter())
    return WeaknessRanking(
        unit=UNIT,
        provisional=not side_out_verified,
        side_out_verified=side_out_verified,
        games=games,
        rallies=rallies,
        weaknesses=weaknesses,
        skipped_matches=skipped_matches,
        lost_on_serve=sum(1 for loss in losses if loss.phase == "serve"),
        lost_on_receive=sum(1 for loss in losses if loss.phase == "receive"),
        unattributed=unattributed["serve"] + unattributed["receive"],
        reason=NO_TAGGED_MATCH if games == 0 else None,
    )
