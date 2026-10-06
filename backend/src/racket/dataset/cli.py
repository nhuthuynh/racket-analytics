"""``racket-manifest-check``: CI gate for fixture and gold-set integrity (FR-151, NFR-078).

Usage::

    racket-manifest-check fixtures/clips/synthetic-60s [--base-manifest base.json]

Exit codes: 0 intact, 1 integrity problems, 2 malformed or unreadable manifest.
A manifest with ``"schema": "gold-set-manifest/v1"`` is also checked as a gold set (ST-040,
``racket.dataset.gold_set``): QD §8 fields, venue split, agreement gates, consent and its
Full Tag label files (``full-tag-labels/v1``).
In CI, ``--base-manifest`` is the manifest from the merge base (``git show``), which enforces
"no hash change without a version bump".
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from racket.dataset.filesystem import (
    MANIFEST_NAME,
    SymlinkInSetError,
    hash_set,
    load_labels,
    load_manifest,
)
from racket.dataset.gold_set import GoldSetCheck, gold_set_of
from racket.dataset.manifest import CheckResult, ManifestCheck, ManifestFormatError


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="racket-manifest-check", description=__doc__)
    parser.add_argument("set_dir", nargs="+", type=Path, help="directories holding manifest.json")
    parser.add_argument("--base-manifest", type=Path, help="manifest from the merge base")
    args = parser.parse_args(argv)

    worst = 0
    for set_dir in args.set_dir:
        try:
            manifest = load_manifest(set_dir / MANIFEST_NAME)
            gold = gold_set_of(manifest)
            base = load_manifest(args.base_manifest) if args.base_manifest else None
        except (
            OSError,
            json.JSONDecodeError,
            ManifestFormatError,
            TypeError,
            AttributeError,
        ) as exc:
            print(f"FAIL {set_dir}: malformed or unreadable manifest: {exc}")
            worst = max(worst, 2)
            continue
        try:
            result = ManifestCheck.check(manifest, hash_set(set_dir))
        except SymlinkInSetError as exc:
            print(f"FAIL {set_dir}: {exc}: symbolic links are not allowed in a set [symlink]")
            worst = max(worst, 1)
            continue
        if base is not None:
            bump = ManifestCheck.check_version_bump(base=base, head=manifest)
            result = CheckResult(result.problems + bump.problems)
        if gold is not None:
            gold_result = GoldSetCheck.check(gold, load_labels(set_dir, gold))
            result = CheckResult(result.problems + gold_result.problems)
        if result.passed:
            kind = f"gold set ({gold.purpose}), " if gold is not None else ""
            print(
                f"OK   {set_dir}: {manifest.id} v{manifest.version}, {kind}"
                f"{len(manifest.files)} files"
            )
        else:
            worst = max(worst, 1)
            for problem in result.problems:
                print(f"FAIL {set_dir}: {problem.describe()}")
    return worst


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
