"""``pooled_low_sample`` (ST-057; FR-123; QD-PL-06; coaching-plan §4; ADR 0041, ADR 0005).

The plan's low-sample flag is the dictionary rule applied to the numbers pooled over the
player's matches, never a combination of each match's own flag. Negative cases first: matches
that are each low-sample but clear the rule together are not flagged, and matches that each
carry ``low_sample=False`` are flagged when the pooled numbers fail the rule. Thresholds are the
shipped dictionary's: n >= 20 for proportions, >= 2 games for AN-04, >= 10 service turns for
AN-03, interval width <= 0.30.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from racket.analytics.public import MetricFact, pooled_low_sample

pytestmark = [pytest.mark.unit]


def _fact(
    metric_id: str,
    k: int,
    n: int,
    *,
    low_sample: bool,
    counts: Mapping[str, int] | None = None,
    lower_bound: bool = False,
) -> MetricFact:
    return MetricFact(
        metric_id=metric_id,
        name=metric_id,
        version="1.0.0",
        k=k,
        n=n,
        counts=dict(counts or {}),
        low_sample=low_sample,
        lower_bound=lower_bound,
        rally_ids=(),
    )


# --- negative cases: the per-match flags are not the answer ---------------------------------


def test_an_04_one_game_per_match_is_not_low_sample_over_two_games() -> None:
    facts = [_fact("AN-04", 3, 1, low_sample=True), _fact("AN-04", 2, 1, low_sample=True)]
    assert not pooled_low_sample("AN-04", facts, 5)


def test_a_proportion_low_in_each_match_is_not_low_sample_when_pooled() -> None:
    # 2 of 15 and 2 of 15 are each under n = 20; 4 of 30 is width 0.244 <= 0.30.
    facts = [_fact("AN-01", 2, 15, low_sample=True), _fact("AN-01", 2, 15, low_sample=True)]
    assert not pooled_low_sample("AN-01", facts, 4)


def test_matches_flagged_not_low_are_low_sample_when_the_pooled_numbers_fail_the_rule() -> None:
    # The pooled 3 of 12 has n < 20, whatever each fact claims.
    facts = [_fact("AN-01", 2, 6, low_sample=False), _fact("AN-01", 1, 6, low_sample=False)]
    assert pooled_low_sample("AN-01", facts, 3)


def test_an_04_with_one_game_in_scope_is_low_sample() -> None:
    assert pooled_low_sample("AN-04", [_fact("AN-04", 4, 1, low_sample=False)], 4)


def test_an_03_uses_pooled_service_turns() -> None:
    low = [_fact("AN-03", 3, 4, low_sample=False), _fact("AN-03", 2, 5, low_sample=False)]
    enough = [_fact("AN-03", 3, 5, low_sample=True), _fact("AN-03", 2, 5, low_sample=True)]
    assert pooled_low_sample("AN-03", low, 5)
    assert not pooled_low_sample("AN-03", enough, 5)


def test_an_07_is_low_sample_when_any_pooled_share_interval_is_too_wide() -> None:
    # Pooled n = 30: the fault share 15 of 30 has width 0.337 > 0.30, though n >= 20.
    counts = {"fault": 8, "forced_error": 2, "winner": 5}
    other = {"fault": 7, "forced_error": 2, "winner": 6}
    facts = [
        _fact("AN-07", 0, 15, low_sample=False, counts=counts),
        _fact("AN-07", 0, 15, low_sample=False, counts=other),
    ]
    assert pooled_low_sample("AN-07", facts, 2)


def test_an_07_with_no_rally_in_scope_is_low_sample() -> None:
    assert pooled_low_sample("AN-07", [_fact("AN-07", 0, 0, low_sample=False)], 0)


def test_an_05_lower_bound_in_any_match_forces_the_flag() -> None:
    # 2 of 40 alone clears the rule (width 0.151); a fault without its type makes it a bound.
    clear = [_fact("AN-05", 1, 20, low_sample=False), _fact("AN-05", 1, 20, low_sample=False)]
    bound = [
        _fact("AN-05", 1, 20, low_sample=False),
        _fact("AN-05", 1, 20, low_sample=False, lower_bound=True),
    ]
    assert not pooled_low_sample("AN-05", clear, 2)
    assert pooled_low_sample("AN-05", bound, 2)


# --- positive cases --------------------------------------------------------------------------


def test_an_07_pooled_shares_each_within_the_width_rule_are_not_low_sample() -> None:
    # Each match carries low_sample=True; pooled n = 60: fault 10, forced 6, winner 44 of 60
    # are each within the 0.30 width rule.
    first = {"fault": 5, "forced_error": 3, "winner": 22}
    second = {"fault": 5, "forced_error": 3, "winner": 22}
    facts = [
        _fact("AN-07", 0, 30, low_sample=True, counts=first),
        _fact("AN-07", 0, 30, low_sample=True, counts=second),
    ]
    assert not pooled_low_sample("AN-07", facts, 6)
