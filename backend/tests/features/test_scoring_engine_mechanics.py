"""Binds tests/features/scoring_engine_mechanics.feature, sprint-01 §7.7 (ST-020).

Written before the engine (tests first). RED until ST-020 provides racket.sports.pickleball.rules
(seams in tests/support/contract.py, ADR 0012). Steps live in scoring_steps.py.
"""

from __future__ import annotations

import pytest
from pytest_bdd import scenarios

from tests.features.scoring_steps import *  # noqa: F403  (shared step fixtures)

pytestmark = [pytest.mark.red_until(story="ST-020"), pytest.mark.scoring]

scenarios("scoring_engine_mechanics.feature")
