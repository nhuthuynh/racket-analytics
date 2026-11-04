"""The R1 feature flags as one switch for tests (QA-VERIFY04R5-01; kickoff 05 BE-2; ADR 0051).

``FEATURE_FLAGS`` names the four ``FEATURE_*`` variables ``Settings.from_env`` reads. The
``flags_on`` fixture (backend/tests/integration/conftest.py) sets them all to ``true`` with
``monkeypatch``, so an app built after it runs as a flag-on stack (`make up` with the four flags
exported) and the variables are restored after the test.
"""

from __future__ import annotations

import pytest

FEATURE_FLAGS = (
    "FEATURE_AGE_GATE",
    "FEATURE_RETENTION_SETTING",
    "FEATURE_TRAINING_CONSENT",
    "FEATURE_QUOTAS",
)


def set_flags(monkeypatch: pytest.MonkeyPatch, *, on: bool) -> tuple[str, ...]:
    for name in FEATURE_FLAGS:
        monkeypatch.setenv(name, "true" if on else "false")
    return FEATURE_FLAGS
