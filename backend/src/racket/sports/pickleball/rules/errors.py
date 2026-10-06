"""Domain errors of the rules engine (scoring-engine.md §2.7; QD-RE-05).

Values, not exceptions: ``apply`` and ``fold`` return them and never raise. The ``message`` is
for tests and logs; the API maps the type to a fixed response (Sprint 2).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DomainError:
    message: str


@dataclass(frozen=True, slots=True)
class GameOver(DomainError):
    message: str = "game already over"


@dataclass(frozen=True, slots=True)
class IllegalState(DomainError):
    message: str = "illegal game state"


@dataclass(frozen=True, slots=True)
class UnknownOutcome(DomainError):
    message: str = "unknown rally outcome"
