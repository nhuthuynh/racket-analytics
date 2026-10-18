"""Citations and the limited-data plan (ST-057; FR-122, FR-123; QD-PL-04, QD-PL-06).

Pure domain (coaching-plan §5): a ``Citation`` is the evidence behind a drill assignment, the
player's own metric, value, n and up to 10 rallies, with one "see all n" evidence link per match
(FR-103). ``CitedPlan`` is the assembled ``TrainingPlan`` with a citation on every assignment; an
assignment without one cannot be created (``MissingCitation``, QD-PL-04).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, NamedTuple, TypeVar

from racket.coaching.plan.domain.model import (
    Drill,
    DrillAssignment,
    PlanInvariantBroken,
    TrainingPlan,
)

_Id = TypeVar("_Id", str, uuid.UUID)
EVIDENCE_MAX = 10  # FR-103 "up to 10"
_NOUNS = {"AN-01": "serves", "AN-02": "serves received", "AN-05": "serves", "AN-07": "rallies"}
_SHARES = {"AN-07:fault": "faults", "AN-07:forced-error": "forced errors"}


class MissingCitation(PlanInvariantBroken):
    """QD-PL-04: an assignment would have no citation, or the citation is not one."""


class RallyRef(NamedTuple):
    match_id: str
    rally_id: str


class EvidenceLink(NamedTuple):
    """The "see all n" target: ``GET /matches/{match_id}/stats/{metric_id}/evidence?side=``."""

    match_id: str
    side: str
    n: int


@dataclass(frozen=True, slots=True)
class Citation:
    target: str  # a plan target (weakness-catalogue §5): a metric id, or AN-07:<share>
    metric_name: str
    metric_version: str
    k: int  # AN-04: the count; AN-07: the share's count
    n: int  # AN-04: games
    low_sample: bool
    rally_ids: tuple[RallyRef, ...]
    evidence: tuple[EvidenceLink, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rally_ids", tuple(RallyRef(*r) for r in self.rally_ids))
        object.__setattr__(self, "evidence", tuple(EvidenceLink(*e) for e in self.evidence))
        found = []
        if self.n < 1 or self.k < 0:
            found.append(f"QD-PL-04: {self.target} has no sample (k={self.k}, n={self.n})")
        if len(self.rally_ids) > EVIDENCE_MAX:
            found.append(f"QD-PL-04: {self.target} cites {len(self.rally_ids)} rallies, at most 10")
        if {r.match_id for r in self.rally_ids} - {e.match_id for e in self.evidence}:
            found.append(f"QD-PL-04: {self.target} cites a rally outside its evidence")
        if found:
            raise MissingCitation(found)

    @classmethod
    def from_evidence(
        cls,
        *,
        target: str,
        metric_name: str,
        metric_version: str,
        k: int,
        n: int,
        low_sample: bool,
        evidence: Iterable[tuple[str, str, Sequence[str]]],
    ) -> Citation:
        """From each match's full evidence list (video order): the first 10 rallies across the
        matches in order, and one link per match with its evidence total."""
        lists = [(m, side, tuple(ids)) for m, side, ids in evidence]
        refs = [RallyRef(m, r) for m, _, ids in lists for r in ids][:EVIDENCE_MAX]
        links = tuple(EvidenceLink(m, side, len(ids)) for m, side, ids in lists)
        return cls(target, metric_name, metric_version, k, n, low_sample, tuple(refs), links)

    @property
    def metric_id(self) -> str:
        return self.target.split(":")[0]

    @property
    def value(self) -> Fraction:
        return Fraction(self.k, self.n)

    @property
    def see_all(self) -> int:
        return sum(e.n for e in self.evidence)

    @property
    def why(self) -> str:
        """The metric and its value, e.g. "Serve faults: 29% of 7 serves" (FR-122)."""
        if self.metric_id == "AN-04":
            games = "game" if self.n == 1 else "games"
            return f"{self.metric_name}: {float(round(self.value, 1)):.1f} over {self.n} {games}"
        name = self.metric_name
        if self.target in _SHARES:
            name = f"{name} ({_SHARES[self.target]})"
        return f"{name}: {round(self.value * 100)}% of {self.n} {_NOUNS[self.metric_id]}"

    def content(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "target": self.target,
            "metric_version": self.metric_version,
            "value": float(round(self.value, 4)),
            "n": self.n,
            "k": self.k,
            "low_sample": self.low_sample,
            "rally_ids": [list(r) for r in self.rally_ids],
            "evidence": [list(e) for e in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class LimitedData:
    """QD-PL-06: the plan's top weakness metric is low-sample; R counted rallies in scope."""

    rallies: int

    @property
    def text(self) -> str:
        return f"based on limited data from {self.rallies} rallies"


