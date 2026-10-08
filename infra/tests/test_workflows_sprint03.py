"""Sprint 3 CI changes (sre-devops-engineer lane).

ST-054 (SRE half, NFR-073): the 10 s "rules + domain" unit budget also measures the new
``analytics`` domain code (sprint-03 §3.2; TCR row 2026-10-06, accepted 2026-10-07).
"""

from __future__ import annotations

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit  # CI selects -m "unit or integration" (PE-R1S3-07)

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def domain_paths() -> list[str]:
    return yaml.safe_load(CI.read_text())["env"]["DOMAIN_TEST_PATHS"].split()


# ---------------------------------------------------------------- negative cases first
def test_the_domain_budget_does_not_fall_back_to_the_whole_unit_suite() -> None:
    assert "tests/unit" not in domain_paths()
    assert "tests/unit/platform" not in domain_paths()  # infrastructure, 60 s budget


# ---------------------------------------------------------------- positive cases
def test_the_domain_budget_covers_the_analytics_domain() -> None:
    assert "tests/unit/analytics" in domain_paths()
    assert (REPO_ROOT / "backend" / "tests" / "unit" / "analytics").is_dir()
