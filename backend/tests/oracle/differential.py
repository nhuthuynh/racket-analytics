"""Differential check P9: production engine vs the independent oracle (ST-022, NFR-002b).

``compare`` scores each random sequence with both engines and reports the SHORTEST disagreeing
prefix found (sprint-01 §14.3.7). The production side is reached through the seams only.

Nightly use (ST-024 wires it into the nightly workflow):
    cd backend && uv run python -m tests.oracle.differential --sequences 100000 --json out.json
Exit code 0 = 0 disagreements, 1 = at least one disagreement.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from tests.oracle import engine as oracle

# A comparable snapshot: (score A, score B, serving side, server number, winner or None)
Snapshot = tuple[int, int, str, int, str | None]
# An engine under test: (raw outcomes, rules, first server) -> snapshots from the start state.
EngineRun = Callable[[Sequence[tuple[str, ...]], oracle.Rules, str], list[Snapshot]]

CONFIGS = (
    oracle.Rules(11, 2, True),
    oracle.Rules(15, 2, True),
    oracle.Rules(21, 2, True),
    oracle.Rules(11, 1, True),
    oracle.Rules(11, 2, False),
)


def oracle_run(raws: Sequence[tuple[str, ...]], rules: oracle.Rules, first: str) -> list[Snapshot]:
    return [
        (s.a, s.b, s.serving, s.server_number, s.winner)
        for s in oracle.run(list(raws), rules, first)
    ]


@dataclass
class Disagreement:
    rules: dict[str, Any]
    first_server: str
    sequence: list[list[str]]
    expected: Snapshot | None
    actual: Snapshot | None


@dataclass
class Report:
    sequences: int
    disagreements: int = 0
    shortest: Disagreement | None = None
    seconds: float = 0.0
    configs: list[dict[str, Any]] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.disagreements == 0


def _first_difference(a: list[Snapshot], b: list[Snapshot]) -> int | None:
    for i in range(max(len(a), len(b))):
        if i >= len(a) or i >= len(b) or a[i] != b[i]:
            return i
    return None


def compare(
    candidate: EngineRun,
    sequences: Iterable[Sequence[tuple[str, ...]]],
    configs: Sequence[oracle.Rules] = CONFIGS,
    reference: EngineRun = oracle_run,
) -> Report:
    started = time.monotonic()
    report = Report(sequences=0, configs=[asdict(c) for c in configs])
    for n, raws in enumerate(sequences):
        rules = configs[n % len(configs)]
        first = "AB"[(n // len(configs)) % 2]
        report.sequences += 1
        want, got = reference(raws, rules, first), candidate(raws, rules, first)
        index = _first_difference(want, got)
        if index is None:
            continue
        report.disagreements += 1
        prefix = [list(r) for r in raws[:index]]  # the rallies that lead to the difference
        if report.shortest is None or len(prefix) < len(report.shortest.sequence):
            report.shortest = Disagreement(
                rules=asdict(rules),
                first_server=first,
                sequence=prefix,
                expected=want[index] if index < len(want) else None,
                actual=got[index] if index < len(got) else None,
            )
    report.seconds = round(time.monotonic() - started, 3)
    return report


def production_run(
    raws: Sequence[tuple[str, ...]], rules: oracle.Rules, first: str
) -> list[Snapshot]:
    """The production engine via the seams (RED until ST-020)."""
    from tests.support import contract
    from tests.support import scoring as sc

    config = contract.RULES_CONFIG.load()(
        rules_version="TEST-ORACLE",
        scoring_system="side_out",
        format="doubles",
        points_to_win=rules.points_to_win,
        win_by=rules.win_by,
        first_service_single_server=rules.first_service_single_server,
    )
    state = contract.NEW_GAME.load()(config, sc.side(first))
    snaps = [_snap(state)]
    for raw in raws:
        if state.is_over:
            break
        state = sc.apply(state, sc.to_outcome(raw), config)
        if sc.is_domain_error(state):
            snaps.append((-1, -1, "error", -1, repr(state)))
            break
        snaps.append(_snap(state))
    return snaps


def _snap(state: Any) -> Snapshot:
    winner = None if state.winner is None else state.winner.name
    return (state.score_a, state.score_b, state.serving_side.name, state.server_number, winner)


def main(argv: list[str] | None = None, candidate: EngineRun | None = None) -> int:
    from tests.support.scoring import random_sequences

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequences", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=int(time.strftime("%Y%m%d")))
    parser.add_argument("--json", help="write the report here")
    args = parser.parse_args(argv)
    report = compare(candidate or production_run, random_sequences(args.seed, args.sequences))
    payload = {**asdict(report), "seed": args.seed, "passed": report.passed}
    text = json.dumps(payload, indent=2, default=str)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
