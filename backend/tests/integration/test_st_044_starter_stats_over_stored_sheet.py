"""ST-044 integration (FR-100, NFR-004): starter stats over a sheet stored and projected by the
real stack. The worked example of metric-dictionary §2 is tagged through the API into
Postgres; the sheet read back (GET .../sheet) is what ``racket.analytics`` reads, and the stats
equal the coach's hand count and the stats of the in-memory projection.
"""

from __future__ import annotations

from typing import Any

from racket.analytics.starter_stats import starter_stats
from tests.support import scorebook as sb
from tests.support.api import ApiDriver
from tests.unit.analytics.sheets import WORKED_EXAMPLE, one_game, tag


def _stored_stats(api: ApiDriver, tags: list[dict[str, Any]] | None, title: str) -> Any:
    if tags is None:
        client = api.as_user("ivy")
        match_id = api.run(sb.create_doubles(client, title))
    else:
        match_id = sb.ready_tagged_match(api, "ivy", tags, title=title)
    return starter_stats(sb.sheet_body(api, "ivy", match_id))


def test_st_044_a_stored_match_without_a_game_has_no_values(api: ApiDriver) -> None:
    stats = _stored_stats(api, None, "ST-044 empty")
    for side in ("A", "B"):
        got = stats["AN-01"][side]
        assert (got["n"], got["value"], got["low_sample"]) == (0, None, True)
        assert stats["AN-04"][side]["games"] == 0


def test_st_044_the_stored_worked_example_matches_the_hand_count(api: ApiDriver) -> None:
    stats = _stored_stats(api, sb.taglib.with_times(WORKED_EXAMPLE), "ST-044 worked example")
    an01, an02 = stats["AN-01"]["A"], stats["AN-02"]["A"]
    assert (an01["k"], an01["n"], an01["ci_low"], an01["ci_high"]) == (4, 7, 0.2505, 0.8418)
    assert (an02["k"], an02["n"]) == (2, 6)
    assert stats["AN-04"]["B"]["player_not_tagged"] == 1
    assert all(8 not in f["rallies"] for sides in stats.values() for f in sides.values())
    assert stats == starter_stats(one_game(WORKED_EXAMPLE))


def test_st_044_stored_wide_mix_flags_an_07_and_reports_runs_per_game(api: ApiDriver) -> None:
    # PE-R1-ST044-01/02, SQA-R1-01: A ends 24 rallies (12 winners, 12 unforced errors); n passes
    # min_sample but every share's interval is wider than 30 points (rule 0.3, FR-101).
    wide_mix = [tag("A", "winner"), tag("B", "unforced_error")] * 12
    stats = _stored_stats(api, sb.taglib.with_times(wide_mix), "ST-044 wide mix")
    an07 = stats["AN-07"]["A"]
    assert (an07["n"], an07["low_sample"]) == (24, True)
    assert stats["AN-06"]["A"]["longest_by_game"] == [1]
    assert stats["AN-06"]["B"]["longest_by_game"] == [1]
    assert stats == starter_stats(one_game(wide_mix))
