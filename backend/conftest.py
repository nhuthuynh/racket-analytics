"""Root conftest of the backend suite: records each test's markers in its JUnit report.

A JUnit report names tests, not markers, so the goal-scorecard method `junit_rate.py --require
weakness_golden` could not see the 9 golden tests that passed (VERIFY-04-r3, G04-03). The
`markers` property of each test case now carries its marker names (QA-VERIFY04R3-02-08).
It lives here, not in tests/conftest.py, so the accepted test tree is unchanged.
"""

from __future__ import annotations

import pytest


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        names = sorted({mark.name for mark in item.iter_markers()})
        item.user_properties.append(("markers", " ".join(names)))
