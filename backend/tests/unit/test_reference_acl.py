"""Coaching's reference ACL (ST-170b; FR-170.R4, FR-170.R5; ADR 0061 "ACL read side", Rule 3.3).

Only ``coach-reviewed`` and ``verified`` entries cross into Coaching; an entry the ACL cannot
translate is dropped (fail closed), never guessed. Red first: a ``draft`` entry must not cross.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from racket.sports.references.loader import ReferenceEntry, ReferenceSet
from racket.sports.references.rules import Pattern
from tests.support.reference_api import ACL, LABELS

pytestmark = pytest.mark.unit

AN09 = Pattern("0.1", "inside_band", "wilson")
AN13 = Pattern("0.1", "higher", "order_statistic_median")
CATALOGUE = {"AN-09": AN09, "AN-13": AN13}
JUDGMENT = ReferenceEntry(
    id="REF-AN09-D-INT", pattern_id="AN-09", definition_version="0.1",
    better_direction="inside_band", level_band="intermediate", format="doubles",
    source_type="judgment", citation_id="SRC-0002", footage_id=None, status="coach-reviewed",
    version=1, band=(0.45, 0.7), value=None, n=None, k=None,
)  # fmt: skip


def _set(*entries: ReferenceEntry, version: int = 1) -> ReferenceSet:
    return ReferenceSet("pb-reference", version, entries)


def test_a_draft_entry_does_not_cross_the_acl() -> None:
    acl = ACL.load()
    assert acl.translate(replace(JUDGMENT, status="draft"), AN09) is None


@pytest.mark.parametrize("status", ["", "Coach-Reviewed", "published", "retired"])
def test_an_unknown_status_does_not_cross_the_acl(status: str) -> None:
    assert ACL.load().translate(replace(JUDGMENT, status=status), AN09) is None


@pytest.mark.parametrize("status", ["coach-reviewed", "verified"])
def test_a_judgment_entry_crosses_with_its_band_as_its_interval(status: str) -> None:
    value = ACL.load().translate(replace(JUDGMENT, status=status), AN09)
    assert value is not None
    assert value.status == status
    assert value.band == (0.45, 0.7)
    assert value.interval == (0.45, 0.7)
    assert value.interval_method == "wilson"
    assert value.n is None
    assert value.provenance_label == LABELS["judgment"]
    assert (value.id, value.version, value.citation_id) == ("REF-AN09-D-INT", 1, "SRC-0002")


def test_a_published_wilson_entry_gets_the_interval_computed_from_k_and_n() -> None:
    published = replace(JUDGMENT, source_type="published", value=0.55, n=40, k=22)
    value = ACL.load().translate(published, AN09)
    assert value is not None
    assert value.provenance_label == LABELS["published"]
    assert value.interval is not None
    low, high = value.interval
    assert low == pytest.approx(0.3983, abs=1e-4)
    assert high == pytest.approx(0.6929, abs=1e-4)
    assert (value.value, value.n, value.k) == (0.55, 40, 22)


def test_a_published_median_entry_without_a_stored_interval_is_dropped() -> None:
    median = replace(
        JUDGMENT, pattern_id="AN-13", source_type="published", band=None, value=6.0, n=30
    )
    assert ACL.load().translate(median, AN13) is None


def test_a_measured_entry_crosses_without_its_footage_id() -> None:
    measured = replace(
        JUDGMENT, source_type="measured", citation_id=None, footage_id="FT-0001",
        value=0.55, n=40, k=22,
    )  # fmt: skip
    value = ACL.load().translate(measured, AN09)
    assert value is not None
    assert value.provenance_label == LABELS["measured"]
    assert value.citation_id is None
    assert not hasattr(value, "footage_id")


def test_an_unknown_source_type_is_dropped() -> None:
    assert ACL.load().translate(replace(JUDGMENT, source_type="pro"), AN09) is None


def test_readable_keeps_reviewed_and_verified_entries_sorted_and_drops_the_rest() -> None:
    entries = (
        replace(JUDGMENT, id="REF-AN13-D-INT", pattern_id="AN-13", band=(4.0, 8.0)),
        replace(JUDGMENT, id="REF-AN09-D-BEG", level_band="beginner", status="draft"),
        replace(JUDGMENT, id="REF-AN09-D-ADV", level_band="advanced", status="verified"),
        JUDGMENT,
        replace(JUDGMENT, id="REF-AN99-D-INT", pattern_id="AN-99"),  # not in the catalogue
    )
    values = ACL.load().readable(_set(*entries), CATALOGUE)
    assert [v.id for v in values] == ["REF-AN09-D-ADV", "REF-AN09-D-INT", "REF-AN13-D-INT"]


def test_current_is_the_highest_version_of_the_one_set() -> None:
    acl = ACL.load()
    v1, v2 = _set(JUDGMENT), _set(replace(JUDGMENT, version=2), version=2)
    assert acl.current((v2, v1)) == v2
    assert acl.current(()) is None


def test_two_set_names_have_no_current_set() -> None:
    acl = ACL.load()
    other = ReferenceSet("other-reference", 3, (JUDGMENT,))
    assert acl.current((_set(JUDGMENT), other)) is None
