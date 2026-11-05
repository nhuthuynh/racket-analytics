#!/usr/bin/env python3
"""Release-notes check for the CI ``doc-check`` job (ST-082; REL-1.1, FR-055.R1; ADR 0058 rule 7).

On ``docs/releases/r1-rc.md`` (``--notes``):
1. the YAML front matter parses to a mapping with ``release``, ``alembic_revision``,
   ``previous_release`` and ``previous_alembic_revision`` (the rollback drill reads them);
2. FR-055.R1: the phrase "unofficial scoring" appears before the first ``##`` section (the notice);
3. REL-1.1: every FR whose Release cell in the traceability matrix (``--matrix``) starts with
   ``R1`` has a row in the notes' features table;
4. REL-1.1: every ``FEATURE_*`` variable of ``infra/env.example`` (``--env``) has a row in the
   flags table whose Default cell is its value there;
5. REL-1.1: the known-limitations table has at least one row, and every row names a P-n.
Exit 0 all pass; 1 at least one problem (one ``FAIL`` line each); 2 usage or unreadable input.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
NOTICE = "unofficial scoring"
KEYS = ("release", "alembic_revision", "previous_release", "previous_alembic_revision")
FR_ID = re.compile(r"^FR-\d{3}$")
FLAG = re.compile(r"^(FEATURE_[A-Z0-9_]+)=(.*)$")
PN = re.compile(r"\bP\d+\b")


def rows(text: str, heading: str) -> list[list[str]]:
    """Body rows of the first table under the ``## <heading>`` section, cells stripped."""
    section = re.search(rf"^## {re.escape(heading)}\b.*?(?=^## |\Z)", text, re.M | re.S)
    if not section:
        return []
    table = [ln for ln in section.group(0).splitlines() if ln.lstrip().startswith("|")]
    cells = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in table[2:]]
    return [c for c in cells if c and c[0]]


def r1_frs(matrix: str) -> list[str]:
    out = []
    for ln in matrix.splitlines():
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) > 3 and FR_ID.match(cells[0]) and cells[3].startswith("R1"):
            out.append(cells[0])
    return out


def flags(env: str) -> dict[str, str]:
    return {m[1]: m[2].strip() for ln in env.splitlines() if (m := FLAG.match(ln.strip()))}


def check(notes: str, frs: list[str], defaults: dict[str, str]) -> list[str]:
    problems = []
    front, body = {}, notes
    parts = notes.split("---\n", 2)
    if notes.startswith("---\n") and len(parts) == 3:
        try:
            front = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError as exc:
            problems.append(f"front matter does not parse: {exc}".splitlines()[0])
        body = parts[2]
    else:
        problems.append("front matter missing (--- ... --- at the top)")
    if not isinstance(front, dict):
        problems.append("front matter is not a mapping")
    elif not problems:
        problems += [f"front matter has no {k}" for k in KEYS if not front.get(k)]

    if NOTICE not in body.split("\n## ", 1)[0].lower():
        problems.append(f'FR-055.R1: no "{NOTICE}" notice before the first section')

    listed = {r[0] for r in rows(body, "Features")}
    problems += [
        f"REL-1.1: R1 requirement {fr} is not in the Features table"
        for fr in frs
        if fr not in listed
    ]

    table = {r[0].strip("`"): r[1].strip("`") if len(r) > 1 else "" for r in rows(body, "Flags")}
    for flag, value in defaults.items():
        if flag not in table:
            problems.append(f"REL-1.1: flag {flag} is not in the Flags table")
        elif table[flag] != value:
            problems.append(
                f"REL-1.1: flag {flag} default is {table[flag]!r}, env.example has {value!r}"
            )

    limits = rows(body, "Known limitations")
    if not limits:
        problems.append("REL-1.1: no row in the Known limitations table")
    problems += [
        f"REL-1.1: limitation {r[0]} names no P-n" for r in limits if not PN.search(" ".join(r[1:]))
    ]
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--notes", type=Path, default=ROOT / "docs/releases/r1-rc.md")
    ap.add_argument(
        "--matrix", type=Path, default=ROOT / "docs/requirements/traceability-matrix.md"
    )
    ap.add_argument("--env", type=Path, default=ROOT / "infra/env.example")
    args = ap.parse_args(argv)
    try:
        notes, matrix, env = (p.read_text() for p in (args.notes, args.matrix, args.env))
    except OSError as exc:
        print(f"check_release_notes: {exc}", file=sys.stderr)
        return 2
    frs = r1_frs(matrix)
    if not frs:
        print(f"check_release_notes: no R1 requirement in {args.matrix}", file=sys.stderr)
        return 2
    problems = check(notes, frs, flags(env))
    for p in problems:
        print(f"FAIL {args.notes.name}: {p}")
    print(
        f"check_release_notes: {len(frs)} R1 FRs, {len(flags(env))} flags, "
        f"{len(problems)} problem(s)"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
