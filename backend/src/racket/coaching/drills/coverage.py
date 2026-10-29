"""``racket-drill-coverage <dir>``: the drill coverage matrix check (ST-059; FR-141; QD-DR-05).

Implements drill-review-checklist §3. Counted drills: the latest version of each drill,
``coach-reviewed`` or ``verified``, no ``deprecated_by``; a warm-up counts in the library but in
no cell. A drill counts in each plan target it hits (AN-07 only through a share skill) x each
level in ``level_min..level_max``. Each of the 18 cells needs >= 2 drills, >= 1 for <= 2
players and >= 1 without ``ball_machine``; the library needs >= 20 drills, >= 3 of them
warm-ups. Prints the matrix, then ``FAIL <gap>`` per gap. Exit 0 pass, 1 gaps or a file that is
not a schema-valid drill (fail closed), 2 not a directory. ``check_coverage`` is pure.

Profile axis (QA-VERIFY04R3-01; FR-124; checklist §3.1): for each players x equipment profile
the plan must serve on its own (``PROFILES``: ``solo+wall``, the G04-01 step 3 preferences), each
target x profile level needs >= 2 counted drills that ``Drill.fits`` the profile's preferences
and fit its session's drill cap, so "Not for me" has a second drill to offer. Gaps read
``AN-04 x intermediate x solo+wall: drills: 1``, with the checklist's sign for x.
``check_profiles`` is pure. ``check_profile_pairs`` (PE-R1-1) adds: a plan training targets t
and u can hold one shared drill for u beside t's drill, so t needs >= 2 drills apart from it;
gaps read ``AN-01 with AN-05 x intermediate x solo+wall: drills: 1``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from racket.coaching.drills.schema_check import drill_schema, errors
from racket.coaching.plan.domain.model import LEVELS, Drill, Preferences

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


def _counted(drills: Iterable[Drill]) -> list[Drill]:
    """The latest version of each drill, when reviewed and not deprecated, in id order."""
    latest: dict[str, Drill] = {}
    for d in drills:
        if d.id not in latest or d.version > latest[d.id].version:
            latest[d.id] = d
    return [d for _, d in sorted(latest.items()) if d.is_reviewed and not d.deprecated]


def check_coverage(drills: Iterable[Drill]) -> CoverageReport:
    """The coverage matrix of a library, given every version of every drill."""
    counted = _counted(drills)
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


@dataclass(frozen=True, slots=True)
class Profile:
    """A players x equipment setup the plan must serve alone, at the levels it is measured at."""

    name: str
    players: int
    equipment: frozenset[str]
    levels: tuple[str, ...]
    minutes_per_session: int = 30
    sessions_per_week: int = 3

    def preferences(self, level: str) -> Preferences:
        return Preferences(
            minutes_per_session=self.minutes_per_session,
            sessions_per_week=self.sessions_per_week,
            players_available=self.players,
            equipment=self.equipment,
            level=level,
        )


SOLO_WALL = Profile("solo+wall", 1, frozenset({"wall"}), ("intermediate",))
PROFILES = (SOLO_WALL,)


@dataclass(frozen=True, slots=True)
class ProfileCell:
    """One target x level x profile cell: the counted drills a swap there can choose from."""

    target: str
    level: str
    profile: str
    drills: int

    def gaps(self) -> list[str]:
        if self.drills >= MIN_DRILLS:
            return []
        return [f"{self.target} {TIMES} {self.level} {TIMES} {self.profile}: drills: {self.drills}"]


@dataclass(frozen=True, slots=True)
class ProfileReport:
    cells: tuple[ProfileCell, ...]
    gaps: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.gaps


def check_profiles(
    drills: Iterable[Drill], profiles: Iterable[Profile] = PROFILES
) -> ProfileReport:
    """Per profile, target and level: the counted non-warm-up drills that fit the profile's
    preferences (QD-PL-02) and whose ``duration_min`` fits its drill cap (QD-PL-03)."""
    in_cells = [d for d in _counted(drills) if not d.is_warm_up]
    cells = []
    for profile in profiles:
        for level in profile.levels:
            prefs = profile.preferences(level)
            fit = [d for d in in_cells if d.fits(prefs) and d.duration_min <= prefs.drill_cap]
            for target in TARGETS:
                n = sum(target in d.plan_targets for d in fit)
                cells.append(ProfileCell(target, level, profile.name, n))
    return ProfileReport(tuple(cells), tuple(g for c in cells for g in c.gaps()))


def check_profile_pairs(
    drills: Iterable[Drill], profiles: Iterable[Profile] = PROFILES
) -> tuple[str, ...]:
    """Per profile, level and ordered pair (t, u): the drills of t left to swap among when the
    session's drill for u is one of them. Targets short on their own are not repeated here."""
    in_cells = [d for d in _counted(drills) if not d.is_warm_up]
    gaps = []
    for profile in profiles:
        for level in profile.levels:
            prefs = profile.preferences(level)
            fit = [d for d in in_cells if d.fits(prefs) and d.duration_min <= prefs.drill_cap]
            by = {t: {d.ref for d in fit if t in d.plan_targets} for t in TARGETS}
            for t in (t for t in TARGETS if len(by[t]) >= MIN_DRILLS):
                for u in (u for u in TARGETS if u != t and by[t] & by[u]):
                    if (n := len(by[t]) - 1) < MIN_DRILLS:
                        cell = f"{t} with {u} {TIMES} {level} {TIMES} {profile.name}"
                        gaps.append(f"{cell}: drills: {n}")
    return tuple(gaps)


def render(report: CoverageReport) -> list[str]:
    """A header, then one row per cell in target x level order."""
    head = ("target", "level", "drills", f"players{AT_MOST}{SMALL_GROUP}", "no_ball_machine")
    rows: list[tuple[object, ...]] = [head]
    rows += [(c.target, c.level, c.drills, c.small_group, c.no_ball_machine) for c in report.cells]
    return [f"{t:<20}{lv:<14}{n:>7}{s:>11}{b:>17}" for t, lv, n, s, b in rows]


def render_profiles(report: ProfileReport) -> list[str]:
    """A header, then one row per profile cell in profile x level x target order."""
    rows: list[tuple[object, ...]] = [("target", "level", "profile", "drills")]
    rows += [(c.target, c.level, c.profile, c.drills) for c in report.cells]
    return [f"{t:<20}{lv:<14}{p:<11}{n:>7}" for t, lv, p, n in rows]


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
    profiles = check_profiles(drills)
    problems = [*broken, *report.gaps, *profiles.gaps, *check_profile_pairs(drills)]
    print("\n".join(render(report)))
    print("\n".join(render_profiles(profiles)))
    print(f"library: {report.counted} reviewed drill(s), {report.warm_ups} warm-up(s)")
    print("".join(f"FAIL {p}\n" for p in problems), end="")
    print(f"{root}: {'FAILED' if problems else 'ok'}, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