@dataclass(frozen=True, slots=True)
class CitedAssignment:
    assignment: DrillAssignment
    citation: Citation

    def __post_init__(self) -> None:
        drill = self.assignment.drill
        if not isinstance(self.citation, Citation):
            raise MissingCitation([f"QD-PL-04: {drill.ref} has no citation"])
        if self.citation.target not in _targets(drill):
            raise MissingCitation([f"QD-PL-04: {drill.ref} does not target {self.citation.target}"])

    @property
    def why(self) -> str:
        return self.citation.why


def _targets(d: Drill) -> list[str]:
    """The drill's citable targets: its metrics in order, AN-07 as its share targets."""
    return [t for m in d.target_metrics for t in sorted(d.plan_targets) if t.split(":")[0] == m]


def citable(library: Iterable[Drill], citations: Mapping[str, Citation]) -> list[Drill]:
    """QD-PL-04: a drill with no citable metric is not eligible."""
    return [d for d in library if any(t in citations for t in _targets(d))]


def source_matches(citations: Mapping[str, Citation]) -> frozenset[str]:
    """coaching-plan §8: the plan's source matches, every match a citation has evidence from
    (each fed the pooled numbers, cited rally or not). A tagged match that adds no evidence
    to any metric is not a source, so deleting it does not make the plan stale (deliberate:
    the plan's numbers do not depend on it; QA-ST061b-R2-04)."""
    return frozenset(e.match_id for c in citations.values() for e in c.evidence)


def deleted_sources(sources: Iterable[_Id], live: Iterable[_Id]) -> frozenset[_Id]:
    """coaching-plan §8: the source matches that are no longer live; any makes the plan stale."""
    return frozenset(sources) - frozenset(live)


class CitedPlan:
    """The plan with a citation on every assignment and its limited-data notice (QD-PL-04/06).

    A weakness drill cites its weakness's target; a warm-up the highest-ranked weakness target it
    trains, else its first citable target. Any assignment, or the top weakness, with no citation
    refuses the whole plan."""

    def __init__(self, plan: TrainingPlan, citations: Mapping[str, Citation], rallies: int):
        self.plan = plan
        self.rallies = rallies
        targets = {w.id: w.target for w in plan.weaknesses}
        by_rank = sorted(plan.weaknesses, key=lambda w: w.rank)
        ranked = [w.target for w in by_rank]
        found: list[str] = []
        sessions = []
        for s in plan.sessions:
            cited = []
            for x in s.assignments:
                if x.weakness_id is not None:
                    wanted = [targets[x.weakness_id]]
                else:
                    own = _targets(x.drill)
                    wanted = [t for t in ranked if t in own] + own
                target = next((t for t in wanted if t in citations), None)
                if target is None:
                    at = f"week {s.week} session {s.index} {x.drill.ref}"
                    found.append(f"QD-PL-04: {at} has no citation")
                    continue
                cited.append(CitedAssignment(x, citations[target]))
            sessions.append(tuple(cited))
        top = ranked[0] if ranked else None
        if top is None or top not in citations:
            name = by_rank[0].id if by_rank else None
            found.append(f"QD-PL-04: top weakness {name} has no citation")
        if found:
            raise MissingCitation(found)
        self.sessions: tuple[tuple[CitedAssignment, ...], ...] = tuple(sessions)
        low = top is not None and citations[top].low_sample
        self.limited_data = LimitedData(rallies) if low else None

    def content(self) -> dict[str, Any]:
        content = self.plan.content()
        content["limited_data"] = None if self.limited_data is None else {"rallies": self.rallies}
        for s, cited in zip(content["sessions"], self.sessions, strict=True):
            for row, x in zip(s["assignments"], cited, strict=True):
                row["citation"] = x.citation.content()
                row["why"] = x.why
        return content

    def content_digest(self) -> str:
        blob = json.dumps(self.content(), sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()
