"""Unit tests of the catalogue and sources parsers of the reference loader (ST-170a; FR-170.R1).

The pattern catalogue (`docs/domain/pattern-catalogue.md` §1) gives ``better_direction`` and
``interval_method`` per pattern; its §0.8 gives the definition version. The sources register
(`docs/domain/sources.md` §2) gives the claim kind and resolve status per ``SRC-nnnn`` row.
Pure text in, values out. A catalogue the parser cannot read fails closed (raises).
"""

from __future__ import annotations

import pytest

from tests.support.references import CATALOGUE, LOADER, RULES, SOURCES

pytestmark = pytest.mark.unit

CATALOGUE_TEXT = """\
Each entry has `definition_version` (0.1 here). Any change bumps it.

## 1. Summary

| Pattern | Name | Value | Data source | min_n | interval_method | better_direction | Sprint 6 |
|---|---|---|---|---|---|---|---|
| AN-09 | Third-shot drop share | drops | FT | 20 | wilson | inside_band | ST-171b (P0) |
| AN-13 | Dink tolerance | median | FT | 10 | order_statistic_median | higher | ST-171c (P0) |
| STACK | Stacking | share | CV | 20 | wilson | none (descriptive) | needs CV (7.1) |

## 2. AN-09 third-shot drop share

| AN-10 | not a summary row | x | FT | 20 | wilson | higher | x |
"""


def test_a_catalogue_without_a_definition_version_fails_closed() -> None:
    loader = LOADER.load()

    with pytest.raises(loader.CatalogueError):
        loader.parse_catalogue(CATALOGUE_TEXT.replace("(0.1 here)", ""))


def test_a_catalogue_without_a_summary_table_fails_closed() -> None:
    loader = LOADER.load()

    with pytest.raises(loader.CatalogueError):
        loader.parse_catalogue("Each entry has `definition_version` (0.1 here).\n")


def test_the_catalogue_summary_gives_direction_and_method_per_ranked_pattern() -> None:
    rules = RULES.load()

    parsed = LOADER.load().parse_catalogue(CATALOGUE_TEXT)

    assert parsed == {
        "AN-09": rules.Pattern("0.1", "inside_band", "wilson"),
        "AN-13": rules.Pattern("0.1", "higher", "order_statistic_median"),
    }


def test_the_repository_catalogue_parses() -> None:
    parsed = LOADER.load().parse_catalogue(CATALOGUE.read_text(encoding="utf-8"))

    assert parsed["AN-09"].better_direction == "inside_band"
    assert parsed["AN-13"].interval_method == "order_statistic_median"
    assert "STACK" not in parsed


def test_the_sources_register_gives_kind_and_status_per_row() -> None:
    rules = RULES.load()

    parsed = LOADER.load().parse_sources(SOURCES.read_text(encoding="utf-8"))

    assert parsed["SRC-0002"] == rules.Source("definition", "resolved")
    assert parsed["SRC-0012"] == rules.Source("statistic", "unresolved")
    assert "SRC-9999" not in parsed
