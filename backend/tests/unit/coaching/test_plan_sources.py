"""Unit tests: a plan's source matches and when they make it stale (ST-061b review PE-ST061b-01;
coaching-plan §8: a plan whose source matches include a match that is no longer live is stale).
Pure domain; negative cases first."""

from __future__ import annotations

import pytest

from racket.coaching.plan.domain import deleted_sources, source_matches
from tests.unit.coaching.citation_helpers import cite

pytestmark = [pytest.mark.unit, pytest.mark.coaching]


def test_no_citation_names_no_source_match() -> None:
    assert source_matches({}) == frozenset()


def test_the_sources_are_every_match_any_citation_has_evidence_from() -> None:
    citations = {
        "AN-04": cite("AN-04", 2, 1, matches=("m1", "m2")),
        "AN-05": cite("AN-05", 2, 7, matches=("m3",)),
    }
    assert source_matches(citations) == frozenset({"m1", "m2", "m3"})


def test_a_match_with_evidence_but_no_cited_rally_is_still_a_source() -> None:
    """Only the first 10 rallies are cited, but every evidence match fed the numbers."""
    citation = cite("AN-04", 12, 2, rallies=10, matches=("m1", "m2"))
    assert {r.match_id for r in citation.rally_ids} == {"m1"}
    assert source_matches({"AN-04": citation}) == frozenset({"m1", "m2"})


def test_a_source_that_is_not_live_any_more_is_deleted() -> None:
    assert deleted_sources({"m1", "m2"}, live={"m1"}) == frozenset({"m2"})


def test_no_source_is_deleted_while_every_source_is_live() -> None:
    assert deleted_sources({"m1", "m2"}, live={"m1", "m2", "m9"}) == frozenset()
    assert deleted_sources(set(), live=set()) == frozenset()
