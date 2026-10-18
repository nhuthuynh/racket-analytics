"""Label-set build: ``python -m racket.dataset.build_label_set [--out PATH]`` (ST-070; FR-009,
FR-150; api-sprint-04 §6; OQ-06, ADR 0023; SEC-4 T4-CS-1, T4-CS-2). Run by an operator in the
``api`` container with the app identity, as ``racket.dataset.admin`` is.

Builds the next label set from the live matches with labels (Quick Tag rallies, the player's
corrections, and Full Tag labels) and prints its manifest (``label-set/v1``) as JSON on stdout.
With ``FEATURE_TRAINING_CONSENT`` on, only matches whose owner has opted in now are in it
(read through ``racket.players.public``, context map R9); off, the FR-150 team-held consent
record decides, as before.

``--out PATH`` also writes the manifest to a new file. An existing file is never written over
(exit 2): a built version is frozen, and a revoke takes effect in the next build (OQ-06).

Exit 0 built; 1 the consent lookup failed (nothing printed, nothing written: fail closed);
2 usage or an existing ``--out`` file. Stdout holds the manifest and nothing else, so this
command installs no log handler; its one-line summary goes to stderr, counts only (NFR-057).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from racket.dataset.label_set import (
    Candidate,
    ConsentRule,
    ConsentUnavailable,
    LabelSet,
    select_label_set,
)
from racket.dataset.repository import LabelRepository
from racket.matches import public as matches
from racket.players import public as players


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m racket.dataset.build_label_set", exit_on_error=False
    )
    parser.add_argument("--out", type=Path, default=None, help="new file for the manifest")
    return parser


def candidates(session: Any) -> list[Candidate]:
    """Every live match with labels, from the Match & Scoring port and this context's tables."""
    repo = LabelRepository(session)
    labels = repo.full_tag_label_counts()
    live = matches.live_matches_with_rallies(session, extra_ids=sorted(labels))
    team = repo.team_consented([m.match_id for m in live])
    return [
        Candidate(m.match_id, m.owner_id, m.rallies, labels.get(m.match_id, 0), m.match_id in team)
        for m in live
    ]


def build(session: Any, rule: ConsentRule, now: datetime) -> LabelSet:
    def opted_in(owners: frozenset[uuid.UUID]) -> set[uuid.UUID]:
        return players.training_opted_in(session, sorted(owners))

    return select_label_set(candidates(session), rule, opted_in, now)


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except (argparse.ArgumentError, SystemExit):
        return 2
    out: Path | None = args.out
    if out is not None and out.exists():
        print("label-set: the --out file exists; a built set is never edited", file=sys.stderr)
        return 2

    from racket.platform.db import engine_for, session_factory
    from racket.platform.settings import Settings

    settings = Settings.from_env()
    rule = ConsentRule.for_flag(settings.feature_training_consent)
    engine = engine_for(settings.database_url)
    session = session_factory(engine)()
    try:
        label_set = build(session, rule, datetime.now(UTC))
    except ConsentUnavailable:
        print("label-set: the consent lookup failed; nothing was built", file=sys.stderr)
        return 1
    finally:
        session.rollback()
        session.close()
        engine.dispose()
    text = json.dumps(label_set.manifest(), indent=2) + "\n"
    if out is not None:
        try:
            with out.open("x", encoding="utf-8") as handle:
                handle.write(text)
        except FileExistsError:
            print("label-set: the --out file exists; a built set is never edited", file=sys.stderr)
            return 2
    sys.stdout.write(text)
    print(f"label-set: built, rule {rule.value}, {len(label_set.matches)} matches", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
