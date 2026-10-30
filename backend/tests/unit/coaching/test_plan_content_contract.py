"""QA-VERIFY04R3-07 (G04-11 c): the plan's content and digest, pinned (coaching-plan §6 step 5).

``content_digest`` is SHA-256 over the canonical JSON (sorted keys, no spaces, UTF-8) of the plan
without ids, version, clock, done state or reasons. The stored ``training_plans.content_digest``
and the ST-060 pass^3 check compare digests across processes and releases, so the field names,
the values and the canonical form are a contract: these tests state the expected content
literally and re-compute the digest independently (``_canonical_digest``), so any renamed key,
dropped field or changed serialisation fails here. Negative cases first.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

import pytest

from racket.coaching.plan.domain import (
    Citation,
    CitedAssignment,
    CitedPlan,
    DrillAssignment,
    MissingCitation,
    Session,
    TrainingPlan,
)
from tests.unit.coaching.citation_helpers import cite
from tests.unit.coaching.plan_helpers import TOP_3, solo_wall
from tests.unit.coaching.test_plan_follow_through import CITED, DRIVES, SERVE, WARM, plan

pytestmark = [pytest.mark.unit, pytest.mark.coaching]

AT = datetime(2026, 10, 18, 9, 30, tzinfo=UTC)

PREFERENCES = {
    "minutes_per_session": 30,
    "sessions_per_week": 3,
    "weekly_minutes": 90,  # the weekly total: 30 x 3 when no weekly cap is given
    "players_available": 1,
    "equipment": ["wall"],
    "level": "intermediate",
}
WEAKNESSES = [
    {"id": "unforced_errors", "target": "AN-04", "rank": 1},
    {"id": "serve_faults", "target": "AN-05", "rank": 2},
    {"id": "errors_under_pressure", "target": "AN-07:forced-error", "rank": 3},
]
ASSIGNMENTS = [
    {"position": 1, "drill": "pb.test.shadow-warm-up@1", "minutes": 10, "weakness_id": None},
    {
        "position": 2,
        "drill": "pb.test.wall-dinks@1",
        "minutes": 12,
        "weakness_id": "unforced_errors",
    },
    {"position": 3, "drill": "pb.test.serve-target@1", "minutes": 8, "weakness_id": "serve_faults"},
]


def _expected_content(library_version: str = "") -> dict[str, Any]:
    return {
        "library_version": library_version,
        "preferences": PREFERENCES,
        "weaknesses": WEAKNESSES,
        "unfitted": [{"weakness_id": "errors_under_pressure", "reason": "no_drill_fits"}],
        "sessions": [
            {"week": w, "index": i, "minutes_budget": 30, "assignments": ASSIGNMENTS}
            for w in (1, 2)
            for i in (1, 2, 3)
        ],
    }


def _canonical_digest(content: dict[str, Any]) -> str:
    """coaching-plan §6 step 5, written out independently of the aggregate."""
    blob = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ------------------------------------------------------------------ what the content leaves out
def test_done_state_reasons_and_version_are_not_content() -> None:
    p = plan()
    before = (p.content(), p.content_digest())
    p.mark_done(week=1, index=1, at=AT)
    assert p.version == 2
    assert (p.content(), p.content_digest()) == before


def test_a_different_library_version_is_a_different_digest() -> None:
    p, q = plan(), plan()
    q.library_version = "sha256:other"
    assert p.content_digest() != q.content_digest()
    assert q.content()["library_version"] == "sha256:other"


# ------------------------------------------------------------------ the pinned content
def test_the_plan_content_is_the_documented_shape() -> None:
    assert plan().content() == _expected_content()


def test_the_plan_digest_is_sha256_of_the_canonical_json() -> None:
    p = plan()
    p.library_version = "sha256:lib"
    assert p.content_digest() == _canonical_digest(_expected_content("sha256:lib"))


def test_a_swapped_drill_changes_the_content_and_the_digest() -> None:
    p = plan()
    before = p.content_digest()
    p.swap(week=1, index=1, position=2, library=[WARM, SERVE, DRIVES], cited=CITED)
    swapped = p.content()["sessions"][0]["assignments"][1]
    assert swapped == {
        "position": 2,
        "drill": "pb.test.a-wall-drives@1",
        "minutes": 12,
        "weakness_id": "unforced_errors",
    }
    assert p.content_digest() == _canonical_digest(p.content()) != before


# ------------------------------------------------------------------ citations
def test_a_citation_with_no_errors_is_a_citation() -> None:
    c = cite("AN-05", 0, 7, rallies=0)  # 0 of 7 serves faulted: k = 0 is a value, not a gap
    assert (c.k, c.n, c.metric_version) == (0, 7, "0.1")


def test_a_citation_content_is_the_documented_shape() -> None:
    c = cite("AN-05", 2, 7, matches=("m1", "m2"))
    assert c.content() == {
        "metric_id": "AN-05",
        "target": "AN-05",
        "metric_version": "0.1",
        "value": 0.2857,  # 2/7 to 4 places
        "n": 7,
        "k": 2,
        "low_sample": False,
        "rally_ids": [["m1", "m1-r1"], ["m1", "m1-r2"], ["m2", "m2-r1"], ["m2", "m2-r2"]],
        "evidence": [["m1", "A", 2], ["m2", "A", 2]],
    }


def test_an_assignment_without_a_citation_names_its_drill() -> None:
    x = DrillAssignment(position=2, drill=SERVE, minutes=8, weakness_id="serve_faults")
    with pytest.raises(MissingCitation) as no_citation:
        CitedAssignment(x, None)  # type: ignore[arg-type]
    assert no_citation.value.violations == ["QD-PL-04: pb.test.serve-target@1 has no citation"]
    with pytest.raises(MissingCitation) as wrong_target:
        CitedAssignment(x, cite("AN-04", 2, 1))
    assert wrong_target.value.violations == [
        "QD-PL-04: pb.test.serve-target@1 does not target AN-04"
    ]


def test_every_uncited_assignment_is_named_not_only_the_first() -> None:
    only_top = {"AN-04": cite("AN-04", 2, 1)}  # no AN-05 citation for the serve drills
    with pytest.raises(MissingCitation) as refused:
        CitedPlan(plan(), only_top, rallies=40)
    uncited = [v for v in refused.value.violations if "pb.test.serve-target@1" in v]
    assert len(uncited) == 6  # one per session, in every one of the 6 sessions


def test_a_plan_with_no_weakness_is_refused_for_its_missing_top_citation() -> None:
    warm_only = Session(
        week=1, index=1, minutes_budget=30, assignments=(DrillAssignment(1, WARM, 10, None),)
    )
    p = TrainingPlan(
        preferences=solo_wall(sessions=1),
        weaknesses=(),
        unfitted=(),
        sessions=(warm_only, Session(2, 1, 30, warm_only.assignments)),
    )
    with pytest.raises(MissingCitation) as refused:
        CitedPlan(p, {"AN-04": cite("AN-04", 2, 1)}, rallies=40)
    assert refused.value.violations == ["QD-PL-04: top weakness None has no citation"]


def test_the_cited_plan_content_and_digest_are_pinned() -> None:
    citations: dict[str, Citation] = {
        "AN-04": cite("AN-04", 2, 1),
        "AN-05": cite("AN-05", 2, 7),
    }
    cited = CitedPlan(plan(), citations, rallies=40)
    content = cited.content()
    expected = _expected_content()
    expected["limited_data"] = None
    rows = [
        {**ASSIGNMENTS[0], "citation": citations["AN-04"].content(), "why": citations["AN-04"].why},
        {**ASSIGNMENTS[1], "citation": citations["AN-04"].content(), "why": citations["AN-04"].why},
        {**ASSIGNMENTS[2], "citation": citations["AN-05"].content(), "why": citations["AN-05"].why},
    ]
    expected["sessions"] = [{**s, "assignments": rows} for s in expected["sessions"]]
    assert content == expected
    assert cited.content_digest() == _canonical_digest(expected)
    assert rows[2]["why"] == "Serve faults: 29% of 7 serves"


def test_a_low_sample_top_weakness_puts_the_rally_count_in_the_content() -> None:
    citations = {"AN-04": cite("AN-04", 2, 1, low_sample=True), "AN-05": cite("AN-05", 2, 7)}
    content = CitedPlan(plan(), citations, rallies=11).content()
    assert content["limited_data"] == {"rallies": 11}
    assert TOP_3[0].target == "AN-04"
