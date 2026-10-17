"""The ``TrainingPlan`` aggregate, rules-only assembly (ST-056) and citations (ST-057);
coaching-plan §5-§6. Pure."""

from racket.coaching.plan.domain.assembly import Infeasible, assemble, warm_up_minutes
from racket.coaching.plan.domain.citation import (
    Citation,
    CitedAssignment,
    CitedPlan,
    EvidenceLink,
    LimitedData,
    MissingCitation,
    RallyRef,
    citable,
    deleted_sources,
    source_matches,
)
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
    "Citation",
    "CitedAssignment",
    "CitedPlan",
    "Drill",
    "DrillAssignment",
    "EvidenceLink",
    "Infeasible",
    "InvalidPreferences",
    "LimitedData",
    "MissingCitation",
    "PlanInvariantBroken",
    "PlanWeakness",
    "Preferences",
    "RallyRef",
    "Session",
    "TrainingPlan",
    "Unfitted",
    "assemble",
    "citable",
    "deleted_sources",
    "source_matches",
    "violations",
    "warm_up_minutes",
]
