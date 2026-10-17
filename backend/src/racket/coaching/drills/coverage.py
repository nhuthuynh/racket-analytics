"""``racket-drill-coverage``: the drill coverage matrix check, a CLI and a CI step (ST-059;
FR-141; QD-DR-05; drill-review-checklist §3).

Usage::

    racket-drill-coverage content/drills

**Counted drills:** the latest version of each drill, ``coach-reviewed`` or ``verified``, with
no ``deprecated_by``. A warm-up counts in the library total but in no cell. A drill counts in
each cell of a plan target it hits (weakness-catalogue §5: AN-07 only through its
``share:fault`` / ``share:forced-error`` skill) times each level from ``level_min`` to
``level_max``.

**Each of the 18 cells** (6 targets x 3 levels) needs at least 2 drills, at least 1 with
``players`` <= 2 and at least 1 whose ``needs`` excludes ``ball_machine``. The library needs at
least 20 reviewed drills, of them at least 3 warm-ups. An AN-07 drill without a share skill is
named. The check prints the matrix, then one ``FAIL`` line per gap, e.g.
``FAIL AN-05 × beginner: players ≤ 2: 0``. Exit codes: 0 pass, 1 gaps or a file that is not a
schema-valid drill, 2 a path that is not a directory.

``check_coverage`` is pure (drills arrive as the plan's ``Drill`` values); ``main`` reads files.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from racket.coaching.drills.schema_check import drill_schema, errors
from racket.coaching.plan.domain.model import LEVELS, Drill

TARGETS = ("AN-01", "AN-02", "AN-04", "AN-05", "AN-07:fault", "AN-07:forced-error")
MIN_DRILLS = 2  # per cell
MAX_SMALL_GROUP = 2  # players
MIN_LIBRARY = 20  # FR-141
MIN_WARM_UPS = 3  # ST-058a; drill-review-checklist §3
BALL_MACHINE = "ball_machine"


@dataclass(frozen=True, slots=True)
class Cell:
    """One target x level cell: its counted drills and the two options it must offer."""

    target: str
    level: str
    drills: int
    small_group: int  # players <= 2
    no_ball_machine: int

    def gaps(self) -> list[str]:
        name = f"{self.target} × {self.level}"
        found = []
        if self.drills < MIN_DRILLS:
            found.append(f"{name}: drills: {self.drills}")
        if self.small_group < 1:
            found.append(f"{name}: players ≤ {MAX_SMALL_GROUP}: 0")
        if self.no_ball_machine < 1:
            found.append(f"{name}: no {BALL_MACHINE}: 0")
        return found


@dataclass(frozen=True, slots=True)
class CoverageReport:
    cells: tuple[Cell, ...]
    counted: int  # reviewed, latest, not deprecated (warm-ups included)
    warm_ups: int
    gaps: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.gaps


def _latest(drills: Iterable[Drill]) -> list[Drill]:
    latest: dict[str, Drill] = {}
    for drill in drills:
        if drill.id not in latest or drill.version > latest[drill.id].version:
            latest[drill.id] = drill
    return [latest[i] for i in sorted(latest)]


def check_coverage(drills: Iterable[Drill]) -> CoverageReport:
    """The coverage matrix of a library (every version of every drill)."""
    counted = [d for d in _latest(drills) if d.is_reviewed and not d.deprecated]
    in_cells = [d for d in counted if not d.is_warm_up]
    gaps = [
        f"{d.ref}: AN-07 without share skill"
        for d in in_cells
        if "AN-07" in d.target_metrics
        and not {"AN-07:fault", "AN-07:forced-error"} & d.plan_targets
    ]
    cells = []
    for target in TARGETS:
        for level in LEVELS:
            hit = [
                d
                for d in in_cells
                if target in d.plan_targets
                and LEVELS.index(d.level_min) <= LEVELS.index(level) <= LEVELS.index(d.level_max)
            ]
            cell = Cell(
                target,
                level,
                drills=len(hit),
                small_group=sum(d.players <= MAX_SMALL_GROUP for d in hit),
                no_ball_machine=sum(BALL_MACHINE not in d.needs for d in hit),
            )
            cells.append(cell)
            gaps += cell.gaps()
    warm_ups = len(counted) - len(in_cells)
    if len(counted) < MIN_LIBRARY:
        gaps.append(f"library: {len(counted)} < {MIN_LIBRARY} reviewed drills")
    if warm_ups < MIN_WARM_UPS:
        gaps.append(f"warm-ups: {warm_ups} < {MIN_WARM_UPS}")
    return CoverageReport(tuple(cells), len(counted), warm_ups, tuple(gaps))


def render(report: CoverageReport) -> list[str]:
    """The matrix: a header, then one row per cell in target x level order."""
    lines = [f"{'target':<20}{'level':<14}{'drills':>7}{'players≤2':>11}{'no_ball_machine':>17}"]
    for c in report.cells:
        lines.append(
            f"{c.target:<20}{c.level:<14}{c.drills:>7}{c.small_group:>11}{c.no_ball_machine:>17}"
        )
    return lines


def load_library(root: Path) -> tuple[list[Drill], list[str]]:
    """Every ``*.json`` drill file under ``root`` as a ``Drill``; unreadable or schema-invalid
    files are returned as problem lines instead (fail closed)."""
    drills: list[Drill] = []
    broken: list[str] = []
    for path in sorted(p for p in root.rglob("*.json") if p.name != "schema.json"):
        name = path.relative_to(root).as_posix()
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            broken.append(f"{name}: invalid drill: {exc}")
            continue
        if bad := list(errors(doc, drill_schema())):
            broken.append(f"{name}: invalid drill: {'; '.join(bad)}")
            continue
        drills.append(Drill.from_document(doc))
    return drills, broken


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="racket-drill-coverage",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("library", type=Path, help="a drill library directory")
    args = parser.parse_args(argv)
    root: Path = args.library
    if not root.is_dir():
        print(f"ERROR {root}: no such directory", file=sys.stderr)
        return 2
    drills, broken = load_library(root)
    report = check_coverage(drills)
    for line in render(report):
        print(line)
    print(f"library: {report.counted} reviewed drill(s), {report.warm_ups} warm-up(s)")
    problems = [*broken, *report.gaps]
    for problem in problems:
        print(f"FAIL {problem}")
    print(f"{root}: {'FAILED' if problems else 'ok'}, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
