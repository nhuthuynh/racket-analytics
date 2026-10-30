"""QA-VERIFY04R3-07 (G04-11 c): Coaching's citation ACL (ST-057; coaching-plan §3, §4, §8).

``citations_from`` pools each plan target over the scoped matches (AN-07 split by ending);
``citations_for`` scopes the owner's matches (an ``is_me`` side, a live sheet, at least one
counted rally) in match-id order; ``live_matches`` and ``scope_key`` delegate to Matches. The
other contexts are reached only through their ``public`` modules, so these unit tests replace
those functions; IT-04-02 runs the same code on Postgres. Negative cases first.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

import pytest

from racket.analytics import public as analytics
from racket.analytics.public import MatchMetrics, MetricFact
from racket.coaching.plan import acl
from racket.matches import public as matches

pytestmark = [pytest.mark.unit, pytest.mark.coaching]

IVY = uuid.UUID(int=1)
M1, M2, M3 = uuid.UUID(int=11), uuid.UUID(int=12), uuid.UUID(int=13)
DB: Any = object()  # the session is only passed through to the public functions


def fact(
    metric_id: str,
    k: int,
    n: int,
    rallies: tuple[str, ...] = (),
    counts: Mapping[str, int] | None = None,
) -> MetricFact:
    return MetricFact(
        metric_id=metric_id,
        name=f"name of {metric_id}",
        version="1.2.0",
        k=k,
        n=n,
        counts=dict(counts or {}),
        low_sample=False,
        lower_bound=False,
        rally_ids=rallies,
    )


def metrics(rallies: int, *facts: MetricFact) -> MatchMetrics:
    return MatchMetrics(rallies=rallies, metrics={f.metric_id: f for f in facts})


# ------------------------------------------------------------------ citations_from (pure)
def test_no_scoped_match_gives_no_citation_and_no_rallies() -> None:
    assert acl.citations_from([]) == acl.CitationFacts({}, 0)


def test_a_target_with_no_sample_is_not_cited() -> None:
    found = acl.citations_from([("m1", "A", metrics(5, fact("AN-05", 0, 0)))])
    assert found.citations == {}
    assert found.rallies == 5


def test_one_serve_is_enough_to_cite_and_the_pooled_flag_is_the_dictionary_s() -> None:
    found = acl.citations_from([("m1", "A", metrics(1, fact("AN-05", 1, 1, ("r1",))))])
    assert (found.citations["AN-05"].n, found.citations["AN-05"].low_sample) == (1, True)
    many = [("m1", "A", metrics(400, fact("AN-05", 40, 400, ("r1",))))]
    assert acl.citations_from(many).citations["AN-05"].low_sample is False


def test_a_metric_is_pooled_over_matches_in_the_order_given() -> None:
    scoped = [
        ("m2", "B", metrics(9, fact("AN-05", 1, 4, ("r21",)))),
        ("m1", "A", metrics(6, fact("AN-05", 2, 3, ("r11", "r12")))),
    ]
    c = acl.citations_from(scoped).citations["AN-05"]
    assert (c.target, c.metric_name, c.metric_version) == ("AN-05", "name of AN-05", "1.2.0")
    assert (c.k, c.n) == (3, 7)
    assert [tuple(r) for r in c.rally_ids] == [("m2", "r21"), ("m1", "r11"), ("m1", "r12")]
    assert [tuple(e) for e in c.evidence] == [("m2", "B", 1), ("m1", "A", 2)]
    assert acl.citations_from(scoped).rallies == 15


def test_a_match_without_the_metric_adds_nothing_to_it() -> None:
    scoped = [
        ("m1", "A", metrics(6, fact("AN-05", 2, 3, ("r11",)))),
        ("m2", "A", metrics(4, fact("AN-01", 1, 2, ("r21",)))),
    ]
    found = acl.citations_from(scoped).citations
    assert sorted(found) == ["AN-01", "AN-05"]
    assert [tuple(e) for e in found["AN-05"].evidence] == [("m1", "A", 1)]
    assert [tuple(e) for e in found["AN-01"].evidence] == [("m2", "A", 1)]


def test_an_07_is_cited_per_ending_with_its_own_count() -> None:
    endings = {"fault": 3, "forced_error": 2, "winner": 5}
    scoped = [("m1", "A", metrics(10, fact("AN-07", 0, 10, ("r1",), endings)))]
    found = acl.citations_from(scoped).citations
    assert "AN-07" not in found
    assert (found["AN-07:fault"].k, found["AN-07:fault"].n) == (3, 10)
    assert (found["AN-07:forced-error"].k, found["AN-07:forced-error"].n) == (2, 10)


def test_an_ending_that_never_happened_is_cited_as_zero() -> None:
    scoped = [("m1", "A", metrics(10, fact("AN-07", 0, 10, ("r1",), {"winner": 10})))]
    found = acl.citations_from(scoped).citations
    assert (found["AN-07:fault"].k, found["AN-07:forced-error"].k) == (0, 0)


def test_a_metric_other_than_an_07_is_cited_with_its_k() -> None:
    scoped = [("m1", "A", metrics(10, fact("AN-04", 4, 2, (), {"fault": 9})))]
    assert acl.citations_from(scoped).citations["AN-04"].k == 4


# ------------------------------------------------------------------ citations_for (scope)
@pytest.fixture
def reads(monkeypatch: pytest.MonkeyPatch) -> list[tuple[uuid.UUID, str]]:
    """Ivy's matches: M3 (side A), M1 (side B), M2 (no is_me side); metric reads recorded."""
    seen: list[tuple[uuid.UUID, str]] = []
    by_match = {
        M1: metrics(4, fact("AN-05", 1, 2, ("r11",))),
        M3: metrics(6, fact("AN-05", 2, 5, ("r31",))),
    }

    def player_sides(db: object, owner: uuid.UUID) -> list[tuple[uuid.UUID, str | None]]:
        assert (db, owner) == (DB, IVY)
        return [(M3, "A"), (M1, "B"), (M2, None)]

    def metric_facts(db: object, match_id: uuid.UUID, side: str) -> MatchMetrics | None:
        assert db is DB
        seen.append((match_id, side))
        return by_match.get(match_id)

    monkeypatch.setattr(matches, "player_sides", player_sides)
    monkeypatch.setattr(analytics, "metric_facts", metric_facts)
    return seen


