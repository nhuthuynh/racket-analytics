"""Shipped rules presets (ST-020; ADR 0009; scoring-engine.md §2.3).

The only file allowed to hold rule values (NFR-079, IT-01-12). Sprint 1 ships exactly one
preset, ``PROVISIONAL-UNVERIFIED``. Its values come from QD §2.2 and are UNVERIFIED
[DOM G1 R2, R6]: the scenarios that rest on them run ``@needs-verification`` until the coach
records ``@rule-<n>`` (OQ-01). A preset named after a federation ships only when every row is
verified (ADR 0009 rule 4, ST-020b).
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from racket.sports.pickleball.rules.config import MatchFormat, RulesConfig, ScoringSystem

PROVISIONAL_UNVERIFIED = "PROVISIONAL-UNVERIFIED"

PRESETS: Mapping[str, RulesConfig] = MappingProxyType(
    {
        PROVISIONAL_UNVERIFIED: RulesConfig(
            rules_version=PROVISIONAL_UNVERIFIED,
            scoring_system=ScoringSystem.SIDE_OUT,
            format=MatchFormat.DOUBLES,
            points_to_win=11,  # unverified (QD §2.2, DOM G1 R2)
            win_by=2,  # unverified (QD §2.2, DOM G1 R2)
            first_service_single_server=True,  # unverified (QD §2.2, DOM G1 R6)
        )
    }
)
