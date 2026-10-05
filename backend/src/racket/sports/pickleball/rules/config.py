"""Rules configuration value objects (ST-020; scoring-engine.md §2.1-§2.2; NFR-079).

Every rule value the engine uses is a ``RulesConfig`` field. This module holds validation
bounds only (``>= 1``); rule values live in ``presets.py``. Pure stdlib, no I/O (QD-TR-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import Literal, TypeVar

_MIN_VALUE = 1
_VERSION_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")


class Side(Enum):
    A = "A"
    B = "B"

    @property
    def other(self) -> Side:
        return Side.B if self is Side.A else Side.A


class ScoringSystem(StrEnum):
    SIDE_OUT = "side_out"
    RALLY = "rally"  # known, refused until verified (FR-043, OQ-01)


class MatchFormat(StrEnum):
    DOUBLES = "doubles"
    SINGLES = "singles"  # known, refused until ST-035


class FaultKind(StrEnum):
    """Glossary "Rally ending": analytics only, never changes the score (QD-RE-09, P7)."""

    SERVE = "serve"
    FOOT = "foot"
    TWO_BOUNCE = "two_bounce"
    NVZ = "nvz"
    OTHER = "other"


SUPPORTED_SCORING_SYSTEMS = frozenset({ScoringSystem.SIDE_OUT})
SUPPORTED_FORMATS = frozenset({MatchFormat.DOUBLES})

Reason = Literal["invalid", "unknown", "unsupported"]
_E = TypeVar("_E", bound=StrEnum)


class InvalidRulesConfig(ValueError):
    """A configuration value out of range. Raised at the edge (preset load, test setup)."""

    def __init__(self, field: str, reason: Reason, detail: str) -> None:
        super().__init__(f"{field} {detail}")
        self.field = field
        self.reason = reason


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _enum_value(enum: type[_E], supported: frozenset[_E], field: str, value: object) -> _E:
    if not isinstance(value, str) or value not in {m.value for m in enum}:
        allowed = ", ".join(sorted(m.value for m in supported))
        raise InvalidRulesConfig(field, "unknown", f"must be one of: {allowed}")
    member = enum(value)
    if member not in supported:
        raise InvalidRulesConfig(field, "unsupported", f"{member.value!r} is not supported yet")
    return member


@dataclass(frozen=True, slots=True, kw_only=True)
class RulesConfig:
    """The rules a game is scored under. Keyword-only and no defaults: a default would be a
    hidden rule value (NFR-079)."""

    rules_version: str
    scoring_system: ScoringSystem
    format: MatchFormat
    points_to_win: int
    win_by: int
    first_service_single_server: bool

    def __post_init__(self) -> None:
        version = self.rules_version
        if not isinstance(version, str) or not version or not set(version) <= _VERSION_CHARS:
            raise InvalidRulesConfig(
                "rules_version", "invalid", "must be letters, digits, '.', '_' or '-'"
            )
        system = _enum_value(
            ScoringSystem, SUPPORTED_SCORING_SYSTEMS, "scoring_system", self.scoring_system
        )
        fmt = _enum_value(MatchFormat, SUPPORTED_FORMATS, "format", self.format)
        object.__setattr__(self, "scoring_system", system)
        object.__setattr__(self, "format", fmt)
        for name in ("points_to_win", "win_by"):
            value = getattr(self, name)
            if not _is_int(value) or value < _MIN_VALUE:
                raise InvalidRulesConfig(name, "invalid", "must be an integer >= 1")
        if not isinstance(self.first_service_single_server, bool):
            raise InvalidRulesConfig("first_service_single_server", "invalid", "must be a bool")
