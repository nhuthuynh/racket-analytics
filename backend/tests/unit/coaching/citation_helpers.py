"""Test citations for ST-057 (FR-122, FR-123; QD-PL-04, QD-PL-06). Values are made up for the
tests, not coaching content; each evidence list holds rally ids ``<match>-r<i>`` in video order."""

from __future__ import annotations

from racket.coaching.plan.domain import Citation

NAMES = {
    "AN-01": "Rallies won on serve",
    "AN-02": "Rallies won when receiving",
    "AN-04": "Unforced errors per game",
    "AN-05": "Serve faults",
    "AN-07": "How rallies ended",
}


def cite(
    target: str,
    k: int,
    n: int,
    *,
    low_sample: bool = False,
    rallies: int | None = None,
    matches: tuple[str, ...] = ("m1",),
) -> Citation:
    """A citation of ``target`` with ``rallies`` evidence rallies (default k) per match."""
    per_match = k if rallies is None else rallies
    evidence = [(m, "A", tuple(f"{m}-r{i}" for i in range(1, per_match + 1))) for m in matches]
    return Citation.from_evidence(
        target=target,
        metric_name=NAMES[target.split(":")[0]],
        metric_version="0.1",
        k=k,
        n=n,
        low_sample=low_sample,
        evidence=evidence,
    )


def all_citations(*, low_top: bool = False) -> dict[str, Citation]:
    """A citation for every plan target (weakness-catalogue §5)."""
    return {
        "AN-01": cite("AN-01", 4, 7),
        "AN-02": cite("AN-02", 3, 6),
        "AN-04": cite("AN-04", 2, 1, low_sample=low_top),
        "AN-05": cite("AN-05", 2, 7),
        "AN-07:fault": cite("AN-07:fault", 2, 10),
        "AN-07:forced-error": cite("AN-07:forced-error", 1, 10),
    }
