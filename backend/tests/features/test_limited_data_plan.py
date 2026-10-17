"""Binds tests/features/limited_data_plan.feature (ST-057; FR-123; QD-PL-06).
Steps live in plan_citation_steps.py."""

from __future__ import annotations

from pytest_bdd import scenarios

from tests.features.plan_citation_steps import *  # noqa: F403  (shared step fixtures)

scenarios("limited_data_plan.feature")
