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
The one ``regenerated`` value the contract defines is also used when every source is live but
the live numbers no longer cite the saved plan (e.g. after a scorebook correction): decision
row "regenerated label" in docs/sprints/04/decisions/ST-061b.md (QA-ST061b-R2-03).
A lost save race (``IntegrityError``) is retried once from the start, then 409
``plan_conflict`` (api-sprint-04 §3.4).

Follow-through (ST-062; FR-124; api-sprint-04 §3): ``mark_done`` / ``undo_done`` / ``swap`` load
the owner's plan, find the session or assignment by its id among the owner's rows (anything else
is 404 ``not_found``, as an unknown id), run the aggregate's command and save it with the
version check (``PlanRepository.update``). Done ops are idempotent by ``(account_id, op_id)``: a
replay answers the stored result; the same key on another session is 409
``idempotency_key_reused``. Only a mark that changes the plan stores its op row; a new key on a
session already done is a no-op that stores none (threat-notes-sprint-04 T4-PL-5). A lost
race (``IntegrityError`` or ``PlanConflict``) is retried once, then 409 ``plan_conflict``. A swap
needs the live citations, so a stale plan, or one the live data no longer cites, is 409
``plan_conflict`` (the client reloads; ``GET`` regenerates it). Events (coaching-plan §7) are
logged after commit with ids only, never the reason.

Transactions: ``citations_for`` runs the stats read repair, which commits, so it runs first; then
the account row is held ``FOR SHARE`` (SEC-S3-TM-05: a ``DELETE /me`` commits before or after,
never across) and ``ranking_for`` holds the owner's match rows ``FOR SHARE`` to the commit.

