"""Integration-only fixtures (QA-VERIFY04R5-01; kickoff 05 BE-2).

``flags_on``: every R1 ``FEATURE_*`` flag on for apps built after it. ``flags_on_client``: an
httpx client of an app built that way on the rolled-back session (``db_session``), lifespan run.
The root conftest is an accepted test file, so these live beside the integration tests instead.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from tests.support import contract
from tests.support.api import async_client, lifespan
from tests.support.flags import set_flags


@pytest.fixture
def flags_on(monkeypatch: pytest.MonkeyPatch) -> tuple[str, ...]:
    """The four FEATURE_* variables set to ``true``; restored after the test."""
    return set_flags(monkeypatch, on=True)


@pytest.fixture
async def flags_on_client(
    flags_on: tuple[str, ...], db_session: Any
) -> AsyncIterator[httpx.AsyncClient]:
    """A client of a flag-on app (built after ``flags_on``) on the rolled-back session."""
    app = contract.APP_FACTORY.load()()
    app.dependency_overrides[contract.DB_SESSION_DEPENDENCY.load()] = lambda: db_session
    try:
        async with lifespan(app), async_client(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
