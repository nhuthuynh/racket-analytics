"""The stats contract names every per-side field the product serves (PE-R2S3-04; ADR 0033 rule 2).

`docs/architecture/api-sprint-03.md` §2.1 says the per-side fields are "exactly starter_stats()
(ST-044) without the `rallies` lists". The FE (D-01) and the harness build against that table,
so a field the domain adds (fee4fa3: AN-06 `longest_by_game`) without a contract row has no
consumer and no automated comparison. This test reads the table and the domain output and fails
on any difference, in either direction. Negative case first: the parser refuses a table with a
metric missing, so an empty or moved table cannot pass by comparing nothing.
"""

from __future__ import annotations

import re

import pytest

from racket.analytics.starter_stats import METRICS, starter_stats
from tests.support.paths import REPO
from tests.unit.analytics.sheets import WORKED_EXAMPLE, one_game

pytestmark = [pytest.mark.unit]

CONTRACT = REPO / "docs" / "architecture" / "api-sprint-03.md"
ROW = re.compile(r"^\|\s*(AN-0\d(?:,\s*AN-0\d)*)\s*\|(.*)\|\s*$")


def contract_fields(text: str) -> dict[str, set[str]]:
    """Per-side fields per metric from the §2.1 table: the first backticked word of each item."""
    section = text.split("### 2.1", 1)[1].split("### 2.2", 1)[0]
    fields: dict[str, set[str]] = {}
    for line in section.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        names = {item.strip().split()[0].strip("`") for item in re.split(r",(?![^(]*\))", m[2])}
        for metric in re.findall(r"AN-0\d", m[1]):
            fields[metric] = names
    missing = set(METRICS) - set(fields)
    if missing:
        raise ValueError(f"api-sprint-03 §2.1 has no per-side row for {sorted(missing)}")
    return fields


def test_a_table_without_every_metric_is_refused() -> None:
    with pytest.raises(ValueError, match="AN-07"):
        contract_fields("### 2.1\n| AN-01, AN-02 | `k`, `n` |\n### 2.2\n")


def test_every_served_field_has_a_contract_row_and_nothing_else_does() -> None:
    documented = contract_fields(CONTRACT.read_text(encoding="utf-8"))
    served = starter_stats(one_game(WORKED_EXAMPLE))
    for metric in METRICS:
        for side in ("A", "B"):
            produced = set(served[metric][side]) - {"rallies"}  # rallies: the evidence route
            assert documented[metric] == produced, (metric, side)
