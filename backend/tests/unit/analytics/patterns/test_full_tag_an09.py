"""AN-09 third-shot drop share from Full Tag labels (ST-171b; FR-171.R2, R3, R6).

``docs/domain/pattern-catalogue.md`` §0.1-§0.3 and §2 define it: the third shot is the serving
side's first hit after the return; drops / third shots with a ``trajectory``. A rally with fewer
than 3 hits, hits 1-3 that do not alternate, or a third shot with no facet is excluded with its
reason and counted in n_excluded, never as a drive; replays and rallies with no hit belong to
neither side. Negative cases first: a 2-hit rally must not count (red first, sprint-06 §3.7).
Table-driven; the Hypothesis properties are in ``test_full_tag_an09_properties.py``, the
catalogue's worked example and GS-PAT-1 in ``tests/integration/test_st_171b_an09_gs_pat_1.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.analytics.patterns.full_tag import (
    AGREEMENT_LABELS,
    UntranslatableLabels,
    full_tag_measures,
    read_rallies,
)
from racket.analytics.patterns.measure import InvalidMeasure, PatternMeasure
from racket.analytics.patterns.third_shot import AN09, third_shots
from racket.analytics.uncertainty import wilson
from racket.dataset import labels as published
from tests.unit.analytics.full_tag_docs import doc, rally
from tests.unit.analytics.full_tag_docs import third_shots as served

pytestmark = [pytest.mark.unit]


def _an09(labels: dict[str, Any], side: str = "A") -> PatternMeasure:
    return full_tag_measures(labels)[AN09][side]


# ------------------------------------------------- negative first: never counted as a drive
def test_a_two_hit_rally_is_excluded_never_counted_as_a_third_shot() -> None:
    m = _an09(doc(rally("r1", "A1", "B1")))
    assert (m.n, m.n_excluded, m.value) == (0, 1, None)
    assert m.exclusions == (("no_third_shot", 1),)


def test_a_third_shot_with_no_trajectory_is_excluded_as_facet_missing_never_a_drive() -> None:
    tally = third_shots(read_rallies(doc(*served("A", ["drive", None]))), "A")
    assert tally.mix == {"drive": ("r1",)}
    assert tally.excluded == {"facet_missing": ("r2",)}


def test_hits_that_do_not_alternate_are_excluded_and_never_counted_for_either_side() -> None:
    labels = doc(rally("r1", "A1", "B1", ("B2", "drive")))
    a, b = _an09(labels, "A"), _an09(labels, "B")
    assert a.exclusions == (("side_order_invalid", 1),)
    assert (a.n, b.n, b.n_excluded) == (0, 0, 0)


@pytest.mark.parametrize(
    ("rallies", "expected"),
    [
        ([rally("r1", "A1", "B1", ("A2", "drop"), ending="replay")], {"replay": ("r1",)}),
        ([rally("r1")], {"no_serve_hit": ("r1",)}),
        (
            [rally("r1", "A1", ending="replay"), rally("r2")],
            {"replay": ("r1",), "no_serve_hit": ("r2",)},
        ),
    ],
    ids=["replay", "no-hit", "both"],
)
def test_replays_and_hitless_rallies_belong_to_neither_side(
    rallies: list[dict[str, Any]], expected: dict[str, tuple[str, ...]]
) -> None:
    read = read_rallies(doc(*rallies))
    for side in ("A", "B"):
        tally = third_shots(read, side)
        assert (tally.n, tally.n_excluded) == (0, 0)
        assert tally.unassigned == expected


def test_a_rally_served_by_b_is_only_in_bs_universe() -> None:
    labels = doc(rally("r1", "B1", "A1", ("B2", "lob")))
    assert (_an09(labels, "A").n, _an09(labels, "B").n) == (0, 1)


# --------------------------------------------------------------- FR-171.R2, R3, R6 examples
@pytest.mark.parametrize(
    ("trajectories", "value", "n", "n_excluded", "low_sample"),
    [
        (["drop"] * 6 + ["drive"] * 4, 0.6, 10, 0, True),  # BA example R2 (happy)
        (["drop"] * 5 + ["drive"] * 20, 0.2, 25, 0, False),  # catalogue AN-09.1, rankable
        (["drop"] * 4 + ["drive"] * 4 + [None] * 2, 0.5, 8, 2, True),  # BA example R3
        (["dink", "lob", "drive"], 0.0, 3, 0, True),  # every other trajectory is not a drop
        (["drop"] * 19 + ["drive"], 0.95, 20, 0, False),  # min_n 20 is reached at 20
        (["drop"] * 19, 1.0, 19, 0, True),  # one below min_n (FR-171.R6)
    ],
    ids=["6-of-10", "5-of-25", "2-missing", "no-drop", "n-20", "n-19"],
)
def test_drop_share_value_n_interval_and_low_sample(
    trajectories: list[str | None], value: float, n: int, n_excluded: int, low_sample: bool
) -> None:
    m = _an09(doc(*served("A", trajectories)))
    k = trajectories.count("drop")
    assert m.value == pytest.approx(value)
    assert (m.n, m.n_excluded, m.low_sample) == (n, n_excluded, low_sample)
    assert m.interval == wilson(k, n)
    assert (m.interval_method, m.definition_version) == ("wilson", "0.1")
    assert m.rankable is not low_sample


def test_the_ba_example_interval_matches_the_catalogue_figure() -> None:
    m = _an09(doc(*served("A", ["drop"] * 6 + ["drive"] * 4)))
    assert m.interval is not None
    assert (round(m.interval.low, 3), round(m.interval.high, 3)) == (0.313, 0.832)


def test_no_counted_third_shot_has_no_value_and_no_interval_but_stays_available() -> None:
    m = _an09(doc(*served("A", [None, None])))
    assert (m.value, m.interval, m.n, m.n_excluded) == (None, None, 0, 2)
    assert (m.available, m.low_sample, m.rankable) == (True, True, False)


def test_exclusions_are_listed_by_reason_in_a_fixed_order() -> None:
    labels = doc(*served("A", [None]), rally("r2", "A1"), rally("r3", "A1", "B1", ("B2", "drop")))
    assert _an09(labels).exclusions == (
        ("facet_missing", 1), ("no_third_shot", 1), ("side_order_invalid", 1),
    )  # fmt: skip


def test_the_mix_holds_every_trajectory_of_the_counted_third_shots() -> None:
    read = read_rallies(doc(*served("B", ["lob", "drop", "dink", "drop"])))
    tally = third_shots(read, "B")
    assert tally.mix == {"lob": ("r1",), "drop": ("r2", "r4"), "dink": ("r3",)}
    assert (tally.k, tally.n) == (2, 4)


# ------------------------------------------------------- agreement (sprint-06 §10 risk row)
def test_a_single_labeller_trajectory_is_labelled_agreement_not_measured() -> None:
    m = _an09(doc(*served("A", ["drop"])))
    assert m.agreement == "not_measured"
    assert AGREEMENT_LABELS["not_measured"] == "single-labeller, agreement not measured"


def test_an_admitted_trajectory_facet_is_labelled_measured() -> None:
    labels = doc(*served("A", ["drop"]))
    m = full_tag_measures(labels, admitted_facets=frozenset({"trajectory"}))[AN09]["A"]
    assert m.agreement == "measured"
    other = full_tag_measures(labels, admitted_facets=frozenset({"intent"}))[AN09]["A"]
    assert other.agreement == "not_measured"


# ------------------------------------------------------------------ ACL: fail closed (R8 side)
def test_the_acl_vocabulary_equals_the_published_label_vocabulary() -> None:
    from racket.analytics.patterns import full_tag

    assert published.SHOT_FACETS["trajectory"] == full_tag.TRAJECTORIES
    assert full_tag.SIDES == published.SIDES
    assert full_tag.SLOTS == published.DOUBLES
    assert full_tag.LABEL_SCHEMA == published.LABEL_SCHEMA
    assert set(full_tag.ENDINGS) == set(published.ENDINGS)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(schema="full-tag-labels/v2"),
        lambda d: d.update(rallies="r1"),
        lambda d: d["rallies"][0].update(id=7),
        lambda d: d["rallies"][0].update(events=None),
        lambda d: d["rallies"][0]["events"][0].update(hitter="C1"),
        lambda d: d["rallies"][0]["events"][2].update(facets={"trajectory": "hybrid"}),
        lambda d: d["rallies"][0]["events"][2].update(facets=["drop"]),
        lambda d: d["rallies"][0].update(outcome={"ending": "let"}),
        lambda d: d["rallies"][0]["events"].append("hit"),
    ],
    ids=[
        "schema",
        "rallies",
        "rally-id",
        "events",
        "hitter",
        "trajectory",
        "facets",
        "ending",
        "event",
    ],
)
def test_a_document_the_acl_cannot_translate_is_refused(mutate: Any) -> None:
    labels = doc(*served("A", ["drop"]))
    mutate(labels)
    with pytest.raises(UntranslatableLabels):
        full_tag_measures(labels)


def test_bounce_events_and_other_facets_are_ignored() -> None:
    labels = doc(*served("A", ["drop"]))
    events = labels["rallies"][0]["events"]
    events.insert(1, {"type": "bounce", "frame": 15, "court_xy_m": [1.0, 2.0]})
    events[3]["facets"]["intent"] = "reset"
    assert (_an09(labels).value, _an09(labels).n) == (1.0, 1)


# ------------------------------------------------- PatternMeasure: exclusions and agreement
def _measure(**changes: Any) -> PatternMeasure:
    fields: dict[str, Any] = {"pattern_id": "AN-09", "value": 0.5, "n": 2, "interval": None,
                              "interval_method": "wilson", "low_sample": True,
                              "definition_version": "0.1", "n_excluded": 1,
                              "exclusions": (("facet_missing", 1),)}  # fmt: skip
    return PatternMeasure(**(fields | changes))


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"exclusions": (("facet_missing", 2),)}, "exclusions"),
        ({"exclusions": (("facet_missing", 0),), "n_excluded": 0}, "exclusions"),
        ({"exclusions": (("", 1),)}, "exclusions"),
        ({"exclusions": (("facet_missing", True),)}, "exclusions"),
        ({"exclusions": [("facet_missing", 1)]}, "exclusions"),
        ({"exclusions": (("a", 1), ("a", 0))}, "exclusions"),
        ({"agreement": "unknown"}, "agreement"),
    ],
    ids=["sum", "zero", "empty-reason", "bool", "list", "repeat", "agreement"],
)
def test_measure_refuses_inconsistent_exclusions_or_agreement(
    changes: dict[str, Any], match: str
) -> None:
    with pytest.raises(InvalidMeasure, match=match):
        _measure(**changes)


def test_a_measure_without_reasons_keeps_its_n_excluded() -> None:
    m = _measure(exclusions=(), n_excluded=3, agreement="measured")
    assert (m.n_excluded, m.exclusions, m.agreement) == (3, (), "measured")
    assert _measure().agreement is None
