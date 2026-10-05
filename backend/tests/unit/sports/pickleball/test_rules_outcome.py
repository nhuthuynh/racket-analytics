"""RallyOutcome and DomainError value objects (ST-020; scoring-engine.md §2.6-§2.7).

BE unit tests, negative first. Outcomes are built at the edge and raise ValueError on bad
input; domain errors are returned values, never raised (QD-RE-05).
"""

from __future__ import annotations

import pytest

from racket.sports.pickleball.rules import DomainError, FaultKind, GameOver, RallyOutcome, Side

pytestmark = [pytest.mark.unit, pytest.mark.scoring]

A, B = Side.A, Side.B


def test_domain_errors_are_values_not_exceptions() -> None:
    assert not issubclass(DomainError, BaseException)
    assert GameOver() == GameOver()


def test_outcome_constructors_validate_their_inputs() -> None:
    with pytest.raises(ValueError, match="side"):
        RallyOutcome.won_by("A")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="fault kind"):
        RallyOutcome.fault(by=A, kind="spin")  # type: ignore[arg-type]
    outcome = RallyOutcome.fault(by=A, kind=FaultKind.NVZ)
    assert (outcome.kind, outcome.rally_winner, outcome.fault_by) == ("fault", B, A)
    assert outcome.fault_kind is FaultKind.NVZ
    assert RallyOutcome.replay().rally_winner is None


def test_hand_built_outcomes_must_be_consistent() -> None:
    with pytest.raises(ValueError, match="kind"):
        RallyOutcome("lob")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="side"):
        RallyOutcome("replay", A)
    with pytest.raises(ValueError, match="fault kind"):
        RallyOutcome("won", A, FaultKind.NVZ)
