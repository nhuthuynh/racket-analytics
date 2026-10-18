"""A test's pytest marker names in its JUnit report (FIX-04-2c; goal scorecard G04-03 a and c).

A JUnit report names a test by file, class and function, never by marker, so the scorecard's
``junit_rate.py`` could not tell that a ``-m weakness_golden`` run held the golden tests.
``record_markers`` adds the testcase property ``markers`` (sorted, comma-separated), which
``junit_rate.py --require-marker NAME`` reads.
"""

from __future__ import annotations

import pytest

PROPERTY = "markers"


def record_markers(item: pytest.Item) -> None:
    """Record ``item``'s marker names once; the teardown report carries them to the XML."""
    if any(name == PROPERTY for name, _ in item.user_properties):
        return
    names = sorted({mark.name for mark in item.iter_markers()})
    item.user_properties.append((PROPERTY, ",".join(names)))
