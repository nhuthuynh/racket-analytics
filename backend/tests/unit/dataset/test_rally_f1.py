"""Rally-segmentation F1 matcher (ST-084b; NFR-006.1-.4; ADR 0004 option 3, ADR 0060 row M11).

R1 (NFR-006.1): a prediction matches a gold rally only when its start and its end are each within
1.0 s. R2 (NFR-006.2): a prediction overlapping two gold rallies is a merge and matches nothing.
R3 (NFR-006.3): a gold rally cut into pieces by predictions that do not overlap each other is a
split and matches nothing. R4 (NFR-006.4): matching is one-to-one and as large as possible.
"""

from __future__ import annotations

import itertools
import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from racket.dataset.rally_f1 import Rally, RallyF1, match_rallies

pytestmark = pytest.mark.unit


def _r(text: str) -> list[Rally]:
    """``"10-20, 21-30"`` -> rallies, seconds."""
    out = []
    for part in text.split(","):
        start, end = part.strip().split("-")
        out.append(Rally(float(start), float(end)))
    return out


def _counts(predicted: str, gold: str) -> tuple[int, int, int]:
    result = match_rallies(_r(predicted), _r(gold))
    return result.tp, result.fp, result.fn


# ------------------------------------------------------------------ R1 (NFR-006.1)
@pytest.mark.parametrize(
    ("predicted", "gold", "expected"),
    [
        pytest.param("10.0-21.01", "10.0-20.0", (0, 1, 1), id="end 1.01 s late: no match"),
        pytest.param("10.0-18.99", "10.0-20.0", (0, 1, 1), id="end 1.01 s early: no match"),
        pytest.param("11.01-20.0", "10.0-20.0", (0, 1, 1), id="start 1.01 s late: no match"),
        pytest.param("8.99-20.0", "10.0-20.0", (0, 1, 1), id="start 1.01 s early: no match"),
        pytest.param("10.0-21.001", "10.0-20.0", (0, 1, 1), id="end 1.001 s late: no match"),
        pytest.param("10.0-21.0", "10.0-20.0", (1, 0, 0), id="end exactly 1.0 s late: match"),
        pytest.param("9.0-19.0", "10.0-20.0", (1, 0, 0), id="both exactly 1.0 s early: match"),
        pytest.param("11.0-21.0", "10.0-20.0", (1, 0, 0), id="both exactly 1.0 s late: match"),
        pytest.param("2.1-6.1", "1.1-5.1", (1, 0, 0), id="1.0 s with float noise: match"),
        pytest.param("10.4-19.7", "10.0-20.0", (1, 0, 0), id="well inside: match"),
    ],
)
def test_r1_start_and_end_each_within_one_second(
    predicted: str, gold: str, expected: tuple[int, int, int]
) -> None:
    assert _counts(predicted, gold) == expected


def test_r1_the_matched_pair_is_reported_by_index() -> None:
    result = match_rallies(_r("50-60, 10.2-19.9"), _r("10-20, 70-80"))
    assert result.pairs == ((1, 0),)


# ------------------------------------------------------------------ R2 (NFR-006.2)
@pytest.mark.parametrize(
    ("predicted", "gold"),
    [
        pytest.param("10.0-30.0", "10.0-19.0, 21.0-30.0", id="spans both, far from either end"),
        pytest.param("10.0-20.6", "10.0-20.0, 20.5-30.0", id="within 1 s of the first, overlaps 2"),
        pytest.param(
            "19.6-30.0", "10.0-20.0, 20.5-30.0", id="within 1 s of the second, overlaps 2"
        ),
    ],
)
def test_r2_a_prediction_spanning_two_gold_rallies_matches_neither(
    predicted: str, gold: str
) -> None:
    assert _counts(predicted, gold) == (0, 1, 2)


def test_r2_touching_the_next_gold_rally_is_not_a_merge() -> None:
    assert _counts("10.0-20.0", "10.0-20.0, 20.0-30.0") == (1, 0, 1)


def test_r2_starting_where_the_previous_gold_rally_ends_is_not_a_merge() -> None:
    assert _counts("10.0-20.0", "0.0-10.0, 10.0-20.0") == (1, 0, 1)


