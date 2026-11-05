#!/usr/bin/env python3
"""ASVS 5.0 checklist status: counts per chapter and the release-review gate (ST-078a; G05-07).

Owner: security-privacy-engineer. Documentation tooling, not product code. It reads the
checklist tables (``### V<n> ...`` heading, then rows ``| ID | L | Requirement | Applies |
Status | Owner / story | Verification |``) and checks the rows in scope:

* in scope: chapters named with ``--chapters`` (default all), rows whose L cell is at or below
  ``--level``, plus rows marked "adopted" (the L3 items NFR-050 adopts);
* ``not-assessed`` (NFR-050.1): an applicable row (Applies is not ``N/A``) must be ``Pass`` or
  ``Fail``, and Applies must be decided (``TBD`` is not). Any other status, including the
  Sprint 0 planning statuses (``S0 planned``, ``S1``, ``Later``, ``Open``), is not assessed;
  ``N/A`` is accepted only when Applies is ``N/A`` too;
* ``fail-without-owner`` (NFR-050.4): a ``Fail`` row's Owner cell names a fix ticket id
  (``ST-078d``, ``SEC-5``) or a residual-risk owner (``P19``, ``ADR 0059``);
* ``pass-without-evidence`` (NFR-050.5): a ``Pass`` row's Verification cell names a test id
  (``test_...``, a ``*.py``/``*.spec.ts``/``*.feature`` path, ``IT-nn-nn``) or a command in
  backticks (``grep``, ``uv run pytest``, ``curl``, ...).

Usage:
    python3 docs/security/tools/asvs_status.py docs/security/asvs-l2-checklist.md --level 2 \
        --fail-on not-assessed,fail-without-owner,pass-without-evidence --chapters V1-V5 \
        --json reports/asvs.json

Exit codes: 0 no problem; 1 at least one problem (one ``FAIL`` line each); 2 usage error, file
missing, or no row in scope (never pass empty). Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

RULES = ("not-assessed", "fail-without-owner", "pass-without-evidence")
BUCKETS = ("Pass", "Fail", "N/A", "Not assessed")
CHAPTER = re.compile(r"^### (V(\d+))\b")
ROW = re.compile(r"^\| (\d+\.\d+\.\d+) \|")
NOT_TICKETS = {"NFR", "FR", "IT", "AQS", "ASB", "EP", "DPA", "DOM", "AQ", "OWASP", "ASVS"}
TICKET = re.compile(r"\b([A-Z]{2,})(?:-[A-Z0-9]+)*-\d+[a-z]?\b")
RESIDUAL = re.compile(r"\bP\d+\b|\bADR[ -]\d{4}\b")
TEST_ID = re.compile(r"\btest_\w+|\.(?:py|spec\.ts|test\.ts|test\.tsx|feature)\b|::|\bIT-\d{2}-\d+")
COMMAND = re.compile(
    r"^(?:\(?cd \S+ && )?(?:grep|rg|git|python3?|uv|npm|pnpm|npx|make|curl|docker|pytest)\b"
)
CODE = re.compile(r"`([^`]+)`")


class Row(NamedTuple):
    id: str
    chapter: str
    level: str
    applies: str
    status: str
    owner: str
    verification: str


class Problem(NamedTuple):
    rule: str
    row: Row
    detail: str

    def line(self) -> str:
        return f"FAIL {self.rule}: {self.row.id} ({self.row.chapter}) {self.detail}"


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_rows(text: str) -> list[Row]:
    rows, chapter = [], ""
    for line in text.splitlines():
        if m := CHAPTER.match(line):
            chapter = m.group(1)
        elif chapter and ROW.match(line):
            c = cells(line)
            if len(c) >= 7:
                rows.append(Row(c[0], chapter, c[1], c[3], c[4], c[5], " | ".join(c[6:])))
    return rows


def parse_chapters(spec: str) -> set[str]:
    out: set[str] = set()
    for part in spec.split(","):
        m = re.fullmatch(r"V(\d+)(?:-V(\d+))?", part.strip())
        lo, hi = (int(m.group(1)), int(m.group(2) or m.group(1))) if m else (0, 0)
        if not m or not 1 <= lo <= hi <= 17:
            raise ValueError(f"bad chapter spec {part!r} (want V1-V17, e.g. V1-V5 or V1,V3)")
        out |= {f"V{n}" for n in range(lo, hi + 1)}
    return out


def in_level(row: Row, level: int) -> bool:
    m = re.match(r"\d+", row.level)
    return "adopted" in row.level.lower() or (m is not None and int(m.group(0)) <= level)


def select(rows: list[Row], *, level: int, chapters: set[str] | None) -> list[Row]:
    return [r for r in rows if in_level(r, level) and (chapters is None or r.chapter in chapters)]


def bucket(row: Row) -> str:
    if row.applies == "N/A" and row.status == "N/A":
        return "N/A"
    if row.applies not in ("TBD", "N/A") and row.status in ("Pass", "Fail"):
        return row.status
    return "Not assessed"


def has_owner(row: Row) -> bool:
    tickets = [m.group(1) for m in TICKET.finditer(row.owner)]
    return any(t not in NOT_TICKETS for t in tickets) or bool(RESIDUAL.search(row.owner))


def has_evidence(row: Row) -> bool:
    if re.search(r"\bIT-\d{2}-\d+", row.verification):
        return True
    spans = CODE.findall(row.verification)
    return any(TEST_ID.search(s) or COMMAND.match(s) for s in spans)


def not_assessed(row: Row) -> str | None:
    if bucket(row) != "Not assessed":
        return None
    if row.applies == "TBD":
        return "Applies is 'TBD'"
    if row.status == "N/A":
        return f"status 'N/A' but Applies is '{row.applies}'"
    return f"status '{row.status}'"


def problems(rows: list[Row], rules: tuple[str, ...] | list[str]) -> list[Problem]:
    out = []
    for row in rows:
        if "not-assessed" in rules and (detail := not_assessed(row)):
            out.append(Problem("not-assessed", row, detail))
        if "fail-without-owner" in rules and bucket(row) == "Fail" and not has_owner(row):
            msg = "names no fix ticket id or residual-risk owner (P-n or ADR id)"
            out.append(Problem("fail-without-owner", row, msg))
        if "pass-without-evidence" in rules and bucket(row) == "Pass" and not has_evidence(row):
            msg = "names no evidence command or test id"
            out.append(Problem("pass-without-evidence", row, msg))
    return out


def counts(rows: list[Row]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for row in rows:
        chapter = out.setdefault(row.chapter, {"rows": 0, **dict.fromkeys(BUCKETS, 0)})
        chapter["rows"] += 1
        chapter[bucket(row)] += 1
    return dict(sorted(out.items(), key=lambda kv: int(kv[0][1:])))


def table(per_chapter: dict[str, dict[str, int]]) -> str:
    lines = ["| Chapter | Rows | " + " | ".join(BUCKETS) + " |", "|---" * (len(BUCKETS) + 2) + "|"]
    for chapter, c in per_chapter.items():
        values = " | ".join(str(c[b]) for b in BUCKETS)
        lines.append(f"| {chapter} | {c['rows']} | {values} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path)
    parser.add_argument("--level", type=int, default=2, choices=(1, 2, 3))
    parser.add_argument("--chapters", default="")
    parser.add_argument("--fail-on", default=",".join(RULES))
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    rules = [r.strip() for r in args.fail_on.split(",") if r.strip()]
    if unknown := [r for r in rules if r not in RULES]:
        print(f"usage: unknown --fail-on rule(s) {unknown}; known: {', '.join(RULES)}")
        return 2
    try:
        chapters = parse_chapters(args.chapters) if args.chapters else None
    except ValueError as exc:
        print(f"usage: {exc}")
        return 2
    if not args.file.is_file():
        print(f"FAIL file: {args.file} does not exist")
        return 2
    rows = select(parse_rows(args.file.read_text(encoding="utf-8")), level=args.level,
                  chapters=chapters)  # fmt: skip
    if not rows:
        print("FAIL scope: no checklist row in scope (check --chapters and --level)")
        return 2
    found, per_chapter = problems(rows, rules), counts(rows)
    print(table(per_chapter))
    for problem in found:
        print(problem.line())
    print(f"{len(found)} problem(s)")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "level": args.level, "rules": rules, "ok": not found, "chapters": per_chapter,
            "problems": [{"rule": p.rule, "id": p.row.id, "chapter": p.row.chapter,
                          "line": p.line()} for p in found],
        }  # fmt: skip
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
