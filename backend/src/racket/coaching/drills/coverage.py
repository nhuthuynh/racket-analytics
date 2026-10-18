"""``racket-drill-coverage <dir>``: the drill coverage matrix check (ST-059; FR-141; QD-DR-05).

Implements drill-review-checklist §3. Counted drills: the latest version of each drill,
``coach-reviewed`` or ``verified``, no ``deprecated_by``; a warm-up counts in the library but in
no cell. A drill counts in each plan target it hits (AN-07 only through a share skill) x each
level in ``level_min..level_max``. Each of the 18 cells needs >= 2 drills, >= 1 for <= 2
players and >= 1 without ``ball_machine``; the library needs >= 20 drills, >= 3 of them
warm-ups. Prints the matrix, then ``FAIL <gap>`` per gap. Exit 0 pass, 1 gaps or a file that is
not a schema-valid drill (fail closed), 2 not a directory. ``check_coverage`` is pure.
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
SHARE_TARGETS = frozenset(TARGETS[4:])
MIN_DRILLS, SMALL_GROUP, MIN_LIBRARY, MIN_WARM_UPS = 2, 2, 20, 3
BALL_MACHINE = "ball_machine"
TIMES, AT_MOST = "\u00d7", "\u2264"  # the checklist's signs


@dataclass(frozen=True, slots=True)
class Cell:
    """One target x level cell: its counted drills and the two options it must offer."""

    target: str
    level: str
    drills: int
    small_group: int  # players <= SMALL_GROUP
    no_ball_machine: int

    def gaps(self) -> list[str]:
        name = f"{self.target} {TIMES} {self.level}"
        return [
            f"{name}: {need}: {n}"
            for need, n, short in (
                ("drills", self.drills, self.drills < MIN_DRILLS),
                (f"players {AT_MOST} {SMALL_GROUP}", self.small_group, self.small_group < 1),
                (f"no {BALL_MACHINE}", self.no_ball_machine, self.no_ball_machine < 1),
            )
            if short
        ]


@dataclass(frozen=True, slots=True)
class CoverageReport:
    cells: tuple[Cell, ...]
    counted: int  # warm-ups included
    warm_ups: int
    gaps: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.gaps


def check_coverage(drills: Iterable[Drill]) -> CoverageReport:
    """The coverage matrix of a library, given every version of every drill."""
    latest: dict[str, Drill] = {}
    for d in drills:
        if d.id not in latest or d.version > latest[d.id].version:
            latest[d.id] = d
    counted = [d for _, d in sorted(latest.items()) if d.is_reviewed and not d.deprecated]
    in_cells = [d for d in counted if not d.is_warm_up]
    gaps = [
        f"{d.ref}: AN-07 without share skill"
        for d in in_cells
        if "AN-07" in d.target_metrics and not SHARE_TARGETS & d.plan_targets
    ]
    cells = []
    for target in TARGETS:
        for i, level in enumerate(LEVELS):
            hit = [
                d
                for d in in_cells
                if target in d.plan_targets
                and LEVELS.index(d.level_min) <= i <= LEVELS.index(d.level_max)
            ]
            small = sum(d.players <= SMALL_GROUP for d in hit)
            cells.append(
                Cell(target, level, len(hit), small, sum(BALL_MACHINE not in d.needs for d in hit))
            )
            gaps += cells[-1].gaps()
    warm_ups = len(counted) - len(in_cells)
    if len(counted) < MIN_LIBRARY:
        gaps.append(f"library: {len(counted)} < {MIN_LIBRARY} reviewed drills")
    if warm_ups < MIN_WARM_UPS:
        gaps.append(f"warm-ups: {warm_ups} < {MIN_WARM_UPS}")
    return CoverageReport(tuple(cells), len(counted), warm_ups, tuple(gaps))


def render(report: CoverageReport) -> list[str]:
    """A header, then one row per cell in target x level order."""
    head = ("target", "level", "drills", f"players{AT_MOST}{SMALL_GROUP}", "no_ball_machine")
    rows: list[tuple[object, ...]] = [head]
    rows += [(c.target, c.level, c.drills, c.small_group, c.no_ball_machine) for c in report.cells]
    return [f"{t:<20}{lv:<14}{n:>7}{s:>11}{b:>17}" for t, lv, n, s, b in rows]


def load_library(root: Path) -> tuple[list[Drill], list[str]]:
    """Every drill file under ``root``; unreadable or schema-invalid files become problems."""
    drills: list[Drill] = []
    broken: list[str] = []
    for path in sorted(p for p in root.rglob("*.json") if p.name != "schema.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            bad = "; ".join(errors(doc, drill_schema()))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            bad = str(exc)
        if bad:
            broken.append(f"{path.relative_to(root).as_posix()}: invalid drill: {bad}")
        else:
            drills.append(Drill.from_document(doc))
    return drills, broken


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="racket-drill-coverage", description=__doc__)
    parser.add_argument("library", type=Path, help="a drill library directory")
    root: Path = parser.parse_args(argv).library
    if not root.is_dir():
        print(f"ERROR {root}: no such directory", file=sys.stderr)
        return 2
    drills, broken = load_library(root)
    report = check_coverage(drills)
    problems = [*broken, *report.gaps]
    print("\n".join(render(report)))
    print(f"library: {report.counted} reviewed drill(s), {report.warm_ups} warm-up(s)")
    print("".join(f"FAIL {p}\n" for p in problems), end="")
    print(f"{root}: {'FAILED' if problems else 'ok'}, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