def test_r2_a_merge_does_not_stop_other_predictions_from_matching() -> None:
    assert _counts("10.0-20.6, 40.0-50.0", "10.0-20.0, 20.5-30.0, 40.0-50.0") == (1, 1, 2)


# ------------------------------------------------------------------ R3 (NFR-006.3)
@pytest.mark.parametrize(
    "predicted",
    [
        pytest.param("10.0-15.0, 15.5-20.0", id="two halves, far from the ends"),
        pytest.param("10.0-19.5, 19.6-20.0", id="first piece within 1 s of both ends"),
        pytest.param("10.0-10.4, 10.5-20.0", id="second piece within 1 s of both ends"),
    ],
)
def test_r3_two_predictions_inside_one_gold_rally_give_no_match(predicted: str) -> None:
    assert _counts(predicted, "10.0-20.0") == (0, 2, 1)


def test_r3_touching_pieces_are_still_a_split() -> None:
    assert _counts("10.0-19.5, 19.5-20.0", "10.0-20.0") == (0, 2, 1)


def test_r3_a_split_does_not_stop_other_gold_rallies_from_matching() -> None:
    assert _counts("10.0-19.5, 19.6-20.0, 40-50", "10.0-20.0, 40-50") == (1, 2, 1)


# ------------------------------------------------------------------ R4 (NFR-006.4)
def test_r4_two_predictions_near_one_gold_rally_give_one_tp_and_one_fp() -> None:
    assert _counts("10.2-20.1, 10.5-19.8", "10.0-20.0") == (1, 1, 0)


def test_r4_one_prediction_near_two_gold_rallies_matches_one() -> None:
    assert _counts("10.2-20.1", "10.0-20.0, 10.5-19.8") == (1, 0, 1)


def test_r4_the_matching_is_maximal_not_greedy() -> None:
    # B is nearest to X, but taking B-X leaves A unmatched; A-X and B-Y give 2.
    result = match_rallies(_r("10.0-20.0, 10.9-20.9"), _r("10.5-20.5, 11.8-21.8"))
    assert (result.tp, result.fp, result.fn) == (2, 0, 0)
    assert result.pairs == ((0, 0), (1, 1))


def test_r4_a_matched_prediction_moves_to_its_next_gold_rally_to_make_room() -> None:
    # The first prediction is near both gold rallies and takes the first; the second is near the
    # first gold rally only, so the first prediction must move on to the second gold rally.
    result = match_rallies(_r("10.5-20.5, 9.5-19.5"), _r("10.0-20.0, 10.9-20.9"))
    assert result.pairs == ((0, 1), (1, 0))


# ------------------------------------------------------------------ precision, recall, F1
def test_precision_recall_and_f1_from_the_counts() -> None:
    result = match_rallies(_r("10-20, 30-40"), _r("10-20, 30-40, 50-60"))
    assert (result.tp, result.fp, result.fn) == (2, 0, 1)
    assert result.precision == 1.0
    assert result.recall == pytest.approx(2 / 3)
    assert result.f1 == pytest.approx(0.8)
    assert result.f1_pct == pytest.approx(80.0)


def test_f1_with_false_positives_and_false_negatives() -> None:
    result = match_rallies(_r("10-20, 30-40, 70-80, 90-95"), _r("10-20, 50-60"))
    assert (result.tp, result.fp, result.fn) == (1, 3, 1)
    assert result.precision == pytest.approx(0.25)
    assert result.recall == pytest.approx(0.5)
    assert result.f1 == pytest.approx(1 / 3)
    assert result.f1_pct == pytest.approx(100 / 3)


def test_no_predictions_scores_zero() -> None:
    result = match_rallies([], _r("10-20"))
    assert (result.tp, result.fp, result.fn) == (0, 0, 1)
    assert (result.precision, result.recall, result.f1) == (0.0, 0.0, 0.0)


def test_no_gold_rallies_scores_zero() -> None:
    result = match_rallies(_r("10-20"), [])
    assert (result.tp, result.fp, result.fn) == (0, 1, 0)
    assert (result.precision, result.recall, result.f1) == (0.0, 0.0, 0.0)


