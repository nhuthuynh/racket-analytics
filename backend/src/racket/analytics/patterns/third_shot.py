"""AN-09 third-shot drop share (ST-171b; FR-171.R2, R3, R6; pattern-catalogue §0.1-§0.3, §2).

Counts one side's served rallies, read through the ACL (``full_tag.Rally``). Hit 1 is the serve
and names the serving side, hit 2 the return, hit 3 the third shot. Every served rally lands in
exactly one bucket: counted (by its third shot's trajectory) or excluded with a reason, checked
in this order: ``no_third_shot`` (fewer than 3 hits), ``side_order_invalid`` (hits 1-3 do not
alternate sides), ``facet_missing`` (hit 3 has no trajectory). A replay or a rally with no hit
belongs to neither side (match-level ``unassigned``). Pure: standard library only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

AN09 = "AN-09"
AN09_VERSION = "0.1"  # catalogue §0.8
AN09_MIN_N = 20  # catalogue §1 (A6)
DROP = "drop"

Buckets = Mapping[str, tuple[str, ...]]


class _Hit(Protocol):
    @property
    def side(self) -> str: ...
    @property
    def trajectory(self) -> str | None: ...


class _Rally(Protocol):
    @property
    def id(self) -> str: ...
    @property
    def replay(self) -> bool: ...
    @property
    def hits(self) -> Sequence[_Hit]: ...


@dataclass(frozen=True, slots=True)
class ThirdShotTally:
    """One side's AN-09 buckets, rally ids in label order."""

    mix: Buckets  # trajectory -> counted rallies
    excluded: Buckets  # reason -> excluded rallies
    unassigned: Buckets  # match level: replay, no_serve_hit

    @property
    def k(self) -> int:
        return len(self.mix.get(DROP, ()))

    @property
    def n(self) -> int:
        return sum(len(ids) for ids in self.mix.values())

    @property
    def n_excluded(self) -> int:
        return sum(len(ids) for ids in self.excluded.values())


def unassigned_reason(rally: _Rally) -> str | None:
    """Catalogue §0.2: a replay or a rally with no hit belongs to neither side."""
    if rally.replay:
        return "replay"
    return None if rally.hits else "no_serve_hit"


def _exclusion(hits: Sequence[_Hit]) -> str | None:
    if len(hits) < 3:
        return "no_third_shot"
    if hits[0].side == hits[1].side or hits[1].side == hits[2].side:
        return "side_order_invalid"
    return "facet_missing" if hits[2].trajectory is None else None


def third_shots(rallies: Sequence[_Rally], side: str) -> ThirdShotTally:
    mix: dict[str, list[str]] = {}
    excluded: dict[str, list[str]] = {}
    unassigned: dict[str, list[str]] = {}
    for rally in rallies:
        if (reason := unassigned_reason(rally)) is not None:
            unassigned.setdefault(reason, []).append(rally.id)
        elif rally.hits[0].side == side:
            if (reason := _exclusion(rally.hits)) is not None:
                excluded.setdefault(reason, []).append(rally.id)
            else:
                trajectory = str(rally.hits[2].trajectory)
                mix.setdefault(trajectory, []).append(rally.id)
    return ThirdShotTally(*({key: tuple(ids) for key, ids in buckets.items()}
                            for buckets in (mix, excluded, unassigned)))  # fmt: skip
