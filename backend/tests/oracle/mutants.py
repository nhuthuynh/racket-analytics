"""Deliberately wrong engines for positive controls of the differential check (retro 0, L4)."""

from __future__ import annotations

from collections.abc import Sequence

from tests.oracle import differential
from tests.oracle import engine as oracle


def receiver_scores(
    raws: Sequence[tuple[str, ...]], rules: oracle.Rules, first: str
) -> list[differential.Snapshot]:
    """Wrong: a rally won by the receiving side also adds a point to side A's score."""
    snaps = differential.oracle_run(raws, rules, first)
    states = oracle.run(list(raws), rules, first)
    out, extra = [snaps[0]], 0
    for raw, prev, snap in zip(raws, states, snaps[1:], strict=False):
        if raw[0] == "won" and raw[1] != prev.serving:
            extra += 1
        a, b, serving, number, winner = snap
        out.append((a + extra, b, serving, number, winner))
    return out