Read cost (SRE-VERIFY04R3-01; G04-02 c): ``current`` first reads the scope key (account, then
the owner's match rows ``FOR SHARE``, as above) and reuses the ranking and citations memoised for
an equal key (``plan/scope.py``), so a read of an unchanged scope replays no scorebook.
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
from typing import NoReturn, TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from racket.coaching.drills.lock import LOCK_NAME
from racket.coaching.plan import acl as citation_acl
from racket.coaching.plan.domain import (
    CitedPlan,
    Drill,
    Infeasible,
    MissingCitation,
    NoAlternative,
    PlanWeakness,
    Preferences,
    SessionDone,
    assemble,
    citable,
    deleted_sources,
    source_matches,
)
from racket.coaching.plan.repository import DoneOp, PlanConflict, PlanRepository, StoredPlan
from racket.coaching.plan.scope import ScopeKey, ScopeMemo
from racket.coaching.schemas import PlanView
from racket.coaching.weakness import acl as weakness_acl
from racket.coaching.weakness.domain import NO_TAGGED_MATCH, WeaknessRanking
from racket.platform.errors import Conflict, NotFound, Unauthenticated
from racket.players import public as players

log = logging.getLogger(__name__)
LIBRARY_ENV = "RACKET_DRILL_LIBRARY"  # the content/drills directory; found from here if unset
SOURCE_MATCH_DELETED = "source_match_deleted"
SAVE_ATTEMPTS = 2  # the first try and one internal retry (api-sprint-04 §3.4)
SCOPE_MEMO_OWNERS = 4096  # owners whose scope facts one API process keeps (judgment)
_T = TypeVar("_T")
ScopeFacts = tuple[citation_acl.CitationFacts, WeaknessRanking]
SCOPE_MEMO: ScopeMemo[ScopeFacts] = ScopeMemo(capacity=SCOPE_MEMO_OWNERS)


class NoPlan(NotFound):
    code = "no_plan"


class NoTaggedMatch(Conflict):
    code = "no_tagged_match"


class NoPlanFits(Conflict):
    code = "no_plan_fits"


class PlanChanged(Conflict):
    code = "plan_conflict"


class NoAlternativeDrill(Conflict):
    code = "no_alternative"


class SessionAlreadyDone(Conflict):
    code = "session_done"


class OpIdReused(Conflict):
    code = "idempotency_key_reused"


@dataclass(frozen=True, slots=True)
class DoneState:
    """The answer of ``POST``/``DELETE .../done`` (api-sprint-04 §3.1, §3.2)."""

    session_id: uuid.UUID
    done_at: datetime | None
    plan_version: int
    replayed: bool = False


@dataclass(frozen=True, slots=True)
class SwapResult:
    """The answer of ``.../swap``: the saved plan, its citations and the swapped session's
    position in it."""

    stored: StoredPlan
    cited: CitedPlan
    session: int
    drill_names: Mapping[str, str]


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
        self,
        session: Session,
        library: Library,
        *,
        clock: Callable[[], datetime] = _now,
        memo: ScopeMemo[ScopeFacts] | None = None,
    ) -> None:
        self.session = session
        self.memo = SCOPE_MEMO if memo is None else memo
        self.library = library
        self.plans = PlanRepository(session, library.drills, clock=clock)
        self.clock = clock

    def generate(self, owner_id: uuid.UUID, prefs: Preferences) -> PlanView:
        """POST /me/plan: the new plan replaces the owner's plan; nothing written on a refusal."""
        started = time.monotonic()
        view = self._retrying(lambda: self._generate(owner_id, prefs))
        self._generated(view, started)
        return view

    def current(self, owner_id: uuid.UUID) -> PlanView:
        """GET /me/plan: the saved plan, re-cited; regenerated or gone when its data went."""
        started = time.monotonic()
        view, regenerated = self._retrying(lambda: self._current(owner_id))
        if not regenerated:
            return view
        self._generated(view, started)
        return replace(view, regenerated=SOURCE_MATCH_DELETED)

    def mark_done(self, owner_id: uuid.UUID, session_id: uuid.UUID, op_id: str) -> DoneState:
        """POST .../done: done once; a replay of ``op_id`` answers the stored result."""
        return self._retrying(lambda: self._mark_done(owner_id, session_id, op_id))

    def undo_done(self, owner_id: uuid.UUID, session_id: uuid.UUID) -> DoneState:
        """DELETE .../done: not done; a no-op when it is not done."""
        return self._retrying(lambda: self._undo_done(owner_id, session_id))

    def swap(self, owner_id: uuid.UUID, assignment_id: uuid.UUID, reason: str | None) -> SwapResult:
        """POST .../swap ("Not for me"): another drill for the same metric, or 409."""
        return self._retrying(lambda: self._swap(owner_id, assignment_id, reason))

    def _owned(self, owner_id: uuid.UUID) -> StoredPlan:
        self._lock_account(owner_id)
        stored = self.plans.get(owner_id)
        if stored is None:
            raise NotFound("no such session or assignment")
        return stored

    def _session_slot(self, stored: StoredPlan, session_id: uuid.UUID) -> int:
        for n, ids in enumerate(stored.sessions):
            if ids.id == session_id:
                return n
        raise NotFound("no such session")

    def _mark_done(self, owner_id: uuid.UUID, session_id: uuid.UUID, op_id: str) -> DoneState:
        stored = self._owned(owner_id)
        n = self._session_slot(stored, session_id)
        op = self.plans.done_op(owner_id, op_id)
        if op is not None:
            self.session.rollback()
            if op.session_id != session_id:
                raise OpIdReused("op id used for another session")
            return DoneState(session_id, op.done_at, op.plan_version, replayed=True)
        plan, loaded = stored.plan, stored.plan.version
        s = plan.sessions[n]
        event = plan.mark_done(week=s.week, index=s.index, at=self.clock())
        done_at = plan.sessions[n].done_at
        if done_at is None:  # pragma: no cover - mark_done leaves it set
            raise AssertionError("session not done after mark_done")
        if event is None:  # already done: a no-op that stores no op row (T4-PL-5)
            self.session.rollback()
            return DoneState(session_id, done_at, plan.version)
        self.plans.update(owner_id, stored.id, plan, loaded_version=loaded)
        self.plans.record_done_op(owner_id, op_id, DoneOp(session_id, plan.version, done_at))
        self.session.commit()
        self._event("coaching.plan.session_done", stored, session_id, op_id=op_id)
        return DoneState(session_id, done_at, plan.version)

    def _undo_done(self, owner_id: uuid.UUID, session_id: uuid.UUID) -> DoneState:
        stored = self._owned(owner_id)
        n = self._session_slot(stored, session_id)
        plan, loaded = stored.plan, stored.plan.version
        s = plan.sessions[n]
        event = plan.undo_done(week=s.week, index=s.index)
        if event is None:
            self.session.rollback()
            return DoneState(session_id, None, plan.version)
        self.plans.update(owner_id, stored.id, plan, loaded_version=loaded)
        self.session.commit()
        self._event("coaching.plan.session_undone", stored, session_id)
        return DoneState(session_id, None, plan.version)

    def _swap(
        self, owner_id: uuid.UUID, assignment_id: uuid.UUID, reason: str | None
    ) -> SwapResult:
        facts = citation_acl.citations_for(self.session, owner_id)
        stored = self._owned(owner_id)
        slot = next(
            (
                (n, k)
                for n, ids in enumerate(stored.sessions)
                for k, a in enumerate(ids.assignment_ids)
                if a == assignment_id
            ),
            None,
        )
        if slot is None:
            raise NotFound("no such assignment")
        n, k = slot
        plan, loaded = stored.plan, stored.plan.version
        s = plan.sessions[n]
        if s.done_at is not None:
            raise SessionAlreadyDone("session is done")
        live = citation_acl.live_matches(self.session, stored.source_match_ids)
        if stored.stale or deleted_sources(stored.source_match_ids, live):
            raise PlanChanged("plan is stale; reload it")
        try:
            CitedPlan(plan, facts.citations, facts.rallies)
        except MissingCitation:
            raise PlanChanged("the live data no longer cites the plan") from None
        old = s.assignments[k]
        try:
            event = plan.swap(
                week=s.week,
                index=s.index,
                position=old.position,
                library=citable(self.library.drills, facts.citations),
                cited=frozenset(facts.citations),
                reason=reason,
            )
        except SessionDone:  # pragma: no cover - checked above
            raise SessionAlreadyDone("session is done") from None
        except NoAlternative:
            raise NoAlternativeDrill("no other drill fits") from None
        cited = CitedPlan(plan, facts.citations, facts.rallies)
        self.plans.update(owner_id, stored.id, plan, loaded_version=loaded)
        self.session.commit()
        log.info(
            "plan drill swapped",
            extra={
                "event": "coaching.plan.drill_swapped",
                "plan_id": str(stored.id),
                "assignment_id": str(assignment_id),
                "from_drill": event.from_drill,
                "to_drill": event.to_drill,
                "metric_id": event.target.split(":")[0],
                "reason_given": event.reason_given,
                "version": event.version,
            },
        )
        return SwapResult(stored, cited, n, self.library.names)

    def _event(
        self, name: str, stored: StoredPlan, session_id: uuid.UUID, op_id: str | None = None
    ) -> None:
        """``SessionMarkedDone`` / ``SessionDoneUndone`` (coaching-plan §7), after commit."""
        extra = {
            "event": name,
            "plan_id": str(stored.id),
            "session_id": str(session_id),
            "version": stored.plan.version,
        }
        if op_id is not None:
            extra["op_id"] = op_id
        log.info("plan session done state changed", extra=extra)

    def _retrying(self, attempt: Callable[[], _T]) -> _T:
        """api-sprint-04 §3.4, coaching-plan §5: a lost race (a concurrent save of the owner's
        one plan or done op, ``IntegrityError``, or a command whose version check found the plan
        moved, ``PlanConflict``) is retried once from the start, then 409 ``plan_conflict``.
        Any other failure rolls back and propagates."""
        for tries in range(1, SAVE_ATTEMPTS + 1):
            try:
                return attempt()
            except (IntegrityError, PlanConflict):
                self.session.rollback()
                if tries == SAVE_ATTEMPTS:
                    raise PlanChanged("plan saved concurrently") from None
            except BaseException:
                self.session.rollback()
                raise
        raise AssertionError("unreachable")  # pragma: no cover

    def _generate(self, owner_id: uuid.UUID, prefs: Preferences) -> PlanView:
        facts = citation_acl.citations_for(self.session, owner_id)
        ranking = self._ranking(owner_id)
        view = self._build(owner_id, prefs, ranking, facts)
        self.session.commit()
        return view

    def _current(self, owner_id: uuid.UUID) -> tuple[PlanView, bool]:
        """The saved plan and False, or the regenerated plan and True (committed)."""
        facts, ranking = self._scope_facts(owner_id)
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
                return PlanView(stored, ranking, cited, self.library.names), False
        try:
            view = self._build(owner_id, stored.plan.preferences, ranking, facts)
        except NoPlanFits:
            self._drop(owner_id)
        self.session.commit()
        return view, True

    def _scope_facts(
        self, owner_id: uuid.UUID
    ) -> tuple[citation_acl.CitationFacts, WeaknessRanking]:
        """The citations and ranking of the owner's scope; reused while its key is unchanged
        (SRE-VERIFY04R3-01). The key is read with the account and match rows share-locked,
        as the live read holds them; a miss reads live and keeps the facts only when the key
        read after them is the key read before (no command landed between the two reads)."""
        before = self._scope_key(owner_id)
        if (hit := self.memo.get(owner_id, before)) is not None:
            return hit
        facts = citation_acl.citations_for(self.session, owner_id)
        ranking = self._ranking(owner_id)
        if self._scope_key(owner_id) == before:
            self.memo.put(owner_id, before, (facts, ranking))
        return facts, ranking

    def _scope_key(self, owner_id: uuid.UUID) -> ScopeKey:
        self._lock_account(owner_id)
        return citation_acl.scope_key(self.session, owner_id)

    def _ranking(self, owner_id: uuid.UUID) -> WeaknessRanking:
        self._lock_account(owner_id)
        return weakness_acl.ranking_for(self.session, owner_id)

    def _lock_account(self, owner_id: uuid.UUID) -> None:
        """The account row ``FOR SHARE`` to the commit (SEC-S3-TM-05); 401 once deleted."""
        if not players.lock_live_account(self.session, owner_id):
            raise Unauthenticated("the account was deleted")

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
