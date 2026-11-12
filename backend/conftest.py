"""Root conftest of the backend suite: records each test's markers in its JUnit report.

A JUnit report names tests, not markers, so the goal-scorecard method `junit_rate.py --require
weakness_golden` could not see the 9 golden tests that passed (VERIFY-04-r3, G04-03). The
`markers` property of each test case now carries its marker names (QA-VERIFY04R3-02-08).
It lives here, not in tests/conftest.py, so the accepted test tree is unchanged.

It also keeps the objects that start-up and collection create out of the cyclic garbage
collector (CI-DOMAIN-BUDGET, sprint 5; docs/sprints/05/decisions/CI-DOMAIN-BUDGET.md).
"""

from __future__ import annotations

import gc
from collections.abc import Generator

import pytest


@pytest.hookimpl(wrapper=True)
def pytest_collection(session: pytest.Session) -> Generator[None, object, object]:
    """Freeze start-up and collection objects out of the cyclic GC; the tests run unchanged.

    About 220,000 objects (modules, classes, functions, test items) exist once collection ends
    and live until the process exits. Every full collection re-scanned them: 0.8-1.0 s of each
    xdist worker's CPU in the domain step, five of the full collections at exit, where the
    controller waits for the slowest worker. Frozen objects are never scanned or collected;
    the collector stays on for everything a test creates, so pytest's unraisable-exception
    check at exit still sees those objects. No collection pass during collection; one pass
    when it ends (about 0.05 s), so the cyclic garbage collection leaves behind (about 22,000
    objects per domain worker) is collected and finalized, not frozen with the live objects.
    Same tests, same order, same Hypothesis examples.
    """
    gc.freeze()  # interpreter, plugins and conftests
    gc.disable()
    try:
        return (yield)
    finally:
        gc.enable()
        gc.collect()  # collection's own garbage, before it could be frozen
        gc.freeze()  # test modules, the code under test and the collected items


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        names = sorted({mark.name for mark in item.iter_markers()})
        item.user_properties.append(("markers", " ".join(names)))
