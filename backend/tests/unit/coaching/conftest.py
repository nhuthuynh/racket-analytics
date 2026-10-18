"""Coaching unit tests record their marker names in the JUnit report (FIX-04-2c; G04-03 a, c):
``-m weakness_golden`` and ``-m plan_property`` runs are checked with
``junit_rate.py --require-marker``. A new file: the root conftest is a protected test file."""

from __future__ import annotations

import pytest

from tests.support.junit_markers import record_markers


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_teardown(item: pytest.Item) -> None:
    # Teardown runs for every test, skipped ones too, after every marker has been applied
    # (the root conftest adds `unit` at collection), and before the teardown report is made.
    record_markers(item)
