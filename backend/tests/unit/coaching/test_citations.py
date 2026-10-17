"""Unit tests: drill citations and the limited-data plan (ST-057; FR-122, FR-123; QD-PL-04,
QD-PL-06; coaching-plan §5). Pure domain; negative cases first."""

from __future__ import annotations

from fractions import Fraction

import pytest

from racket.coaching.plan.domain import (
    Citation,
    CitedPlan,
    LimitedData,
    MissingCitation,
    PlanWeakness,
    TrainingPlan,
    assemble,
    citable,
)
from tests.unit.coaching.citation_helpers import all_citations, cite
from tests.unit.coaching.plan_helpers import TOP_3, drill, reviewed_test_library, solo_wall, warm_up

pytestmark = [pytest.mark.unit, pytest.mark.coaching]


def _plan(library: list | None = None, weaknesses: tuple = TOP_3) -> TrainingPlan:
    plan = assemble(weaknesses, solo_wall(), library or reviewed_test_library())
    assert isinstance(plan, TrainingPlan), plan
    return plan


# --- negative cases first: no assignment without a citation (QD-PL-04) ---


def test_an_assignment_without_a_citation_cannot_be_created() -> None:
    citations = {k: v for k, v in all_citations().items() if k != "AN-05"}
    with pytest.raises(MissingCitation) as refused:
        CitedPlan(_plan(), citations, rallies=13)
    assert all(v.startswith("QD-PL-04") for v in refused.value.violations)
    assert any("pb.test.serve-target@1" in v for v in refused.value.violations)


def test_a_citation_with_no_sample_is_not_a_citation() -> None:
    with pytest.raises(MissingCitation, match="QD-PL-04"):
        cite("AN-05", 0, 0)


def test_a_citation_holds_at_most_ten_rallies() -> None:
    with pytest.raises(MissingCitation, match="at most 10"):
        Citation(
            target="AN-04",
            metric_name="Unforced errors per game",
            metric_version="0.1",
            k=11,
            n=2,
            low_sample=False,
            rally_ids=tuple(("m1", f"r{i}") for i in range(11)),
            evidence=(("m1", "A", 11),),
        )


def test_a_cited_rally_must_come_from_the_cited_evidence() -> None:
    with pytest.raises(MissingCitation, match="evidence"):
        Citation(
            target="AN-04",
            metric_name="Unforced errors per game",
            metric_version="0.1",
            k=1,
            n=1,
            low_sample=False,
            rally_ids=(("other-match", "r1"),),
            evidence=(("m1", "A", 1),),
        )


def test_a_warm_up_with_no_citable_metric_is_refused() -> None:
    plan = _plan([warm_up("pb.test.serve-warm-up", targets=("AN-01",)), drill("pb.test.dinks")])
    citations = {k: v for k, v in all_citations().items() if k != "AN-01"}
    with pytest.raises(MissingCitation, match="pb.test.serve-warm-up"):
        CitedPlan(plan, citations, rallies=13)


def test_a_plan_whose_top_weakness_has_no_citation_is_refused() -> None:
    top = (PlanWeakness("opponent_winners", "AN-02", 1), *[w for w in TOP_3][:2])
    ranks = tuple(PlanWeakness(w.id, w.target, i) for i, w in enumerate(top, start=1))
    citations = {k: v for k, v in all_citations().items() if k != "AN-02"}
    with pytest.raises(MissingCitation, match="opponent_winners"):
        CitedPlan(_plan(weaknesses=ranks), citations, rallies=13)


def test_drills_with_no_citable_metric_are_not_eligible() -> None:
    library = reviewed_test_library()
    citations = {k: v for k, v in all_citations().items() if k != "AN-05"}
    kept = {d.id for d in citable(library, citations)}
    assert "pb.test.serve-target" in kept  # AN-01 is still citable
    only_an05 = {"AN-04": all_citations()["AN-04"]}
    assert "pb.test.serve-target" not in {d.id for d in citable(library, only_an05)}


