"""Rally outcomes (scoring-engine.md §2.6; glossary "Rally ending").

Built at the edge, so the constructors raise ``ValueError`` on bad input; ``apply`` itself
never raises (QD-RE-05).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from racket.sports.pickleball.rules.config import FaultKind, Side

OutcomeKind = Literal["won", "fault", "replay"]


@dataclass(frozen=True, slots=True)
class RallyOutcome:
    kind: OutcomeKind
    side: Side | None = None  # won: the rally winner; fault: the faulting side
    fault_kind: FaultKind | None = None

    def __post_init__(self) -> None:
        needs_side = self.kind in ("won", "fault")
        if self.kind not in ("won", "fault", "replay"):
            raise ValueError(f"unknown outcome kind: {self.kind!r}")
        if needs_side != isinstance(self.side, Side) or (not needs_side and self.side):
            raise ValueError(f"a {self.kind!r} outcome needs a side exactly when it names one")
        if (self.kind == "fault") != isinstance(self.fault_kind, FaultKind):
            raise ValueError("a fault needs a fault kind, and only a fault has one")

    @classmethod
    def won_by(cls, side: Side) -> RallyOutcome:
        """The rally was won outright by ``side``."""
        return cls("won", side)

    @classmethod
    def fault(cls, *, by: Side, kind: FaultKind) -> RallyOutcome:
        """``by`` committed a fault, i.e. lost the rally. The subtype never changes the score."""
        return cls("fault", by, kind)

    @classmethod
    def replay(cls) -> RallyOutcome:
        """The rally is replayed; nothing changes (QD-RE-08, P8)."""
        return cls("replay")

    @property
    def rally_winner(self) -> Side | None:
        if self.kind == "won":
            return self.side
        if self.kind == "fault" and self.side is not None:
            return self.side.other
        return None

    @property
    def fault_by(self) -> Side | None:
        return self.side if self.kind == "fault" else None
