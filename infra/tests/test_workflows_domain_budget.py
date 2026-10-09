"""NFR-073 domain unit budget on the CI runner (decision CI-DOMAIN-BUDGET in ST-048.md).

The domain suite (1,217 tests, default Hypothesis profile) took 8.9 s of test time plus
about 1 s of interpreter and plugin start-up on ubuntu-24.04, so the 10 s budget stopped it
with exit 124 although every test passed (runs 37914004993, 37919451474). The suite runs on
every runner core with pytest-xdist, as the integration job already does (C-32). The budget
itself, the paths and the default profile stay as they are; idle workers steal
queued tests so the Hypothesis-heavy modules do not end the run on one worker.
"""

from __future__ import annotations

import pytest
import yaml
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def domain_step() -> dict:
    steps = yaml.safe_load(CI.read_text())["jobs"]["python-unit"]["steps"]
    return next(s for s in steps if "DOMAIN_UNIT_BUDGET_S" in s.get("run", ""))


# ---------------------------------------------------------------- negative cases first
def test_the_domain_budget_is_not_raised_to_make_room() -> None:
    assert int(yaml.safe_load(CI.read_text())["env"]["DOMAIN_UNIT_BUDGET_S"]) <= 10


def test_the_domain_step_still_runs_every_domain_path_and_skips_only_red_until() -> None:
    run = domain_step()["run"]
    assert "$DOMAIN_TEST_PATHS" in run
    assert '-m "unit and not red_until"' in run
    assert "--deselect" not in run
    assert "-k " not in run


# ---------------------------------------------------------------- positive case
def test_the_domain_step_uses_one_xdist_worker_per_runner_core() -> None:
    run = domain_step()["run"]
    assert "run_with_budget.py" in run
    assert " -n auto " in run
    # Work stealing: the ~30 Hypothesis tests hold most of the time and sit in a few modules,
    # so the default batch hand-out left one worker running them alone (run 37921213218).
    assert " --dist worksteal " in run
