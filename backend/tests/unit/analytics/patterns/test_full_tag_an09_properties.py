"""AN-09 properties over generated Full Tag documents (ST-171b; FR-171.R2, R3; catalogue §0.2).

"counted + excluded = all": per side, counted + excluded = the side's served rallies, and over
the match universe(A) + universe(B) + unassigned = all rallies; a rally is in one bucket only.
A rally with fewer than 3 hits, or a third shot with no facet, is never counted (never a drive).
Hypothesis runs the default profile in the domain suite and the ``ci`` profile (>= 1,000
examples) in CI's serial property step.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.analytics.patterns.full_tag import full_tag_measures, read_rallies
from racket.analytics.patterns.third_shot import AN09, third_shots
from tests.unit.analytics.full_tag_docs import doc, rally

pytestmark = [pytest.mark.unit]

SLOTS = ("A1", "A2", "B1", "B2")
TRAJECTORY = st.sampled_from([None, "drive", "drop", "dink", "lob"])
HIT = st.tuples(st.sampled_from(SLOTS), TRAJECTORY).map(lambda h: h[0] if h[1] is None else h)
ENDING = st.sampled_from(["winner", "unforced_error", "forced_error", "fault", "replay"])


@st.composite
def documents(draw: Any) -> dict[str, Any]:
    count = draw(st.integers(min_value=0, max_value=12))
    return doc(*(
        rally(f"r{i}", *draw(st.lists(HIT, max_size=6)), ending=draw(ENDING))
        for i in range(count)
    ))  # fmt: skip


def _ids(buckets: Mapping[str, tuple[str, ...]]) -> list[str]:
    return [rid for ids in buckets.values() for rid in ids]


@given(documents())
def test_every_rally_is_in_exactly_one_bucket(labels: dict[str, Any]) -> None:
    read = read_rallies(labels)
    a, b = third_shots(read, "A"), third_shots(read, "B")
    assert a.unassigned == b.unassigned
    placed = _ids(a.mix) + _ids(a.excluded) + _ids(b.mix) + _ids(b.excluded) + _ids(a.unassigned)
    assert sorted(placed) == sorted(r["id"] for r in labels["rallies"])


@given(documents())
def test_counted_plus_excluded_is_the_sides_served_rallies(labels: dict[str, Any]) -> None:
    measures = full_tag_measures(labels)[AN09]
    for side in ("A", "B"):
        served = [
            r for r in labels["rallies"]
            if r["outcome"]["ending"] != "replay" and r["events"]
            and r["events"][0]["hitter"][0] == side
        ]  # fmt: skip
        m = measures[side]
        assert m.n + m.n_excluded == len(served)
        assert sum(count for _, count in m.exclusions) == m.n_excluded
        if m.n:
            assert m.value == third_shots(read_rallies(labels), side).k / m.n
        else:
            assert m.value is None


@given(documents())
def test_a_short_rally_or_a_missing_facet_is_never_counted(labels: dict[str, Any]) -> None:
    read = read_rallies(labels)
    for side in ("A", "B"):
        counted = set(_ids(third_shots(read, side).mix))
        for r in labels["rallies"]:
            hits = r["events"]
            if len(hits) < 3 or "facets" not in hits[2]:
                assert r["id"] not in counted


@given(documents(), st.data())
def test_removing_a_counted_facet_moves_one_rally_from_n_to_n_excluded(
    labels: dict[str, Any], data: st.DataObject
) -> None:
    before = full_tag_measures(labels)[AN09]
    read = read_rallies(labels)
    counted = [(s, rid) for s in ("A", "B") for rid in _ids(third_shots(read, s).mix)]
    if not counted:
        return
    side, rid = data.draw(st.sampled_from(counted))
    target = next(r for r in labels["rallies"] if r["id"] == rid)
    del target["events"][2]["facets"]
    after = full_tag_measures(labels)[AN09][side]
    assert (after.n, after.n_excluded) == (before[side].n - 1, before[side].n_excluded + 1)
