"""The ``TrainingPlan`` aggregate and rules-only assembly (ST-056; coaching-plan §5-§6). Pure."""

from racket.coaching.plan.domain.assembly import Infeasible, assemble, warm_up_minutes
from racket.coaching.plan.domain.model import (
    NO_DRILL_FITS,
    Drill,
    DrillAssignment,
    InvalidPreferences,
    PlanInvariantBroken,
    PlanWeakness,
    Preferences,
    Session,
    TrainingPlan,
    Unfitted,
    violations,
)

__all__ = [
    "NO_DRILL_FITS",
    "Drill",
    "DrillAssignment",
    "Infeasible",
    "InvalidPreferences",
    "PlanInvariantBroken",
    "PlanWeakness",
    "Preferences",
    "Session",
    "TrainingPlan",
    "Unfitted",
    "assemble",
    "violations",
    "warm_up_minutes",
]
