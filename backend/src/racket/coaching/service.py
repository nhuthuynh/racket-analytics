"""Coaching use cases: generate and read the current plan (ST-061b; FR-120..FR-123; NFR-019;
coaching-plan §3-§8; api-sprint-04 §2).

``PlanService.generate`` ranks the owner's weaknesses (ST-055 ACL), pools the citations (ST-057
ACL), assembles the rules-only plan over the reviewed drill library (ST-056), cites every
assignment and saves it as the owner's one plan (ST-061a repository), all or nothing.
``PlanService.current`` reads the saved plan and re-cites it from the live read models, so a
deleted match is never cited. The plan is stale when the purge marked it so or, from the
``DELETE /matches/{id}`` on, when one of its source matches (``plan_source_matches``, written
with the plan) is no longer live; a stale plan, or one the live data no longer cites, is
regenerated with its stored preferences (``regenerated: "source_match_deleted"``) or, with no
tagged match left or no plan that fits, deleted (404 ``no_plan``), as coaching-plan §8 says.

Transactions: ``citations_for`` runs the stats read repair, which commits, so it runs first; then
the account row is held ``FOR SHARE`` (SEC-S3-TM-05: a ``DELETE /me`` commits before or after,
never across) and ``ranking_for`` holds the owner's match rows ``FOR SHARE`` to the commit.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import NoReturn

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from racket.coaching.drills.lock import LOCK_NAME
from racket.coaching.plan import acl as citation_acl
from racket.coaching.plan.domain import (
    CitedPlan,
    Drill,
    Infeasible,
    MissingCitation,
    PlanWeakness,
    Preferences,
    assemble,
    citable,
    deleted_sources,
    source_matches,
)
from racket.coaching.plan.repository import PlanRepository
from racket.coaching.schemas import PlanView
from racket.coaching.weakness import acl as weakness_acl
from racket.coaching.weakness.domain import NO_TAGGED_MATCH, WeaknessRanking
from racket.platform.errors import Conflict, NotFound, Unauthenticated
from racket.players import public as players

log = logging.getLogger(__name__)
LIBRARY_ENV = "RACKET_DRILL_LIBRARY"  # the content/drills directory; found from here if unset
SOURCE_MATCH_DELETED = "source_match_deleted"


class NoPlan(NotFound):
    code = "no_plan"


class NoTaggedMatch(Conflict):
    code = "no_tagged_match"


class NoPlanFits(Conflict):
    code = "no_plan_fits"


class PlanChanged(Conflict):
    code = "plan_conflict"


@dataclass(frozen=True, slots=True)
class Library:
    """The drill library as the plan sees it: every version, names and a ``library_version``
    (sha256 of the canonical documents, review status included, so a review changes it)."""

    drills: tuple[Drill, ...]
    names: Mapping[str, str]
    version: str


def library_dir() -> Path:
    if configured := os.environ.get(LIBRARY_ENV):
        return Path(configured)
    for parent in Path(__file__).resolve().parents:
        if (parent / "content" / "drills" / LOCK_NAME).is_file():
            return parent / "content" / "drills"
    raise FileNotFoundError(f"no drill library: set {LIBRARY_ENV}")


@cache
def load_library(root: Path) -> Library:
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(root.glob("*/v*.json"))]
    blob = json.dumps(docs, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    drills = tuple(Drill.from_document(doc) for doc in docs)
    names = {f"{doc['id']}@{doc['version']}": str(doc["name"]) for doc in docs}
    return Library(drills, names, "sha256:" + hashlib.sha256(blob.encode()).hexdigest())


def _now() -> datetime:
    return datetime.now(UTC)


class PlanService:
    def __init__(
        self, session: Session, library: Library, *, clock: Callable[[], datetime] = _now
    ) -> None:
        self.session = session
        self.library = library
        self.plans = PlanRepository(session, library.drills, clock=clock)

    def generate(self, owner_id: uuid.UUID, prefs: Preferences) -> PlanView:
        """POST /me/plan: the new plan replaces the owner's plan; nothing written on a refusal."""
        started = time.monotonic()
        try:
            facts = citation_acl.citations_for(self.session, owner_id)
            ranking = self._ranking(owner_id)
            view = self._build(owner_id, prefs, ranking, facts)
            self.session.commit()
        except IntegrityError:  # a concurrent generate saved first (one plan per owner)
            self.session.rollback()
            raise PlanChanged("plan saved concurrently") from None
        except BaseException:
            self.session.rollback()
            raise
        self._generated(view, started)
        return view

    def current(self, owner_id: uuid.UUID) -> PlanView:
        """GET /me/plan: the saved plan, re-cited; regenerated or gone when its data went."""
        started = time.monotonic()
        try:
            facts = citation_acl.citations_for(self.session, owner_id)
            ranking = self._ranking(owner_id)
            stored = self.plans.get(owner_id)
            if stored is None:
                raise NoPlan("no plan")
            if ranking.reason == NO_TAGGED_MATCH:
                self._drop(owner_id)
            live = citation_acl.live_matches(self.session, stored.source_match_ids)
            if not stored.stale and not deleted_sources(stored.source_match_ids, live):
                try:
                    cited = CitedPlan(stored.plan, facts.citations, facts.rallies)
                except MissingCitation:
                    pass
                else:
                    self.session.rollback()  # read only: end the share locks
                    return PlanView(stored, ranking, cited, self.library.names)
            try:
                view = self._build(owner_id, stored.plan.preferences, ranking, facts)
            except NoPlanFits:
                self._drop(owner_id)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            raise PlanChanged("plan saved concurrently") from None
        except BaseException:
            self.session.rollback()
            raise
        self._generated(view, started)
        return replace(view, regenerated=SOURCE_MATCH_DELETED)

    def _ranking(self, owner_id: uuid.UUID) -> WeaknessRanking:
        if not players.lock_live_account(self.session, owner_id):
            raise Unauthenticated("the account was deleted")
        return weakness_acl.ranking_for(self.session, owner_id)

    def _drop(self, owner_id: uuid.UUID) -> NoReturn:
        """No tagged match or no fitting plan left: the old plan goes, 404 ``no_plan``."""
        self.plans.delete_owned(owner_id)
        self.session.commit()
        raise NoPlan("no plan can be built any more")

    def _build(
        self,
        owner_id: uuid.UUID,
        prefs: Preferences,
        ranking: WeaknessRanking,
        facts: citation_acl.CitationFacts,
    ) -> PlanView:
        if ranking.reason == NO_TAGGED_MATCH:
            raise NoTaggedMatch("no tagged match in scope")
        weaknesses = [PlanWeakness(w.id, w.plan_target, w.rank) for w in ranking.weaknesses]
        drills = citable(self.library.drills, facts.citations)  # QD-PL-04 eligibility
        plan = assemble(weaknesses, prefs, drills, self.library.version)
        if isinstance(plan, Infeasible):
            raise NoPlanFits(plan.reason)
        cited = CitedPlan(plan, facts.citations, facts.rallies)
        sources = {uuid.UUID(m) for m in source_matches(facts.citations)}
        self.plans.save(owner_id, plan, sources)
        stored = self.plans.get(owner_id)
        if stored is None:  # pragma: no cover - the row was written in this transaction
            raise PlanChanged("plan vanished after save")
        return PlanView(stored, ranking, cited, self.library.names)

    def _generated(self, view: PlanView, started: float) -> None:
        """``TrainingPlanGenerated`` (coaching-plan §7), after commit: ids and counts only."""
        sources = {e.match_id for s in view.cited.sessions for x in s for e in x.citation.evidence}
        log.info(
            "plan generated",
            extra={
                "event": "coaching.plan.generated",
                "plan_id": str(view.stored.id),
                "owner_id": str(view.stored.owner_id),
                "version": view.stored.plan.version,
                "library_version": view.stored.plan.library_version,
                "content_digest": view.cited.content_digest(),
                "source_matches": len(sources),
                "sessions": len(view.stored.plan.sessions),
                "unfitted_count": len(view.stored.plan.unfitted),
                "limited_data": view.cited.limited_data is not None,
                "duration_ms": round((time.monotonic() - started) * 1000, 1),
            },
        )
