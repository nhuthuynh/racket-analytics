#!/usr/bin/env python3
"""Gate checks for a security threat-notes file (SEC-4; ADR 0047 rule 2).

Owner: security-privacy-engineer. Documentation tooling, not product code. It checks one file:

1. every relative Markdown link resolves to a file in the repository (anchors are ignored);
2. every requirement id named with ``--topic`` (e.g. FR-003) appears in a ``##`` heading;
3. every route named with ``--route "METHOD /path"`` has a row in the section whose heading
   contains ``BOLA matrix``: ``| `METHOD /path` | <kind> | <attacker status> | ...`` with a
   non-empty kind and an attacker status of 404;
4. every threat row (first cell ``T4-XX-n``) has 8 cells and a non-empty Test and Status cell;
5. with ``--disclaimer``, one line says "not legal advice" and names both US and AU.

Usage:
    python3 docs/security/tools/check_threat_notes.py docs/security/threat-notes-sprint-04.md \
        --topic FR-003 --route "POST /me/plan/sessions/{session_id}/done" --disclaimer

Exit codes: 0 all checks pass; 1 at least one problem (one ``FAIL`` line each); 2 file missing.
Standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
THREAT_ROW = re.compile(r"^\| (T4-[A-Z]{2}-\d+) \|.*$", re.M)


def cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def broken_links(path: Path, text: str) -> list[str]:
    out = []
    for target in LINK.findall(text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue
        if not (path.parent / target.split("#", 1)[0]).exists():
            out.append(f"FAIL link: {target} does not resolve from {path}")
    return out


def missing_topics(text: str, topics: list[str]) -> list[str]:
    headings = [line for line in text.splitlines() if line.startswith("## ")]
    return [
        f"FAIL topic: no '## ' heading names {t}"
        for t in topics
        if not any(re.search(rf"\b{re.escape(t)}\b", h) for h in headings)
    ]


def bola_section(text: str) -> str:
    match = re.search(r"^## [^\n]*BOLA matrix[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1) if match else ""


def missing_routes(text: str, routes: list[str]) -> list[str]:
    section = bola_section(text)
    if routes and not section:
        return ["FAIL bola: no '## ' heading containing 'BOLA matrix'"]
    out = []
    for route in routes:
        rows = [r for r in section.splitlines() if r.startswith(f"| `{route}` |")]
        if not rows:
            out.append(f"FAIL bola: no row for `{route}`")
            continue
        row = cells(rows[0])
        if len(row) < 3 or not row[1] or row[2] != "404":
            out.append(f"FAIL bola: `{route}` needs a kind and attacker status 404, got {row[1:3]}")
    return out


def bad_threat_rows(text: str) -> list[str]:
    out = []
    for match in THREAT_ROW.finditer(text):
        row = cells(match.group(0))
        if len(row) != 8 or not row[6] or not row[7]:
            out.append(f"FAIL threat: {match.group(1)} needs 8 cells with a Test and a Status")
    return out


def missing_disclaimer(text: str) -> list[str]:
    for line in text.splitlines():
        if "not legal advice" in line.lower() and re.search(r"\bUS\b", line) and "AU" in line:
            return []
    return ["FAIL disclaimer: no line says 'not legal advice' and names US and AU"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path)
    parser.add_argument("--topic", action="append", default=[])
    parser.add_argument("--route", action="append", default=[])
    parser.add_argument("--disclaimer", action="store_true")
    args = parser.parse_args(argv)
    if not args.file.is_file():
        print(f"FAIL file: {args.file} does not exist")
        return 2
    text = args.file.read_text(encoding="utf-8")
    problems = broken_links(args.file, text) + missing_topics(text, args.topic)
    problems += missing_routes(text, args.route) + bad_threat_rows(text)
    if args.disclaimer:
        problems += missing_disclaimer(text)
    for problem in problems:
        print(problem)
    print(f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
