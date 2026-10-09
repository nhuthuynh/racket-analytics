"""``racket-drill-lint``: the drill library lint, a CLI and a CI job (ST-053; FR-140).

Usage::

    racket-drill-lint content/drills                 # a library directory, with library.lock
    racket-drill-lint path/to/one-drill.json         # one file: the rules, no lock
    racket-drill-lint content/drills --update-lock   # add new drill versions to the lock
    racket-drill-lint content/drills --base-lock base.lock   # also against the base branch

``--base-lock`` (default: the ``RACKET_DRILL_BASE_LOCK`` environment variable, which the
``drill-lint`` CI job fills from the base branch) is the base branch's ``library.lock``: every
version locked there must keep its file, its content and its lock line, so a deletion or an
in-place edit fails even when the same change rewrites the library's lock. A base branch without
a lock is ``{"schema": "drill-library-lock/v1", "drills": {}}``. It applies to directories.

The rules are in ``rules.py`` (schema and FR-140), immutability in ``lock.py``. Known metric
ids are every entry of the pickleball metric dictionary (Published Language R5), any status.
Every failure line names the file, the drill and the reason. Exit codes: 0 pass, 1 problems,
2 a path that does not exist or a lock (the library's or the base one) that cannot be read.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from racket.coaching.drills.lock import (
    LOCK_NAME,
    check_library,
    lock_update,
    parse_lock,
    render_lock,
)
from racket.coaching.drills.rules import Problem, lint_drills
from racket.sports.pickleball.metrics import load_dictionary


def _load(paths: Iterable[Path], root: Path) -> tuple[dict[str, object], list[Problem]]:
    docs: dict[str, object] = {}
    broken: list[Problem] = []
    for path in paths:
        name = str(path.relative_to(root))
        try:
            docs[name] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            broken.append(Problem(name, None, "invalid json", str(exc)))
    return docs, broken


BASE_LOCK_ENV = "RACKET_DRILL_BASE_LOCK"


def read_lock(path: Path) -> dict[str, str]:
    return parse_lock(path.read_text(encoding="utf-8"), str(path))


def lint_path(
    target: Path,
    metrics: frozenset[str],
    update_lock: bool = False,
    base: dict[str, str] | None = None,
) -> list[Problem]:
    if target.is_file():
        docs, broken = _load([target], target.parent)
        return broken + lint_drills(docs, metrics)
    files = sorted(p for p in target.rglob("*.json") if p.name != "schema.json")
    docs, broken = _load(files, target)
    lock_path = target / LOCK_NAME
    lock = read_lock(lock_path) if lock_path.exists() else {}
    if update_lock and not broken and (grown := lock_update(docs, metrics, lock, base)) is not None:
        lock_path.write_text(render_lock(grown), encoding="utf-8")
        lock = grown
    problems = broken + check_library(docs, metrics, lock, base)
    if not lock_path.exists():
        problems.insert(0, Problem(LOCK_NAME, None, "no lock", f"{lock_path} is missing"))
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="racket-drill-lint",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("paths", nargs="+", type=Path, help="drill library directories or files")
    parser.add_argument("--update-lock", action="store_true", help="add new versions to the lock")
    parser.add_argument(
        "--base-lock",
        type=Path,
        default=os.environ.get(BASE_LOCK_ENV) or None,
        help=f"the base branch's library.lock (default: ${BASE_LOCK_ENV})",
    )
    args = parser.parse_args(argv)
    base: dict[str, str] | None = None
    if args.base_lock is not None:
        try:
            base = read_lock(Path(args.base_lock))
        except (OSError, ValueError) as exc:
            print(f"ERROR {args.base_lock}: unreadable base lock: {exc}", file=sys.stderr)
            return 2
    dictionary = load_dictionary()
    metrics = frozenset(entry.id for entry in dictionary.entries)
    worst = 0
    for target in args.paths:
        if not target.exists():
            print(f"ERROR {target}: no such file or directory", file=sys.stderr)
            worst = 2
            continue
        try:
            problems = lint_path(target, metrics, update_lock=args.update_lock, base=base)
        except (OSError, ValueError) as exc:
            print(f"ERROR {target}: unreadable lock: {exc}", file=sys.stderr)
            worst = 2
            continue
        for problem in problems:
            print(problem.line())
        status = "FAILED" if problems else "ok"
        version = dictionary.version
        print(f"{target}: {status}, {len(problems)} problem(s), metric dictionary v{version}")
        if problems:
            worst = max(worst, 1)
    return worst


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
