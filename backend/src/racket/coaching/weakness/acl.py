"""Coaching's Anticorruption Layer for weakness ranking (ST-055; coaching-plan.md §4; map R8, R12).

Analytics' read model (``racket.analytics.public.rally_facts``) and Match's port
(``racket.matches.public.player_sides``) are translated here into the domain's ``RallyFact``;
Coaching never reads Analytics' sheet, attribution, snapshot or tables.

Scope (coaching-plan §3): the owner's live matches with at least one counted rally ("tagged")
and a participant marked ``is_me``. A tagged match without ``is_me`` is skipped and counted in
``skipped_matches``: guessing the side would rank the opponent's weaknesses (judgment, PE-4).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy.orm import Session

from racket.analytics import public as analytics
from racket.coaching.weakness.domain import RallyFact, RallyLoss, WeaknessRanking, attribute, rank
from racket.matches import public as matches

# Rules versions whose side-out rule the coach has verified (rules-verified.md row 1). Empty
# until P7: fail closed, an unknown version is never taken as verified.
SIDE_OUT_VERIFIED_RULES: frozenset[str] = frozenset()


def translate(facts: analytics.RallyFacts) -> tuple[RallyFact, ...]:
    """Analytics' counted rallies in Coaching's language (no Analytics type leaks past here)."""
    return tuple(
        RallyFact(
            rally_id=r.rally_id,
            game=r.game,
            serving_side=r.serving_side,
            winning_side=r.winning_side,
            ending=r.ending,
            fault_kind=r.fault_kind,
            responsible_player=r.responsible_player,
            point_to=r.point_to,
        )
        for r in facts.rallies
    )


def ranking_for(session: Session, owner_id: uuid.UUID) -> WeaknessRanking:
    """The owner's weakness ranking over every tagged live match in scope.

    Each ``rally_facts`` read keeps its match row ``FOR SHARE`` to the caller's commit, so the
    rows are read in ascending match id order, the order ``DELETE /me`` tombstones them in
    (global lock order, deletion-and-purge.md §3.1; PE-055-R1-01). The ranking does not depend
    on the order of the matches."""
    scoped = []
    for match_id, side in sorted(matches.player_sides(session, owner_id), key=_match_id):
        facts = analytics.rally_facts(session, match_id)
        if facts is not None and facts.rallies:  # else deleted meanwhile, or not tagged
            scoped.append((match_id, side, facts))
    return ranking_of(scoped)


def ranking_of(
    scoped: Iterable[tuple[uuid.UUID, str | None, analytics.RallyFacts]],
) -> WeaknessRanking:
    """The ranking over tagged matches already read: (match id, the player's side or None,
    the match's rally facts). A match without a side is skipped and counted (pure; ST-060)."""
    losses: list[RallyLoss] = []
    games = rallies = skipped = 0
    rules: set[str] = set()
    for match_id, side, facts in scoped:
        if side is None:
            skipped += 1
            continue
        translated = translate(facts)
        losses += attribute(match_id, side, translated)
        games += len(facts.games)
        rallies += len(translated)
        rules.add(facts.rules_version)
    return rank(
        losses,
        games,
        rallies=rallies,
        skipped_matches=skipped,
        side_out_verified=_side_out_verified(rules),
    )


def _side_out_verified(rules_versions: Iterable[str]) -> bool:
    """True only when every match in scope is scored by a rules version whose side-out rule
    is verified (DOM G1 R2, P7); with no match in scope nothing is verified either."""
    versions = set(rules_versions)
    return bool(versions) and versions <= SIDE_OUT_VERIFIED_RULES


def _match_id(match_side: tuple[uuid.UUID, str | None]) -> uuid.UUID:
    return match_side[0]
