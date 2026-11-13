"""Binds tests/features/review_tiers_sprint_06.feature (CI-TIERS-06; PRC-10.1, PRC-10.2).

The steps are the CI-TIERS-a steps of test_review_tiers_scenarios.py (a throwaway git repository,
then `scripts/ci/review_tiers.py --base main --head pr --json`); this module imports their
pytest-bdd fixtures instead of copying them."""

from __future__ import annotations

import pytest
import test_review_tiers_scenarios as ci_tiers_a
from pytest_bdd import scenarios

pytestmark = [pytest.mark.scenario, pytest.mark.integration]

globals().update(
    {
        name: value
        for name, value in vars(ci_tiers_a).items()
        if name.startswith("pytestbdd_stepdef_") or name == "ctx"
    }
)

scenarios("review_tiers_sprint_06.feature")
