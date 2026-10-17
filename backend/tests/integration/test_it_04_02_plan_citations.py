"""IT-04-02b (ST-057; FR-122, FR-123; QD-PL-04, QD-PL-06; coaching-plan §4-§5): plan citations
from tagged matches in Postgres, read through Coaching's ACL, equal what the player sees in
``GET /matches/{id}/stats`` and every cited rally id is in ``GET …/stats/{metric}/evidence``.

Matches are created and tagged through the API (Ivy is slot A1, ``is_me``, so side A); the
citations are then built by ``racket.coaching.plan.acl.citations_for`` on a fresh session, which
reads only ``racket.matches.public`` and ``racket.analytics.public``. Negative cases first.
"""

from __future__ import annotations

import uuid
from fractions import Fraction
from typing import Any

import pytest
from sqlalchemy.orm import Session

from racket.coaching.plan import acl
from racket.coaching.plan.domain import (
    CitedPlan,
    MissingCitation,
    PlanWeakness,
    TrainingPlan,
    assemble,
    citable,
)
from racket.coaching.weakness import acl as weakness_acl
from tests.support import stats as st
from tests.support.api import ApiDriver
from tests.unit.coaching.plan_helpers import TOP_3, reviewed_test_library, solo_wall

pytestmark = [pytest.mark.needs_verification, pytest.mark.coaching]

_SHARE = {"AN-07:fault": "fault", "AN-07:forced-error": "forced_error"}


def _facts(engine: Any, api: ApiDriver, user: str) -> acl.CitationFacts:
    owner = uuid.UUID(st.me_id(api, user))
    with Session(bind=engine) as session:
        return acl.citations_for(session, owner)


def _expected(stats: dict[str, Any], target: str) -> tuple[int, int, Any, bool, str]:
    """(k, n, rounded value, low_sample, metric version) of ``target`` for side A in GET stats."""
    metric = stats["metrics"][target.split(":")[0]]
    a = metric["A"]
    version = metric["entry"]["version"]
    if target == "AN-04":
        return a["count"], a["games"], a["value"], a["low_sample"], version
    if target in _SHARE:
        share = a["shares"][_SHARE[target]]
        return share["k"], a["n"], share["value"], a["low_sample"], version
    return a["k"], a["n"], a["value"], a["low_sample"], version


def _evidence_ids(api: ApiDriver, match_id: str, metric: str) -> tuple[list[str], int]:
    response = st.evidence(api, "ivy", match_id, metric, "A")
    assert response.status_code == 200, response.text
    body = response.json()
    return [item["rally_id"] for item in body["items"]], body["total"]


def test_it_04_02b_no_tagged_match_gives_no_citation_and_no_plan_can_be_cited(
    api: ApiDriver, committed_db: Any
) -> None:
    facts = _facts(committed_db, api, "ivy")
    assert (facts.citations, facts.rallies) == ({}, 0)
    plan = assemble(TOP_3, solo_wall(), reviewed_test_library())
    assert isinstance(plan, TrainingPlan)
    with pytest.raises(MissingCitation, match="QD-PL-04"):
        CitedPlan(plan, facts.citations, rallies=facts.rallies)


def test_it_04_02b_a_deleted_match_and_another_players_match_are_never_cited(
    api: ApiDriver, committed_db: Any
) -> None:
    mine = st.tagged_example(api, "ivy", "IT-04-02b deleted")
    st.tagged_example(api, "carlos", "IT-04-02b someone else")
    assert _facts(committed_db, api, "ivy").rallies == 13
    response = st.delete_match(api, "ivy", mine)
    assert response.status_code in (200, 202, 204), response.text
    facts = _facts(committed_db, api, "ivy")
    assert (facts.citations, facts.rallies) == ({}, 0)


def test_it_04_02b_citations_equal_get_stats_and_cite_get_evidence(
    api: ApiDriver, committed_db: Any
) -> None:
    match_id = st.tagged_example(api, "ivy", "IT-04-02b worked example")
    facts = _facts(committed_db, api, "ivy")
    stats = st.stats_body(api, "ivy", match_id)
    assert facts.rallies == 13
    assert sorted(facts.citations) == sorted(acl.PLAN_TARGETS)
    for target, c in facts.citations.items():
        k, n, value, low_sample, version = _expected(stats, target)
        assert (c.k, c.n, c.low_sample, c.metric_version) == (k, n, low_sample, version), target
        places = 1 if target == "AN-04" else 4
        assert round(float(c.value), places) == value, target
        ids, total = _evidence_ids(api, match_id, c.metric_id)
        assert [rally for m, rally in c.rally_ids] == ids[:10], target
        assert {m for m, _ in c.rally_ids} <= {match_id}
        assert c.evidence == ((match_id, "A", total),), target


def test_it_04_02b_two_matches_pool_their_numbers_and_evidence(
    api: ApiDriver, committed_db: Any
) -> None:
    first = st.tagged_example(api, "ivy", "IT-04-02b first")
    second = st.tagged_example(api, "ivy", "IT-04-02b second")
    facts = _facts(committed_db, api, "ivy")
    assert facts.rallies == 26
    one = st.stats_body(api, "ivy", first)
    for target, c in facts.citations.items():
        k, n, _, _, _ = _expected(one, target)
        assert (c.k, c.n) == (2 * k, 2 * n), target
        assert c.value == Fraction(2 * k, 2 * n)
        for match_id in (first, second):
            ids, _ = _evidence_ids(api, match_id, c.metric_id)
            assert {r for m, r in c.rally_ids if m == match_id} <= set(ids), target
        assert {m for m, _, _ in c.evidence} == {first, second}
        assert len(c.rally_ids) <= 10


def test_it_04_02b_a_plan_from_one_short_match_cites_every_drill_and_says_limited_data(
    api: ApiDriver, committed_db: Any
) -> None:
    st.tagged_example(api, "ivy", "IT-04-02b plan")
    facts = _facts(committed_db, api, "ivy")
    owner = uuid.UUID(st.me_id(api, "ivy"))
    with Session(bind=committed_db) as session:
        ranking = weakness_acl.ranking_for(session, owner)
    top = [PlanWeakness(w.id, w.plan_target, w.rank) for w in ranking.weaknesses[:3]]
    plan = assemble(top, solo_wall(), citable(reviewed_test_library(), facts.citations))
    assert isinstance(plan, TrainingPlan), plan
    cited = CitedPlan(plan, facts.citations, rallies=facts.rallies)
    for session_ in cited.sessions:
        for x in session_:
            assert x.citation == facts.citations[x.citation.target]
    assert facts.citations[top[0].target].low_sample  # 1 game: every metric is low-sample
    assert cited.limited_data is not None
    assert (cited.limited_data.rallies, cited.limited_data.text) == (
        13,
        "based on limited data from 13 rallies",
    )
