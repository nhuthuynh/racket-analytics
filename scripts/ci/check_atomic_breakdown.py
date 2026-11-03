#!/usr/bin/env python3
"""QA-DOR-CHECK (PRC-7.1, ADR 0056): the Definition of Ready "atomic breakdown" rules as a check.

Usage:
    check_atomic_breakdown.py [--root DIR] [FILE ...]

With no FILE, it checks the current sprint's breakdown: the highest NN of
`docs/sprints/sprint-<nn>.md` gives `docs/sprints/<nn>/requirements-breakdown.md`; while that file
does not exist it prints `skipped (PRC-7.1)` and exits 0. The ci.yml `doc-check` job runs it so.

A breakdown fails on:
- `nfr`: a row of an `Id` table whose id starts `NFR-` that lacks a metric, a method, a target or a
  test level. Each comes from a non-empty cell (`—`/`-` are empty) of a column whose header names
  it (`Metric…`, `Method`, `Target`, `Test level`). A `Rule…` column holds a pass/fail behaviour,
  which is its own metric, method and target. A section line opening `Method…:` or
  `Common method…:` gives the method, and `Each item = …` the metric and method, for the rows of
  that `##`/`###` section only.
- `fr`: a Gherkin `Rule:` line (inside a ```gherkin fence) with no `Example:` line marked
  `(negative…` before the next `Rule:` or the end of the fence.
- `id`: a first cell of an `Id` table that `measurelib._FINDING_ID` does not match in full, or a
  `Rule:` id that is not `FR-nnn.R<k>` with a base `FR-nnn` that `_FINDING_ID` matches in full
  (the two formats agreed in the breakdown's header, retro 4 M15).
A file with no item at all fails closed. Exit codes: 0 pass, 1 problems, 2 usage (missing file).
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "measure"))
from measurelib import _FINDING_ID

ATTRIBUTES = ("metric", "method", "target", "test level")
_EMPTY = {"", "\u2014", "\u2013", "-"}  # em dash, en dash, hyphen
_SECTION_METHOD = re.compile(r"(?:^|\.\s+)(?:Common method|Method)\b[^:\n]*:", re.I)
_SECTION_EACH_ITEM = re.compile(r"\bEach item\s*=")
_RULE_ID = re.compile(r"(FR-\d{3})\.R\d+")
_NEGATIVE = re.compile(r"\(negative\b", re.I)


@dataclass
class Section:
    covers: set[str] = field(default_factory=set)
    rows: list[tuple[int, dict[str, str], list[str]]] = field(default_factory=list)


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _plain(cell: str) -> str:
    return cell.replace("**", "").replace("`", "").strip()


def _column_attribute(header: str) -> set[str]:
    h = header.lower()
    if h.startswith("rule"):
        return {"metric", "method", "target"}
    return {a for a in ATTRIBUTES if a in h}


def _sections(lines: list[str]) -> Iterator[Section]:
    """Split by `##`/`###` headings; collect `Id` table rows and section-wide attribute lines."""
    section = Section()
    header: list[str] | None = None
    fence = False
    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if stripped.startswith("#"):
            yield section
            section, header = Section(), None
            continue
        if not stripped.startswith("|"):
            header = None
            if _SECTION_METHOD.search(stripped):
                section.covers.add("method")
            if _SECTION_EACH_ITEM.search(stripped):
                section.covers |= {"metric", "method"}
            continue
        cells = _cells(stripped)
        if header is None:
            header = cells
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        if _plain(header[0]).lower() == "id":
            section.rows.append((number, dict(zip(header, cells, strict=False)), cells))
    yield section


def _id_ok(item: str) -> bool:
    return _FINDING_ID.fullmatch(item) is not None


def check_text(text: str, label: str) -> list[str]:
    lines = text.splitlines()
    problems: list[str] = []
    items = 0

    for section in _sections(lines):
        for number, row, cells in section.rows:
            items += 1
            item = _plain(cells[0])
            where = f"{label}:{number}"
            if not _id_ok(item):
                problems.append(f"FAIL id: {where}: id {item} is not a parseable item id")
            if not item.startswith("NFR-"):
                continue
            have = set(section.covers)
            for header, value in row.items():
                if _plain(value) not in _EMPTY:
                    have |= _column_attribute(header)
            problems += [
                f"FAIL nfr: {where}: {item} has no {a}" for a in ATTRIBUTES if a not in have
            ]

    fence = False
    rule: tuple[int, str] | None = None
    negative = False

    def close() -> None:
        if rule and not negative:
            problems.append(f"FAIL fr: {label}:{rule[0]}: {rule[1]} has no negative Example")

    for number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("```"):
            if fence:
                close()
                rule = None
            fence = not fence
            continue
        if not fence:
            continue
        if stripped.startswith("Rule:"):
            close()
            items += 1
            rule_id = (stripped[len("Rule:") :].split() or [""])[0]
            rule, negative = (number, rule_id), False
            base = _RULE_ID.fullmatch(rule_id)
            if not base or not _id_ok(base.group(1)):
                problems.append(
                    f"FAIL id: {label}:{number}: id {rule_id} is not FR-nnn.R<k> "
                    "with a parseable base"
                )
        elif rule and stripped.startswith("Example:") and _NEGATIVE.search(stripped):
            negative = True
    close()

    if items == 0:
        problems.append(f"FAIL empty: {label}: no items (no Id table rows, no Gherkin Rule: lines)")
    return problems


def current_breakdown(root: Path) -> Path | None:
    plans = sorted((root / "docs" / "sprints").glob("sprint-[0-9][0-9].md"))
    if not plans:
        return None
    sprint = plans[-1].stem.split("-")[1]
    return root / "docs" / "sprints" / sprint / "requirements-breakdown.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("files", nargs="*", type=Path)
    args = parser.parse_args(argv)

    files = args.files
    if not files:
        current = current_breakdown(args.root)
        if current is None or not current.is_file():
            print("atomic breakdown: skipped (PRC-7.1): no current sprint breakdown yet")
            return 0
        files = [current]

    problems: list[str] = []
    for path in files:
        if not path.is_file():
            print(f"usage: {path} does not exist", file=sys.stderr)
            return 2
        label = str(path.relative_to(args.root)) if path.is_relative_to(args.root) else str(path)
        problems += check_text(path.read_text(encoding="utf-8"), label)

    for problem in problems:
        print(problem)
    print(f"atomic breakdown: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
