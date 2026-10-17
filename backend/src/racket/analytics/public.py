"""Analytics' published port: the purge job (deletion-and-purge.md §4.2, §5) and the read
model Coaching translates at its ACL (ST-055; coaching-plan.md §4, context map R8)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from racket.analytics.repository import SnapshotRepository
from racket.analytics.sheet import counted_rallies, game_numbers_in_scope
from racket.matches import public as matches


def purge_match(session: Session, match_id: uuid.UUID) -> int:
    """Delete every snapshot of the match (in the caller's transaction). Rows deleted."""
    return SnapshotRepository(session).delete_for_match(match_id)


def snapshot_match_ids(
    session: Session, after: uuid.UUID | None, limit: int
) -> Sequence[uuid.UUID]:
    """Match ids that have snapshot rows, ascending, one page (orphan sweep, SEC-S3-TM-02)."""
    return SnapshotRepository(session).match_ids(after, limit)


@dataclass(frozen=True, slots=True)
class RallyFact:
    """One counted rally (metric-dictionary rules 0.1, 0.2) as plain values (read model)."""

    rally_id: str
    number: int
    game: int
    serving_side: str
    winning_side: str
    ending: str
    fault_kind: str | None
    responsible_player: str | None
    actor: str  # the side that made the ending (rule 0.2)
    point_to: str | None  # the side that scored, None when only the serve moved


@dataclass(frozen=True, slots=True)
class RallyFacts:
    """The counted rallies of a match's games in scope (dictionary AN-04), in play order."""

    sheet_version: int | None
    rules_version: str
    games: tuple[int, ...]
    rallies: tuple[RallyFact, ...]


def facts_of_sheet(sheet: Mapping[str, Any], sheet_version: int | None = None) -> RallyFacts:
    """The read model of a projected score sheet (pure; ``rally_facts`` reads the live one)."""
    games = tuple(game_numbers_in_scope(sheet))
    in_scope = set(games)
    rallies = tuple(
        RallyFact(
            rally_id=r.rally_id,
            number=r.number,
            game=r.game,
            serving_side=r.serving_side,
            winning_side=r.winning_side,
            ending=r.ending,
            fault_kind=r.fault_kind,
            responsible_player=r.responsible_player,
            actor=r.actor,
            point_to=r.point_to,
        )
        for r in counted_rallies(sheet)
        if r.game in in_scope
    )
    return RallyFacts(sheet_version, str(sheet.get("rules_version", "")), games, rallies)


def rally_facts(session: Session, match_id: uuid.UUID) -> RallyFacts | None:
    """The counted rallies of a live match; ``None`` when the match is gone (tombstoned or
    purged). Read-only; the match row stays share-locked until the caller ends its
    transaction (``lock_live_sheet``)."""
    live = matches.lock_live_sheet(session, match_id)
    if live is None:
        return None
    return facts_of_sheet(live.sheet, live.version)


@dataclass(frozen=True, slots=True)
class MetricFact:
    """One published metric of one side of a match (ST-057; coaching-plan §4), as in
    ``GET …/stats``: ``k`` of ``n`` (AN-04: count of games; AN-07: ``counts`` per ending), the
    flag, and the evidence ``rally_ids`` in the order ``GET …/evidence`` lists them."""

    metric_id: str
    name: str
    version: str
    k: int
    n: int
    counts: Mapping[str, int]
    low_sample: bool
    lower_bound: bool  # AN-05: a fault without its type, so the value is a lower bound
    rally_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MatchMetrics:
    rallies: int  # counted rallies in scope (dictionary rule 0.1)
    metrics: Mapping[str, MetricFact]


_K_N = {"AN-03": ("points", "turns"), "AN-04": ("count", "games")}


def metric_facts(session: Session, match_id: uuid.UUID, side: str) -> MatchMetrics | None:
    """The published metrics of the live sheet for ``side`` (read repair as ``GET …/stats``;
    commits the caller's session). ``None`` when the match is gone."""
    from racket.analytics import service
    from racket.analytics.evidence import EvidenceQuery, evidence_page
    from racket.sports.pickleball import metrics

    found = service.current(session, match_id, trigger="read")
    if found is None:
        return None
    rows = found.sheet.get("rows", ())
    out: dict[str, MetricFact] = {}
    for entry in metrics.load_dictionary().published():
        fields = found.snapshot.stats.get(entry.id, {}).get(side)
        k_key, n_key = _K_N.get(entry.id, ("k", "n"))
        if fields is None or n_key not in fields:
            continue
        numbers = found.snapshot.rallies(entry.id, side)
        everything = EvidenceQuery(side, len(numbers) + 1, 0)
        items, _, _ = evidence_page(rows, numbers, everything)
        out[entry.id] = MetricFact(
            metric_id=entry.id,
            name=entry.name,
            version=entry.version,
            k=int(fields.get(k_key, 0)),
            n=int(fields[n_key]),
            counts=dict(fields.get("counts", {})),
            low_sample=bool(fields["low_sample"]),
            lower_bound=bool(fields.get("fault_type_not_tagged", 0)),
            rally_ids=tuple(str(i["rally_id"]) for i in items),
        )
    rallies = len(facts_of_sheet(found.sheet).rallies)
    return MatchMetrics(rallies, out)


def pooled_low_sample(metric_id: str, facts: Sequence[MetricFact], k: int) -> bool:
    """The dictionary's low-sample rule (ADR 0041, ADR 0005) on numbers pooled over matches:
    ``k`` of the summed n (AN-07: every summed ending share, rule 0.3)."""
    from racket.analytics.snapshot import policy_from_dictionary
    from racket.sports.pickleball import metrics

    policy = policy_from_dictionary(metrics.load_dictionary())
    n = sum(f.n for f in facts)
    if metric_id == "AN-04":
        return policy.count_flagged(games=n)
    if metric_id == "AN-03":
        return policy.turns_flagged(n)
    if metric_id == "AN-07":
        endings = {c for f in facts for c in f.counts}
        shares = [sum(f.counts.get(c, 0) for f in facts) for c in sorted(endings)]
        return any(policy.proportion_flagged(c, n, metric_id) for c in shares) or n == 0
    flagged = policy.proportion_flagged(k, n, metric_id)
    return flagged or any(f.lower_bound for f in facts)
