"""Unit tests of the reference-set rules (ST-170a; FR-170.R1, R3; ADR 0061 Rules 1 and 3.3).

One test per refusal, negative case first (testing-strategy §2). The rules are pure: the pattern
catalogue, the sources register and the footage provenance records are passed in as values.
Written red first: before ST-170a an entry with no source passes because nothing checks it.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.support.references import RULES, entry, reference_doc

pytestmark = pytest.mark.unit

FILE = "pb-reference/v1.json"


def _catalogue() -> dict[str, Any]:
    rules = RULES.load()
    return {
        "AN-09": rules.Pattern("0.1", "inside_band", "wilson"),
        "AN-13": rules.Pattern("0.1", "higher", "order_statistic_median"),
        "AN-10": rules.Pattern("0.1", "higher", "wilson"),
    }


def _sources() -> dict[str, Any]:
    rules = RULES.load()
    return {
        "SRC-0002": rules.Source("definition", "resolved"),
        "SRC-0012": rules.Source("statistic", "unresolved"),
        "SRC-0100": rules.Source("statistic", "resolved"),
    }


def _problems(
    entries: list[dict[str, Any]],
    footage: dict[str, Any] | None = None,
    name: str = FILE,
    doc: Any = None,
) -> list[tuple[str, str, str]]:
    rules = RULES.load()
    found = rules.lint_set(
        name, doc if doc is not None else reference_doc(entries), _catalogue(), _sources(),
        footage or {},
    )  # fmt: skip
    return [(p.entry, p.field, p.reason) for p in found]


def _fields(problems: list[tuple[str, str, str]]) -> set[str]:
    return {field for _, field, _ in problems}


def _published(**changes: Any) -> dict[str, Any]:
    made = entry(
        pattern_id="AN-10", better_direction="higher", band=None, source_type="published",
        source={"citation_id": "SRC-0100"}, value=0.6, n=40, k=24,
    )  # fmt: skip
    for key, value in changes.items():
        if value is None:
            made.pop(key, None)
        else:
            made[key] = value
    return made


# ---------------------------------------------------------------- FR-170.R1 required fields


@pytest.mark.parametrize(
    "field",
    ["id", "pattern_id", "definition_version", "better_direction", "level_band", "format",
     "source_type", "source", "band", "status", "version"],
)  # fmt: skip
def test_a_missing_field_is_refused_naming_the_entry_and_the_field(field: str) -> None:
    doc = reference_doc([entry()])
    del doc["entries"][0][field]

    problems = _problems([], doc=doc)

    assert any(f == field and "missing field" in r for _, f, r in problems), problems


def test_a_complete_judgment_entry_passes() -> None:
    assert _problems([entry()]) == []


def test_an_unresolved_citation_is_refused() -> None:
    problems = _problems([entry(source={"citation_id": "SRC-9999"})])

    assert ("REF-AN09-D-INT", "source", "unresolved citation SRC-9999") in problems


def test_a_published_value_needs_a_resolved_statistic_row() -> None:
    problems = _problems([_published(source={"citation_id": "SRC-0012"})])

    assert ("REF-AN09-D-INT", "source", "SRC-0012 cannot back a published value") in problems
    assert _problems([_published()]) == []


def test_a_published_entry_with_no_n_is_refused() -> None:
    assert ("REF-AN09-D-INT", "n", "missing field") in _problems([_published(n=None)])


def test_a_published_proportion_with_no_k_or_a_value_that_is_not_k_over_n_is_refused() -> None:
    assert "k" in _fields(_problems([_published(k=None)]))
    assert "value" in _fields(_problems([_published(value=0.7)]))
    assert "k" in _fields(_problems([_published(k=41)]))


def test_a_published_median_needs_an_interval_around_its_value() -> None:
    median = _published(pattern_id="AN-13", value=6, n=12, k=None, interval=[4, 8])
    assert _problems([median]) == []
    assert "interval" in _fields(_problems([{**median, "interval": [7, 9]}]))
    assert "interval" in _fields(_problems([{k: v for k, v in median.items() if k != "interval"}]))


def test_a_judgment_entry_carries_no_n() -> None:
    assert ("REF-AN09-D-INT", "n", "judgment entries carry a band and no n") in _problems(
        [entry(n=20)]
    )


def test_better_direction_must_equal_the_catalogue() -> None:
    problems = _problems([entry(better_direction="higher")])

    assert any(
        f == "better_direction" and "differs from the catalogue" in r for _, f, r in problems
    )


def test_an_unknown_pattern_or_definition_version_is_refused() -> None:
    assert "pattern_id" in _fields(_problems([entry(pattern_id="AN-99")]))
    assert "definition_version" in _fields(_problems([entry(definition_version="0.2")]))


def test_inside_band_needs_a_band_not_a_point_value() -> None:
    problems = _problems([entry(band=None, value=0.55)])

    assert ("REF-AN09-D-INT", "band", "missing field (required for inside_band)") in problems


@pytest.mark.parametrize("band", [[0.7, 0.45], [0.45], ["a", "b"], [0.45, 1.2], "0.45-0.70"])
def test_a_malformed_band_is_refused(band: Any) -> None:
    assert "band" in _fields(_problems([entry(band=band)]))


@pytest.mark.parametrize(
    ("field", "value"),
    [("status", "approved"), ("format", "mixed"), ("source_type", "pro"),
     ("level_band", "3.5"), ("id", ""), ("version", "1")],
)  # fmt: skip
def test_a_value_outside_its_vocabulary_is_refused(field: str, value: Any) -> None:
    assert field in _fields(_problems([entry(**{field: value})]))


def test_a_judgment_value_may_not_claim_pro_play() -> None:
    assert "level_band" in _fields(_problems([entry(level_band="pro")]))


# ---------------------------------------------------------------- FR-170.R3 measured entries


def _measured(fid: str = "FTG-0001") -> dict[str, Any]:
    return entry(
        source_type="measured", source={"footage_id": fid, "rights_record_id": "RR-0001"},
        value=0.55, n=40, k=22,
    )  # fmt: skip


def test_a_measured_entry_without_a_provenance_record_is_refused() -> None:
    problems = _problems([_measured()])

    assert (
        "REF-AN09-D-INT", "source", "footage FTG-0001 does not permit reference-library"
    ) in problems  # fmt: skip


def test_a_measured_entry_on_footage_permitting_only_analysis_is_refused() -> None:
    rules = RULES.load()
    footage = {"FTG-0001": rules.Footage("RR-0001", frozenset({"analysis"}))}

    problems = _problems([_measured()], footage)

    assert any("FTG-0001" in r and "reference-library" in r for _, _, r in problems)


def test_a_measured_entry_whose_rights_record_differs_is_refused() -> None:
    rules = RULES.load()
    footage = {"FTG-0001": rules.Footage("RR-0002", frozenset({"reference-library"}))}

    assert "source" in _fields(_problems([_measured()], footage))


def test_a_measured_entry_on_footage_permitting_reference_library_passes() -> None:
    rules = RULES.load()
    footage = {"FTG-0001": rules.Footage("RR-0001", frozenset({"analysis", "reference-library"}))}

    assert _problems([_measured()], footage) == []


def test_a_measured_entry_without_footage_or_rights_record_is_refused() -> None:
    assert "source" in _fields(_problems([entry(source_type="measured", value=0.55, n=40, k=22)]))


# ---------------------------------------------------------------- set shape and duplicates


def test_a_duplicate_pattern_band_format_version_is_refused() -> None:
    problems = _problems([entry(), entry(id="REF-AN09-D-INT-2", band=[0.4, 0.6])])

    assert ("REF-AN09-D-INT-2", "entry", "duplicate entry (AN-09, intermediate, doubles, v1)") in (
        problems
    )


def test_a_duplicate_entry_id_is_refused() -> None:
    problems = _problems([entry(), entry(format="singles")])

    assert ("REF-AN09-D-INT", "id", "duplicate id") in problems


def test_an_entry_version_other_than_the_set_version_is_refused() -> None:
    assert "version" in _fields(_problems([entry(version=2)]))


@pytest.mark.parametrize("name", ["pb-reference/v01.json", "pb-reference/one.json", "v1.json"])
def test_a_file_not_named_set_slash_v_n_is_refused(name: str) -> None:
    assert "file" in _fields(_problems([entry()], name=name))


def test_a_set_whose_name_or_version_differs_from_its_path_is_refused() -> None:
    assert "set" in _fields(_problems([], doc={**reference_doc([entry()]), "set": "other"}))
    assert "version" in _fields(_problems([], doc={**reference_doc([entry()]), "version": 2}))


@pytest.mark.parametrize("doc", [[], "x", {"set": "pb-reference", "version": 1}])
def test_a_document_that_is_not_a_reference_set_is_refused(doc: Any) -> None:
    assert _problems([], doc=doc) != []


def test_problem_text_names_file_entry_field_and_reason() -> None:
    rules = RULES.load()
    (problem,) = rules.lint_set(
        FILE, reference_doc([entry(source=None)]), _catalogue(), _sources(), {}
    )

    assert str(problem) == f"FAIL {FILE}: REF-AN09-D-INT: source: missing field"
