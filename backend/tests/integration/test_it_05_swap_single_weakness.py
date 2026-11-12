"""IT-05-09 (ST-081a; FR-124.R1-R2, FR-141.R1; drill-review-checklist §3.1.1; COACH-S5-01): "Not
for me" on a single-weakness plan, over the real ``content/drills`` files.

Boundaries: CLI <-> files (``racket-drill-coverage --session-size`` prints one swap-counted row per
solo+wall cell and fails naming a cell below S + 1) and files -> plan domain
(``Drill.from_document``, ``assemble``, ``TrainingPlan.swap``) with the G04-01 step 3 preferences.

Negative first (QA-R2-1): an AN-02 drill of ``duration_min`` 12 whose id sorts last fits the cap
but not the smallest slot, so it does not lift AN-02 to 3. Then, per target, with N swap-counted
drills read from the library (so the ITs stay true when ST-081b adds drills):
(1) the first "Not for me" on each weakness drill of each session of a single-weakness plan swaps
to a different fitting drill citing the target and not already in the session (FR-124.R2), a
fresh plan per press; the cell must pass (N >= S + 1), so the four cells short on ``main``
carry ``red_until`` ST-081b (ADR 0046); (2) on one plan, presses on a full session succeed
N - S times and the next answers ``NoAlternative`` with version, ``content_digest`` and
``excluded_drills`` unchanged (with N = 3: the second press). The library passing the rule is
itself a ``red_until`` ST-081b row: it is red on ``main`` (AN-02, AN-04, AN-07:fault,
AN-07:forced-error have 2) and its stale-marker check fails once ST-081b closes the cells.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from racket.coaching.drills.coverage import SOLO_WALL, check_profiles, check_session_size
from racket.coaching.plan.domain import (
    Drill,
    DrillSwapped,
    NoAlternative,
    PlanWeakness,
    TrainingPlan,
    assemble,
)
from tests.integration.test_it_04_13_drill_coverage_cli import LIBRARY, fails, run

pytestmark = pytest.mark.integration

TARGETS = ("AN-01", "AN-02", "AN-04", "AN-05", "AN-07:fault", "AN-07:forced-error")
SHORT_ON_MAIN = ("AN-02", "AN-04", "AN-07:fault", "AN-07:forced-error")  # checklist §3.1.1
G04_01 = SOLO_WALL.preferences("intermediate")
S = 2  # solo+wall at 30 min: floor((30 - 5) / 10)
LONG_AN02 = "pb.return.z-long"


def _documents(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    files = sorted(p for p in root.rglob("*.json") if p.name != "schema.json")
    return [(p, json.loads(p.read_text(encoding="utf-8"))) for p in files]


def _library(root: Path = LIBRARY) -> list[Drill]:
    return [Drill.from_document(doc) for _, doc in _documents(root)]


def _cell(drills: list[Drill], target: str) -> int:
    """N: the swap-counted drills of ``target`` in solo+wall x intermediate."""
    (n,) = [c.drills for c in check_session_size(drills).cells if c.target == target]
    return n


def _cap_counted(drills: list[Drill], target: str) -> int:
    (n,) = [c.drills for c in check_profiles(drills).cells if c.target == target]
    return n


def _single(target: str, library: list[Drill]) -> TrainingPlan:
    plan = assemble([PlanWeakness("w-1", target, 1)], G04_01, library)
    assert isinstance(plan, TrainingPlan), plan
    assert plan.unfitted == (), plan.unfitted
    return plan


def _swap(plan: TrainingPlan, n: int, position: int, library: list[Drill]) -> DrillSwapped:
    s = plan.sessions[n]
    return plan.swap(
        week=s.week, index=s.index, position=position, library=library, cited=set(TARGETS)
    )


def _per_target() -> list[Any]:
    red = pytest.mark.red_until(story="ST-081b")
    return [pytest.param(t, marks=red) if t in SHORT_ON_MAIN else t for t in TARGETS]


# ---------------------------------------------------------------- negative case first (QA-R2-1)
def test_it_05_09_a_long_third_an02_drill_keeps_the_cell_short(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    copy = tmp_path / "drills"
    shutil.copytree(LIBRARY, copy)
    an02 = [
        (p, d)
        for p, d in _documents(copy)
        if "AN-02" in Drill.from_document(d).plan_targets
        and d["duration_min"] <= 10
        and Drill.from_document(d).fits(G04_01)
        and not Drill.from_document(d).is_warm_up
    ]
    for path, _ in an02[S:]:  # leave exactly S swap-counted AN-02 drills
        path.unlink()
    source = json.loads((LIBRARY / "pb.return.wall-return" / "v1.json").read_text("utf-8"))
    (copy / LONG_AN02).mkdir()
    long = source | {"id": LONG_AN02, "duration_min": 12, "duration_max": 15}
    (copy / LONG_AN02 / "v1.json").write_text(json.dumps(long), encoding="utf-8")
    assert _cap_counted(_library(copy), "AN-02") == S + 1  # the cap filter alone would pass it
    rc, out = run(capsys, "--session-size", copy)
    assert rc == 1, out
    assert "FAIL AN-02 × intermediate × solo+wall: drills: 2 < 3 (single-weakness swap)" in fails(
        out
    ), out
    rc, out = run(capsys, copy)  # without the flag the check is unchanged (IT-04-13, IT-04-18)
    assert "single-weakness swap" not in out, out


# ---------------------------------------------------------------- the library (red until ST-081b)
@pytest.mark.red_until(story="ST-081b")
def test_it_05_09_the_library_has_s_plus_one_swap_counted_drills_per_solo_wall_cell(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc, out = run(capsys, "--session-size", LIBRARY)
    assert fails(out) == [], out
    assert rc == 0, out


# ---------------------------------------------------------------- (1) the first press swaps
@pytest.mark.parametrize("target", _per_target())
def test_it_05_09_the_first_press_on_each_drill_of_a_single_weakness_plan_swaps(
    target: str,
) -> None:
    library = _library()
    assert _cell(library, target) >= S + 1, f"{target} is short (COACH-S5-01)"
    presses = 0
    for n in range(len(_single(target, library).sessions)):
        session = _single(target, library).sessions[n]
        for x in (x for x in session.assignments if x.weakness_id is not None):
            plan = _single(target, library)  # a swapped-out drill is never offered again
            swapped = _swap(plan, n, x.position, library)
            others = {y.drill.ref for y in session.assignments if y is not x}
            assert (swapped.from_drill, swapped.target) == (x.drill.ref, target)
            assert swapped.to_drill != x.drill.ref
            assert swapped.to_drill not in others  # FR-124.R2: never one already in the session
            new = plan.sessions[n].assignments[x.position - 1]
            assert new.drill.fits(G04_01)
            assert target in new.drill.plan_targets
            assert plan.sessions[n].total_minutes <= G04_01.minutes_budget
            presses += 1
    assert presses >= len(_single(target, library).sessions)  # never a vacuous pass


# ---------------------------------------------------------------- (2) presses add up per plan
@pytest.mark.parametrize("target", TARGETS)
def test_it_05_09_presses_on_one_plan_succeed_n_minus_s_times_then_answer_409(
    target: str,
) -> None:
    library = _library()
    n_swap, n_cap = _cell(library, target), _cap_counted(library, target)
    plan = _single(target, library)
    full = [
        n
        for n, s in enumerate(plan.sessions)
        if sum(x.weakness_id is not None for x in s.assignments) == S
    ]
    assert full, "no session holds S drills of the target"
    n = full[0]
    swaps = 0
    while True:
        version, digest, excluded = plan.version, plan.content_digest(), plan.excluded_drills
        try:
            _swap(plan, n, 2, library)
        except NoAlternative:
            break
        swaps += 1
        assert swaps <= n_cap, "a turned-down drill was offered again"
    assert (plan.version, plan.content_digest(), plan.excluded_drills) == (
        version,
        digest,
        excluded,
    )
    assert max(0, n_swap - S) <= swaps <= max(0, n_cap - S), (n_swap, n_cap, swaps)
    if n_swap == n_cap == S + 1:
        assert swaps == 1  # COACH-5 §3: the second press answers 409
