"""`scripts/measure/planlib.py` (QA-HARNESS-4a): the independent reference behind G04-01..G04-03.

Refusals first: an empty or broken plan never grades clean (fail closed, ADR 0014). The ranking
is pinned to the COACH-4 worked examples, read verbatim from weakness-catalogue.md §7: a catalogue
change fails these tests until planlib and they change with a TCR row.
"""

from __future__ import annotations

import plan_fixtures as pf
import pytest
from conftest import REPO_ROOT

pytestmark = pytest.mark.unit
pl = pf.load("planlib")
CATALOGUE = (REPO_ROOT / "docs" / "domain" / "weakness-catalogue.md").read_text(encoding="utf-8")
ROWS = pl.catalogue_rows(CATALOGUE)
EXAMPLES = [("FR-120", "Ivy")] + [(e, s) for e in ("dict §2", "gm1", "gm2", "gm3") for s in "AB"]


def _set(path: tuple, value):
    def apply(p: dict) -> None:
        *head, last = path
        target = p
        for key in head:
            target = target[key]
        target[last] = value

    return apply


def test_a_plan_with_nothing_in_it_fails_closed() -> None:
    assert pl.grade({}, pf.library()) == ["plan: preferences missing or malformed"]


A0 = ("sessions", 0, "assignments")
BROKEN = [
    (_set(("sessions",), []), "plan: 0 sessions, expected 6"),
    (_set((*A0, 1, "drill", "id"), "pb.test.gone"), "QD-PL-02: week 1 session 1 #2"),
    (_set((*A0, 1, "minutes"), 4), "QD-PL-01: week 1 session 1 #2 pb.test.a@1: 4 min"),
    (_set(("preferences", "weekly_minutes"), 60), "QD-PL-01: week 1: 90 min, weekly 60"),
    (_set(("preferences", "level"), "expert"), "plan: preferences missing or malformed"),
    (_set((*A0, 0, "minutes"), 11), "QD-PL-03: week 1 session 1 #1 pb.test.warm@1: warm-up"),
    (_set((*A0, 1, "citation", "n"), 0), "QD-PL-04: week 1 session 1 #2 pb.test.a@1: citation"),
    (_set((*A0, 2, "citation", "metric_id"), "AN-05"), "QD-PL-04: week 1 session 1 #3"),
]


@pytest.mark.parametrize(("breaks", "names"), BROKEN)
def test_a_broken_plan_names_its_rule(breaks, names: str) -> None:
    plan = pf.plan()
    breaks(plan)
    assert any(p.startswith(names) for p in pl.grade(plan, pf.library())), names


def test_a_plan_keeping_every_rule_grades_clean() -> None:
    assert pl.grade(pf.plan(), pf.library()) == []


def test_a_cited_value_or_rally_the_stats_do_not_show_is_named() -> None:
    plan, ev = pf.plan(), {m: {f"r{x}" for x in pf.REF[m]["A"]["rallies"]} for m in pf.REF}
    stats = pf.s.as_api_shape(pf.REF)
    assert pl.citation_problems(plan, stats, "A", ev, pf.library()) == []
    plan["sessions"][0]["assignments"][1]["citation"]["value"] = 0.99
    plan["sessions"][1]["assignments"][2]["citation"]["rally_ids"] = ["r99"]
    got = pl.citation_problems(plan, stats, "A", ev, pf.library())
    assert [p.split(" (")[0] for p in got] == [
        "QD-PL-04: s0a2 AN-02 0.99 n=6 is not GET stats",
        "QD-PL-04: s1a3 AN-04 rally r99 is not in GET evidence",
    ]


def test_no_games_is_an_empty_ranking_not_an_error() -> None:
    assert pl.rank_facts([], 0)["weaknesses"] == []


def test_the_catalogue_holds_exactly_the_nine_worked_examples() -> None:
    assert sorted(ROWS) == sorted(EXAMPLES)


@pytest.mark.parametrize(("example", "side"), EXAMPLES)
def test_ranking_equals_the_coach_worked_example(example: str, side: str) -> None:
    got = {(e, s): row for e, s, row in pl.worked_examples(REPO_ROOT)}
    assert got[(example, side)] == ROWS[(example, side)]


def test_a_wrong_order_or_missing_side_out_mark_is_named() -> None:
    want = pl.ranking([{"first_serving_side": "A", "tags": pf.s.STATS_TAGS}], "A")
    assert [w["id"] for w in want["weaknesses"]][:2] == ["opponent_winners", "unforced_errors"]
    assert (want["games"], want["rallies"]) == (1, 13)
    got = want | {"weaknesses": want["weaknesses"][::-1], "side_out_verified": None}
    assert [p.split(":")[0] for p in pl.ranking_problems(want, got)] == [
        "ranking side_out_verified",
        "ranking order",
    ]