def test_nothing_to_score_is_refused() -> None:
    with pytest.raises(ValueError, match=r"^nothing to score: no predicted and no gold rallies$"):
        match_rallies([], [])


@pytest.mark.parametrize(
    ("start", "end"),
    [(10.0, 10.0), (10.0, 9.0), (math.nan, 10.0), (0.0, math.inf), (-math.inf, 1.0)],
)
def test_a_rally_must_be_finite_and_end_after_it_starts(start: float, end: float) -> None:
    with pytest.raises(ValueError, match="rally"):
        Rally(start, end)


def test_the_result_is_a_value() -> None:
    a = match_rallies(_r("10-20"), _r("10-20"))
    assert a == match_rallies(_r("10-20"), _r("10-20"))
    assert isinstance(a, RallyF1)


# ------------------------------------------------------------------ properties (R4)
_ms = st.integers(min_value=0, max_value=120_000)
_len_ms = st.integers(min_value=100, max_value=30_000)
_rally = st.builds(lambda s, n: Rally(s / 1000, (s + n) / 1000), _ms, _len_ms)
_rallies = st.lists(_rally, max_size=8)


def _overlap(a: Rally, b: Rally) -> bool:
    return a.start_s < b.end_s and b.start_s < a.end_s


def _cut(x: Rally, others: list[Rally]) -> bool:
    hits = [o for o in others if _overlap(x, o)]
    return any(not _overlap(a, b) for a, b in itertools.combinations(hits, 2))


def _eligible(p: Rally, g: Rally, predicted: list[Rally], gold: list[Rally]) -> bool:
    near = all(
        round(abs(a - b) * 1000) <= 1000 for a, b in ((p.start_s, g.start_s), (p.end_s, g.end_s))
    )
    return near and not _cut(p, gold) and not _cut(g, predicted)


def _max_matching_brute(predicted: list[Rally], gold: list[Rally]) -> int:
    edges = [
        (i, j)
        for i, p in enumerate(predicted)
        for j, g in enumerate(gold)
        if _eligible(p, g, predicted, gold)
    ]
    for size in range(min(len(predicted), len(gold)), 0, -1):
        for chosen in itertools.combinations(edges, size):
            if len({i for i, _ in chosen}) == size and len({j for _, j in chosen}) == size:
                return size
    return 0


@given(_rallies, _rallies)
def test_property_matching_is_one_to_one_and_f1_in_unit_interval(
    predicted: list[Rally], gold: list[Rally]
) -> None:
    if not predicted and not gold:
        return
    result = match_rallies(predicted, gold)
    preds = [i for i, _ in result.pairs]
    golds = [j for _, j in result.pairs]
    assert len(set(preds)) == len(preds) == result.tp
    assert len(set(golds)) == len(golds) == result.tp
    assert result.tp + result.fp == len(predicted)
    assert result.tp + result.fn == len(gold)
    for i, j in result.pairs:
        assert _eligible(predicted[i], gold[j], predicted, gold)
    for value in (result.precision, result.recall, result.f1):
        assert 0.0 <= value <= 1.0
    assert result.f1_pct == pytest.approx(100 * result.f1)


@given(st.lists(_rally, max_size=4), st.lists(_rally, max_size=4))
def test_property_the_matching_is_maximum(predicted: list[Rally], gold: list[Rally]) -> None:
    if not predicted and not gold:
        return
    assert match_rallies(predicted, gold).tp == _max_matching_brute(predicted, gold)


@given(_rallies, _rallies, st.randoms(use_true_random=False))
def test_property_order_does_not_change_the_counts(
    predicted: list[Rally], gold: list[Rally], rnd: object
) -> None:
    if not predicted and not gold:
        return
    before = match_rallies(predicted, gold)
    p2, g2 = list(predicted), list(gold)
    rnd.shuffle(p2)  # type: ignore[attr-defined]
    rnd.shuffle(g2)  # type: ignore[attr-defined]
    after = match_rallies(p2, g2)
    assert (after.tp, after.fp, after.fn) == (before.tp, before.fp, before.fn)
