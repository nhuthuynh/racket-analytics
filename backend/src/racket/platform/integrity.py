"""``racket-integrity``: the confirmed-corrections check of a restore (ST-076b; NFR-045.3;
ADR 0058 rule 4 step 10). A composition root: the fingerprint is Match & Scoring's, read
through its port only (context map C4, rule 1).

    racket-integrity                                   # prints the fingerprint as JSON
    racket-integrity --expect-count N --expect-sha256 HEX   # also compares with backup.json

Stdout: ``{"corrections": {"count": N, "sha256": "...", "equal": bool}}`` (``equal`` only when
compared). Exit 0: printed, equal, or ``--help``; 1: not equal (named on stderr); 2: usage, configuration
or database error. Reads ``DATABASE_URL`` only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

from racket.matches.public import corrections_fingerprint

_SHA256 = re.compile(r"[0-9a-f]{64}")


def _count(raw: str) -> int:
    if not raw.isascii() or not raw.isdigit():
        raise ValueError("count must be a whole number")
    return int(raw)


def _sha256(raw: str) -> str:
    if not _SHA256.fullmatch(raw):
        raise ValueError("sha256 must be 64 lower-case hex digits")
    return raw


def _parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="racket-integrity", exit_on_error=False)
    parser.add_argument("--expect-count", type=_count, default=None)
    parser.add_argument("--expect-sha256", type=_sha256, default=None)
    args = parser.parse_args(argv)
    if (args.expect_count is None) != (args.expect_sha256 is None):
        raise ValueError("give both --expect-count and --expect-sha256, or neither")
    return args


def _fingerprint(database_url: str) -> tuple[int, str]:
    from racket.platform.db import engine_for, session_factory

    with session_factory(engine_for(database_url))() as session:
        count, digest = corrections_fingerprint(session)
    return count, digest


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parse(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:  # argparse exits 0 after --help, 2 on its own usage errors
        if exc.code == 0:
            return 0
        print(f"racket-integrity: {exc}", file=sys.stderr)
        return 2
    except (argparse.ArgumentError, ValueError) as exc:
        print(f"racket-integrity: {exc}", file=sys.stderr)
        return 2
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("racket-integrity: DATABASE_URL is not set", file=sys.stderr)
        return 2
    try:
        count, digest = _fingerprint(database_url)
    except Exception as exc:  # noqa: BLE001 - any database problem is exit 2
        print(f"racket-integrity: database error ({type(exc).__name__})", file=sys.stderr)
        return 2
    result: dict[str, Any] = {"count": count, "sha256": digest}
    rc = 0
    if args.expect_count is not None:
        result["equal"] = (count, digest) == (args.expect_count, args.expect_sha256)
        if not result["equal"]:
            print(
                f"racket-integrity: corrections differ: count {count} "
                f"(expected {args.expect_count}), sha256 {digest} "
                f"(expected {args.expect_sha256})",
                file=sys.stderr,
            )
            rc = 1
    print(json.dumps({"corrections": result}, sort_keys=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