# --- positive cases ---


def test_every_assignment_cites_metric_value_n_and_rallies() -> None:
    cited = CitedPlan(_plan(), all_citations(), rallies=13)
    for session in cited.sessions:
        for x in session:
            c = x.citation
            assert c.n >= 1 and c.value is not None
            assert c.metric_id in x.assignment.drill.target_metrics
            assert 1 <= len(c.rally_ids) <= 10


def test_a_weakness_drill_cites_its_weakness_metric() -> None:
    cited = CitedPlan(_plan(), all_citations(), rallies=13)
    targets = {w.id: w.target for w in TOP_3}
    for session in cited.sessions:
        for x in session[1:]:
            assert x.citation.target == targets[x.assignment.weakness_id]


def test_a_warm_up_cites_the_highest_ranked_weakness_metric_it_targets() -> None:
    cited = CitedPlan(_plan(), all_citations(), rallies=13)
    assert {s[0].citation.target for s in cited.sessions} == {"AN-04"}  # rank 1, AN-04 warm-ups


def test_a_warm_up_with_no_weakness_metric_cites_its_first_citable_target() -> None:
    library = [warm_up("pb.test.serve-warm-up", targets=("AN-02", "AN-01")), drill("pb.test.dinks")]
    citations = {k: v for k, v in all_citations().items() if k != "AN-02"}
    cited = CitedPlan(_plan(library), citations, rallies=13)
    assert cited.sessions[0][0].citation.target == "AN-01"


def test_why_names_the_metric_and_its_value() -> None:
    assert cite("AN-05", 2, 7).why == "Serve faults: 29% of 7 serves"
    assert cite("AN-01", 4, 7).why == "Rallies won on serve: 57% of 7 serves"
    assert cite("AN-04", 2, 1).why == "Unforced errors per game: 2.0 over 1 game"
    assert cite("AN-04", 5, 2).why == "Unforced errors per game: 2.5 over 2 games"
    assert cite("AN-07:fault", 2, 10).why == "How rallies ended (faults): 20% of 10 rallies"
    assert cite("AN-05", 2, 7).value == Fraction(2, 7)


def test_at_most_ten_rallies_and_a_see_all_target_per_match() -> None:
    c = cite("AN-04", 14, 2, rallies=7, matches=("m1", "m2"))
    assert len(c.rally_ids) == 10
    assert c.rally_ids[:7] == tuple(("m1", f"m1-r{i}") for i in range(1, 8))
    assert c.rally_ids[7:] == (("m2", "m2-r1"), ("m2", "m2-r2"), ("m2", "m2-r3"))
    assert c.evidence == (("m1", "A", 7), ("m2", "A", 7))
    assert c.see_all == 14


def test_limited_data_when_the_top_weakness_metric_is_low_sample() -> None:
    cited = CitedPlan(_plan(), all_citations(low_top=True), rallies=13)
    assert cited.limited_data == LimitedData(rallies=13)
    assert cited.limited_data.text == "based on limited data from 13 rallies"


def test_no_limited_data_when_only_a_lower_weakness_is_low_sample() -> None:
    citations = all_citations()
    citations["AN-05"] = cite("AN-05", 2, 7, low_sample=True)
    assert CitedPlan(_plan(), citations, rallies=13).limited_data is None


def test_cited_content_carries_citations_and_is_deterministic() -> None:
    first = CitedPlan(_plan(), all_citations(low_top=True), rallies=13)
    again = CitedPlan(_plan(), all_citations(low_top=True), rallies=13)
    content = first.content()
    assert content["limited_data"] == {"rallies": 13}
    x = content["sessions"][0]["assignments"][1]
    assert set(x["citation"]) >= {"metric_id", "value", "n", "k", "rally_ids", "evidence"}
    assert x["why"]
    assert first.content_digest() == again.content_digest()
    assert first.content_digest() != CitedPlan(_plan(), all_citations(), 13).content_digest()
