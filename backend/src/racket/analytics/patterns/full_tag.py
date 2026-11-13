"""Full Tag adapter: pattern measures from one Full Tag label document (ST-171b; ADR 0061 Rule 1).

The ACL of Analytics over the Dataset & Labelling published language (``full-tag-labels/v1``,
``racket.dataset.labels``): ``read_rallies`` turns a validated document into Analytics' own
``Rally`` and ``Hit`` and refuses anything outside that vocabulary (``UntranslatableLabels``,
fail closed). The vocabulary below is pinned equal to the publisher's by a contract test, so this
pure module imports neither the Dataset context nor a framework (context-map rule 1).
``full_tag_measures`` returns ``measures[pattern][side]`` like ``quick_tag_measures``: AN-09 now
(FR-171.R2, R3, R6); AN-13 and AN-08 join with ST-171c/d. A facet whose labeller agreement is
not admitted (QD-TX-03) is labelled "single-labeller, agreement not measured".
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from racket.analytics.patterns.measure import PatternMeasure
from racket.analytics.patterns.third_shot import (
    AN09,
    AN09_MIN_N,
    AN09_VERSION,
    ThirdShotTally,
    third_shots,
)
from racket.analytics.uncertainty import wilson

LABEL_SCHEMA = "full-tag-labels/v1"
SIDES = ("A", "B")
SLOTS = ("A1", "A2", "B1", "B2")
ENDINGS = ("winner", "unforced_error", "forced_error", "fault", "replay")
TRAJECTORIES = ("drive", "drop", "dink", "lob")
AGREEMENT_LABELS = {
    "not_measured": "single-labeller, agreement not measured",
    "measured": "labeller agreement admitted (QD-TX-03)",
}


class UntranslatableLabels(ValueError):
    """A label document outside the published vocabulary: nothing is measured from it."""


@dataclass(frozen=True, slots=True)
class Hit:
    side: str
    trajectory: str | None


@dataclass(frozen=True, slots=True)
class Rally:
    id: str
    replay: bool
    hits: tuple[Hit, ...]


def _hit(event: Mapping[str, Any], where: str) -> Hit:
    hitter = event.get("hitter")
    if hitter not in SLOTS:
        raise UntranslatableLabels(f"{where}: unknown hitter {hitter!r}")
    facets = event.get("facets", {})
    if not isinstance(facets, Mapping):
        raise UntranslatableLabels(f"{where}: facets must be an object")
    trajectory = facets.get("trajectory")
    if trajectory is not None and trajectory not in TRAJECTORIES:
        raise UntranslatableLabels(f"{where}: unknown trajectory {trajectory!r}")
    return Hit(str(hitter)[0], trajectory)


def _rally(raw: object, where: str) -> Rally:
    if not isinstance(raw, Mapping) or not isinstance(raw.get("id"), str):
        raise UntranslatableLabels(f"{where}: a rally needs a string id")
    events, outcome = raw.get("events"), raw.get("outcome")
    if not isinstance(events, list) or not isinstance(outcome, Mapping):
        raise UntranslatableLabels(f"{where}: a rally needs events and an outcome")
    if outcome.get("ending") not in ENDINGS:
        raise UntranslatableLabels(f"{where}: unknown ending {outcome.get('ending')!r}")
    hits = []
    for i, event in enumerate(events):
        if not isinstance(event, Mapping):
            raise UntranslatableLabels(f"{where}.events[{i}]: an event must be an object")
        if event.get("type") == "hit":
            hits.append(_hit(event, f"{where}.events[{i}]"))
    return Rally(raw["id"], outcome["ending"] == "replay", tuple(hits))


def read_rallies(labels: Mapping[str, Any]) -> tuple[Rally, ...]:
    """The rallies of one validated label document in Analytics' terms (the ACL)."""
    if labels.get("schema") != LABEL_SCHEMA or not isinstance(labels.get("rallies"), list):
        raise UntranslatableLabels(f"not a {LABEL_SCHEMA} document")
    return tuple(_rally(raw, f"rallies[{i}]") for i, raw in enumerate(labels["rallies"]))


def an09_measure(tally: ThirdShotTally, agreement: str) -> PatternMeasure:
    """FR-171.R2, R3, R6: drops / counted third shots, Wilson 95 %, low sample below min_n."""
    n = tally.n
    return PatternMeasure(
        AN09,
        tally.k / n if n else None,
        n,
        wilson(tally.k, n),
        "wilson",
        n < AN09_MIN_N,
        AN09_VERSION,
        n_excluded=tally.n_excluded,
        exclusions=tuple(sorted((r, len(ids)) for r, ids in tally.excluded.items())),
        agreement=agreement,
    )


def full_tag_measures(
    labels: Mapping[str, Any], *, admitted_facets: Collection[str] = ()
) -> dict[str, dict[str, PatternMeasure]]:
    """``measures[pattern][side]`` of one validated Full Tag label document.
    ``admitted_facets``: the facets with admitted labeller agreement (the gold-set manifest's
    ``agreement``, QD-TX-03); none by default."""
    rallies = read_rallies(labels)
    agreement = "measured" if "trajectory" in admitted_facets else "not_measured"
    return {AN09: {side: an09_measure(third_shots(rallies, side), agreement) for side in SIDES}}
