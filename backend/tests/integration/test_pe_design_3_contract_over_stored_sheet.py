"""PE-DESIGN-3 integration (PE-R2S3-04; ADR 0033 rule 2): the api-sprint-03 §2.1 per-side field
table equals the fields of the starter stats computed over a score sheet stored in Postgres and
read back through the API (GET .../sheet), the input the stats route (ST-046) will read. A match
with no game must still serve every documented field (values null, n = 0), so the contract has
no field that only exists once rallies are tagged. Negative case first.
"""

from __future__ import annotations

from typing import Any

from racket.analytics.starter_stats import METRICS, starter_stats
from tests.support import scorebook as sb
from tests.support.api import ApiDriver
from tests.unit.analytics.sheets import WORKED_EXAMPLE
from tests.unit.analytics.test_stats_contract_doc import CONTRACT, contract_fields


def _served_fields(stats: dict[str, Any]) -> dict[str, dict[str, set[str]]]:
    return {m: {s: set(stats[m][s]) - {"rallies"} for s in ("A", "B")} for m in METRICS}


def test_pe_design_3_a_stored_match_without_a_game_serves_every_documented_field(
    api: ApiDriver,
) -> None:
    documented = contract_fields(CONTRACT.read_text(encoding="utf-8"))
    match_id = api.run(sb.create_doubles(api.as_user("ivy"), "PE-DESIGN-3 empty"))
    served = _served_fields(starter_stats(sb.sheet_body(api, "ivy", match_id)))
    for metric in METRICS:
        assert served[metric] == {"A": documented[metric], "B": documented[metric]}, metric


def test_pe_design_3_the_stored_worked_example_serves_exactly_the_contract_fields(
    api: ApiDriver,
) -> None:
    documented = contract_fields(CONTRACT.read_text(encoding="utf-8"))
    tags = sb.taglib.with_times(WORKED_EXAMPLE)
    match_id = sb.ready_tagged_match(api, "ivy", tags, title="PE-DESIGN-3 worked example")
    served = _served_fields(starter_stats(sb.sheet_body(api, "ivy", match_id)))
    for metric in METRICS:
        assert served[metric] == {"A": documented[metric], "B": documented[metric]}, metric
    assert "longest_by_game" in served["AN-06"]["A"]
