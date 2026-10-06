"""Disk floor before evidence runs (QA-R2V-05, PE-R2-S1-04, QA-R3-03; working-agreement 1a,
ADR 0030 rule 3).

At under 10 GB free, SeaweedFS refuses writes ("No more free space left") and the live goal run
and the object-store parity tests fail for a reason that is not the code. Every evidence run
must refuse to start below the floor instead of producing a false red.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SCRIPTS_DIR

PRECHECK = SCRIPTS_DIR / "disk-precheck.sh"
LIVE_GOAL = SCRIPTS_DIR / "measure" / "live_goal.py"


def precheck(*args: str, **env: str) -> subprocess.CompletedProcess[str]:
    full = {k: v for k, v in os.environ.items() if not k.startswith("RA_")}
    full.update(env)
    return subprocess.run(
        ["bash", str(PRECHECK), *args], capture_output=True, text=True, env=full, timeout=30
    )


# ---------------------------------------------------------------- negative cases first
@pytest.mark.unit
def test_precheck_refuses_when_free_space_is_below_the_floor() -> None:
    res = precheck(RA_MIN_FREE_GB="1000000")
    assert res.returncode == 3, res
    assert "need >= 1000000 GB" in res.stderr
    assert "prune" in res.stderr


@pytest.mark.unit
@pytest.mark.parametrize("value", ["ten", "-1", "1.5"])
def test_precheck_refuses_a_malformed_floor(value: str) -> None:
    res = precheck(RA_MIN_FREE_GB=value)
    assert res.returncode == 2, res
    assert "RA_MIN_FREE_GB" in res.stderr


@pytest.mark.unit
def test_precheck_refuses_a_missing_path(tmp_path: Path) -> None:
    res = precheck(str(tmp_path / "nope"))
    assert res.returncode == 2, res


@pytest.mark.unit
def test_live_goal_refuses_to_start_below_the_disk_floor() -> None:
    # No stack is running: the refusal must come before any network call.
    res = subprocess.run(
        [sys.executable, str(LIVE_GOAL), "--min-free-gb", "1000000", "--file", str(LIVE_GOAL)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert res.returncode == 2, res
    assert "need >= 1000000 GB" in res.stderr, res.stderr


# ---------------------------------------------------------------- positive cases
@pytest.mark.unit
def test_precheck_passes_and_prints_the_df_line_at_or_above_the_floor() -> None:
    res = precheck(RA_MIN_FREE_GB="0")
    assert res.returncode == 0, res
    assert "Avail" in res.stdout  # the `df -h` header, so the evidence shows the measurement
    assert "disk-precheck: ok" in res.stdout


@pytest.mark.unit
def test_precheck_default_floor_is_10_gb() -> None:
    text = PRECHECK.read_text()
    assert "RA_MIN_FREE_GB:-10" in text


@pytest.mark.unit
def test_live_goal_default_floor_is_10_gb() -> None:
    res = subprocess.run(
        [sys.executable, str(LIVE_GOAL), "--help"], capture_output=True, text=True, timeout=30
    )
    assert res.returncode == 0
    assert "--min-free-gb" in res.stdout
    assert "default 10" in res.stdout


@pytest.mark.unit
def test_precheck_advice_never_removes_images_another_agent_may_use() -> None:
    # `docker image prune -a` removes every image without a running container, including other
    # rounds' stacks (ADR 0033 option 3 rejected; docs/ops/disk-and-prune.md step 3: dangling only).
    res = precheck(RA_MIN_FREE_GB="1000000")
    assert res.returncode == 3, res
    assert "image prune -af" not in res.stderr
    assert "image prune -a " not in res.stderr
    assert "docker image prune -f" in res.stderr
