"""Binds tests/features/drill_rationale.feature (ST-057; FR-122; QD-PL-04).
Steps live in plan_citation_steps.py."""

from __future__ import annotations

from pytest_bdd import scenarios

from tests.features.plan_citation_steps import *  # noqa: F403  (shared step fixtures)

scenarios("drill_rationale.feature")
