"""ST-049 integration (NFR-004, QD-GD-03): a golden match of GS-AN-1 v1 tagged and corrected
through the real API into Postgres. The sheet read back (GET .../sheet) is what
``racket.analytics`` reads; its starter stats equal the frozen values of the set exactly, per
metric and side, and equal the stats of the in-memory projection the regression uses.

gm3 is the match whose path through storage matters most: two corrections (an ending, then a
winner that ends the game at rally 19) and four rallies kept as "needs your decision".
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.analytics.starter_stats import starter_stats
from tests.regression.test_golden_an import (
    METRICS,
    differences,
    expected,
    product_stats,
    script,
)
from tests.support import scorebook as sb
from tests.support.api import ApiDriver

pytestmark = [pytest.mark.golden_an, pytest.mark.analytics]

GM3 = "gm3-corrections-needs-decision"


def _stored_stats(api: ApiDriver, match: str, *, with_corrections: bool) -> Any:
    s = script(match)
    (game,) = s["games"]
    match_id = sb.ready_tagged_match(api, "ivy", game["tags"], title=f"ST-049 {match}")
    ivy = api.as_user("ivy")
    if with_corrections:
        for c in s["corrections"]:
            rally_id = sb.sheet_body(api, "ivy", match_id)["rows"][c["rally"] - 1]["rally_id"]
            version = api.run(sb.version_of(ivy, match_id))
            response = api.run(
                sb.command(ivy, "correct", version=version,
                           body={"field": c["field"], "value": c["value"]},
                           match_id=match_id, rally_id=rally_id)
            )  # fmt: skip
            assert response.status_code == 200, response.text
    return starter_stats(sb.sheet_body(api, "ivy", match_id))


def _found(match: str, got: Any) -> list[str]:
    want = expected(match)["metrics"]
    return [d for m in METRICS for d in differences(match, m, want[m], got[m])]


def test_st_049_a_stored_golden_match_without_its_corrections_differs(api: ApiDriver) -> None:
    """Negative first: the stored path is not trivially equal; leaving out the two corrections
    is reported naming the match, a metric and a side."""
    found = _found(GM3, _stored_stats(api, GM3, with_corrections=False))
    assert found, "a stored match without its corrections went unnoticed"
    assert all(d.startswith(f"GS-AN-1 {GM3} AN-") and " side " in d for d in found), found


def test_st_049_the_stored_corrected_golden_match_equals_gs_an_1(api: ApiDriver) -> None:
    stats = _stored_stats(api, GM3, with_corrections=True)
    found = _found(GM3, stats)
    assert not found, "\n".join(found)
    assert stats == product_stats(script(GM3))
