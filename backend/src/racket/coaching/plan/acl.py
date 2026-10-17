"""Coaching's ACL for plan citations (ST-057; coaching-plan §4; map R8, R12).

``citations_for`` pools each plan target's metric over the owner's tagged live matches with an
``is_me`` side (coaching-plan §3 scope), read only through ``racket.matches.public`` and
``racket.analytics.public``, and returns domain ``Citation`` values. With one match in scope the
numbers equal ``GET /matches/{id}/stats`` for that side, and every rally is in its evidence.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from racket.analytics import public as analytics
from racket.coaching.plan.domain import Citation
from racket.matches import public as matches

PLAN_TARGETS = ("AN-01", "AN-02", "AN-04", "AN-05", "AN-07:fault", "AN-07:forced-error")
_ENDINGS = {"AN-07:fault": "fault", "AN-07:forced-error": "forced_error"}


@dataclass(frozen=True, slots=True)
class CitationFacts:
    citations: dict[str, Citation] = field(default_factory=dict)
    rallies: int = 0  # counted rallies in scope (QD-PL-06)


def citations_for(session: Session, owner_id: uuid.UUID) -> CitationFacts:
    """Every plan target with n >= 1 in scope, as a ``Citation`` (matches in match id order,
    the global lock order, deletion-and-purge.md §3.1)."""
    scoped: list[tuple[str, str, analytics.MatchMetrics]] = []
    for match_id, side in sorted(matches.player_sides(session, owner_id), key=lambda m: m[0]):
        if side is None:
            continue  # no is_me participant: skipped, as the ranking does
        found = analytics.metric_facts(session, match_id, side)
        if found is not None and found.rallies:
            scoped.append((str(match_id), side, found))
    citations = {}
    for target in PLAN_TARGETS:
        metric = target.split(":")[0]
        per_match = [(m, side, f.metrics[metric]) for m, side, f in scoped if metric in f.metrics]
        facts = [fact for _, _, fact in per_match]
        k = sum(_k(target, fact) for fact in facts)
        n = sum(fact.n for fact in facts)
        if n < 1:
            continue
        citations[target] = Citation.from_evidence(
            target=target,
            metric_name=facts[0].name,
            metric_version=facts[0].version,
            k=k,
            n=n,
            low_sample=analytics.pooled_low_sample(metric, facts, k),
            evidence=[(m, side, fact.rally_ids) for m, side, fact in per_match],
        )
    return CitationFacts(citations, sum(f.rallies for _, _, f in scoped))


def _k(target: str, fact: analytics.MetricFact) -> int:
    return fact.counts.get(_ENDINGS[target], 0) if target in _ENDINGS else fact.k
