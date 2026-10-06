"""Binds tests/features/side_out_doubles_provisional.feature, sprint-01 §7.8 (ST-023).

Written before the engine (tests first). RED until ST-020 provides racket.sports.pickleball.rules
(seams in tests/support/contract.py, ADR 0012). Steps live in scoring_steps.py.
"""

from __future__ import annotations

import pytest
from pytest_bdd import scenarios

from tests.features.scoring_steps import *  # noqa: F403  (shared step fixtures)

pytestmark = [pytest.mark.scoring]

scenarios("side_out_doubles_provisional.feature")
