"""Unit tests for scripts/measure/unofficial_notice.py (FIX-03-2c, PD-R1S3-01-PM; DR-03 R3-3 a).

Negative cases first: the pre-fix plan line ("every metric card") is reported, a missing line is
refused rather than passed, and a dictionary that drops "before the first card" is reported.
"""

from __future__ import annotations

import pytest
from unofficial_notice_fixtures import NEW_WORDS, OLD_WORDS, dictionary, load, plan

pytestmark = pytest.mark.unit

ok_dictionary = dictionary("once, before the first card")


def test_plan_promising_every_metric_card_is_reported() -> None:
    problems = load().check(plan(OLD_WORDS), ok_dictionary)
    assert any("every metric card" in p for p in problems), problems


def test_plan_without_rulebook_line_is_refused() -> None:
    mod = load()
    with pytest.raises(mod.MissingLine, match="Rulebook PDFs later"):
        mod.check(plan(None), ok_dictionary)


def test_dictionary_without_rule_0_5_is_refused() -> None:
    mod = load()
    with pytest.raises(mod.MissingLine, match="Rules dependence"):
        mod.check(plan(NEW_WORDS), "## 0. Rules\n\n6. **Versioning:** x\n")


def test_dictionary_dropping_before_the_first_card_is_reported() -> None:
    problems = load().check(plan(NEW_WORDS), dictionary("on each card"))
    assert any("metric-dictionary rule 0.5" in p for p in problems), problems


def test_plan_naming_stats_page_without_once_is_reported() -> None:
    words = 'the score sheet and every stats page say "unofficial"'
    problems = load().check(plan(words), ok_dictionary)
    assert any("once before the first card" in p for p in problems), problems


def test_plan_with_the_decided_words_passes() -> None:
    assert load().check(plan(NEW_WORDS), ok_dictionary) == []


def test_per_card_promise_elsewhere_in_the_plan_is_reported() -> None:
    other = '| OQ-01 | Not supplied | so every metric card carries the same "unofficial scoring" notice |\n'
    problems = load().check(other + plan(NEW_WORDS), ok_dictionary)
    assert any("line 1" in p and "every metric card" in p for p in problems), problems
