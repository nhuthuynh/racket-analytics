"""G05-02 method guard (ST-075c review round 1, PE-075c-R1-01).

The fast-burn rule fires when the 1 h error ratio is over 7.2 % (14.4 x the 0.5 % budget). The
drill burst is 10 minutes at 10 rps with 10 % faulted: 600 errors in 6000 requests. If the
10-minute clean run (6000 good requests) shares the stack, both sit in the 1 h window and the
ratio is 600 / 12000 = 5 %, so ``ApiAvailabilityFastBurn`` cannot fire and ``inject_5xx`` exits 1.
ADR 0057 §2 and docs/ops/slo.md need no load in the previous hour, so each of the two documented
blocks (goal-scorecard §4 G05-02 and the slo.md "Drill" block) must tear the stack down and bring
a fresh one up (``up`` then ``make demo``) between the clean run and the drill.
"""

from __future__ import annotations

import pytest
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit

SCORECARD = REPO_ROOT / "docs" / "sprints" / "05" / "goal-scorecard.md"
SLO_DOC = REPO_ROOT / "docs" / "ops" / "slo.md"

FAST_BURN_RATIO = 14.4 * 0.005  # slo.yml ApiAvailabilityFastBurn threshold (7.2 %)
RPS, MINUTES, FAULT_PCT = 10, 10, 10  # inject_5xx defaults used by both blocks


def _block(path, heading: str) -> list[str]:
    section = path.read_text().split(heading, 1)[1]
    block = section.split("```", 1)[1].split("```", 1)[0]
    # join shell continuation lines so one command is one entry
    return block.replace("\\\n", " ").splitlines()


BLOCKS = {
    "goal-scorecard G05-02": lambda: _block(SCORECARD, "### G05-02"),
    "slo.md Drill": lambda: _block(SLO_DOC, "## Drill"),
}


def _index(lines: list[str], *needles: str) -> int:
    hits = [i for i, ln in enumerate(lines) if all(n in ln for n in needles)]
    assert len(hits) == 1, (needles, hits)
    return hits[0]


def test_a_shared_window_keeps_the_drill_under_the_fast_burn_threshold() -> None:
    """Why the order matters: the arithmetic of the finding."""
    burst = RPS * 60 * MINUTES
    errors = burst * FAULT_PCT // 100
    assert errors / burst > FAST_BURN_RATIO  # a fresh stack: 10 % > 7.2 %, fires
    assert errors / (burst + RPS * 60 * MINUTES) < FAST_BURN_RATIO  # after the clean run: 5 %


@pytest.mark.parametrize("name", sorted(BLOCKS))
def test_the_clean_run_and_the_drill_never_share_a_stack(name: str) -> None:
    lines = BLOCKS[name]()
    clean = _index(lines, "inject_5xx.py", "--rate 0", "--expect-no-alert")
    drill = _index(lines, "inject_5xx.py", "--expect-alert ApiAvailabilityFastBurn")
    first, second = sorted((clean, drill))
    between = lines[first + 1 : second]
    downs = [i for i, ln in enumerate(between) if "docker compose" in ln and " down -v" in ln]
    ups = [i for i, ln in enumerate(between) if "docker compose" in ln and " up -d" in ln]
    assert downs, f"{name}: no 'down -v' between the clean run and the drill"
    assert ups and min(downs) < max(ups), f"{name}: no fresh 'up -d' after the teardown"
    assert "make demo" in between[max(ups)], f"{name}: the fresh stack is not seeded by make demo"


@pytest.mark.parametrize("name", sorted(BLOCKS))
def test_the_block_ends_with_a_teardown(name: str) -> None:
    lines = [ln for ln in BLOCKS[name]() if ln.strip() and not ln.lstrip().startswith("#")]
    drill = _index(lines, "inject_5xx.py", "--expect-alert ApiAvailabilityFastBurn")
    tail = lines[drill + 1 :]
    assert any("docker compose" in ln and "down -v --rmi local" in ln for ln in tail), name