def test_a_match_without_an_is_me_side_is_never_read(reads: list[tuple[uuid.UUID, str]]) -> None:
    acl.citations_for(DB, IVY)
    assert M2 not in {m for m, _ in reads}


def test_scoped_matches_are_read_and_cited_in_match_id_order(
    reads: list[tuple[uuid.UUID, str]],
) -> None:
    found = acl.citations_for(DB, IVY)
    assert reads == [(M1, "B"), (M3, "A")]
    c = found.citations["AN-05"]
    assert [tuple(e) for e in c.evidence] == [(str(M1), "B", 1), (str(M3), "A", 1)]
    assert (c.k, c.n, found.rallies) == (3, 7, 10)


def test_a_gone_match_or_one_with_no_counted_rally_is_out_of_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(matches, "player_sides", lambda _db, _o: [(M1, "A"), (M2, "A")])
    answers = {M1: None, M2: metrics(0, fact("AN-05", 1, 2, ("r",)))}
    monkeypatch.setattr(analytics, "metric_facts", lambda _db, m, _s: answers[m])
    assert acl.citations_for(DB, IVY) == acl.CitationFacts({}, 0)


# ------------------------------------------------------------------ live matches and scope key
def test_live_matches_asks_once_for_each_id_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[list[uuid.UUID]] = []

    def live_ids(db: object, ids: list[uuid.UUID]) -> set[uuid.UUID]:
        assert db is DB
        asked.append(ids)
        return {M1}

    monkeypatch.setattr(matches, "live_ids", live_ids)
    assert acl.live_matches(DB, [M3, M1, M3, M2]) == {M1}
    assert asked == [[M1, M2, M3]]


def test_the_scope_key_is_the_owner_s_locked_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    key = ((M1, "A", 7),)
    calls: list[tuple[object, uuid.UUID]] = []

    def lock_scope_versions(db: object, owner: uuid.UUID) -> tuple[object, ...]:
        calls.append((db, owner))
        return key

    monkeypatch.setattr(matches, "lock_scope_versions", lock_scope_versions)
    assert acl.scope_key(DB, IVY) == key
    assert calls == [(DB, IVY)]
