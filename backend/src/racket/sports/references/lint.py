"""``racket-reference-lint``: the reference-set lint (ST-170a; FR-170.R1-R3; ADR 0061 Rule 1).

Usage::

    racket-reference-lint content/references
    racket-reference-lint content/references --update-lock      # lock new versions
    racket-reference-lint content/references --base-lock base.lock

``--catalogue`` and ``--sources`` default to ``docs/domain/pattern-catalogue.md`` and
``docs/domain/sources.md`` under the current directory (the repository root in CI).
``--base-lock`` (default: ``RACKET_REFERENCE_BASE_LOCK``) is the base branch's lock. No footage
provenance export exists in Sprint 6 (ADR 0062 planned), so every ``measured`` entry is refused.
Exit codes: 0 pass, 1 problems, 2 a path, catalogue, register or lock that cannot be read.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from racket.sports.references.loader import (
    CatalogueError,
    check_tree,
    parse_catalogue,
    parse_sources,
    read_tree,
)
from racket.sports.references.lock import LOCK_NAME, LockError, lock_update, parse_lock, render_lock

BASE_LOCK_ENV = "RACKET_REFERENCE_BASE_LOCK"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="racket-reference-lint", description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--catalogue", type=Path, default=Path("docs/domain/pattern-catalogue.md"))
    parser.add_argument("--sources", type=Path, default=Path("docs/domain/sources.md"))
    parser.add_argument("--base-lock", type=Path, default=os.environ.get(BASE_LOCK_ENV) or None)
    parser.add_argument("--update-lock", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not args.root.is_dir():
            raise FileNotFoundError(f"{args.root} is not a directory")
        catalogue = parse_catalogue(args.catalogue.read_text(encoding="utf-8"))
        sources = parse_sources(args.sources.read_text(encoding="utf-8"))
        base = {}
        if args.base_lock is not None:
            base = parse_lock(args.base_lock.read_text(encoding="utf-8"), str(args.base_lock))
        docs, lock, broken = read_tree(args.root)
    except (OSError, CatalogueError, LockError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
    if args.update_lock and not broken:
        lock = lock_update(docs, lock or {})
        (args.root / LOCK_NAME).write_text(render_lock(lock), encoding="utf-8")
    problems = broken + check_tree(docs, lock, catalogue, sources, {}, base)
    for problem in problems:
        print(problem)
    print(f"reference-lint: {len(docs)} version file(s), {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
