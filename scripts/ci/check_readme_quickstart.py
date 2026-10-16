#!/usr/bin/env python3
"""MVP-01: the README's "Run it locally" section names only real make targets and Compose settings.

Usage: check_readme_quickstart.py [--readme README.md] [--repo .]
Exit 0 when the section exists, every `make <target>` it shows in code is a documented Makefile
target (one with `## help`), and every `VAR=value` it sets before `make` is read by
infra/compose.yaml. Exit 1 with one line per problem otherwise.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SECTION = "## Run it locally"
_CODE = re.compile(r"```[^\n]*\n(.*?)```|`([^`\n]+)`", re.S)
_MAKE = re.compile(r"(?:^|[\s$;&|])make((?:[ \t]+[a-z][\w-]*)+)", re.M)
_ASSIGN = re.compile(r"(?:^|[\s$])([A-Z][A-Z0-9_]*)=\S*[ \t]+make\b", re.M)
_TARGET = re.compile(r"^([A-Za-z0-9_-]+):[^=\n]*?##", re.M)


def quick_start_section(readme: str) -> str:
    """The text from the section heading up to the next heading of the same or higher level."""
    lines = readme.splitlines()
    try:
        start = lines.index(SECTION)
    except ValueError:
        return ""
    after = range(start + 1, len(lines))
    end = next((i for i in after if re.match(r"#{1,2} ", lines[i])), len(lines))
    return "\n".join(lines[start:end]) + "\n"


def _code(section: str) -> str:
    return "\n".join(block or span for block, span in _CODE.findall(section))


def make_targets_named(section: str) -> list[str]:
    """Targets of every `make ...` command written in code spans or blocks, in order."""
    return [t for m in _MAKE.finditer(_code(section)) for t in m.group(1).split()]


def makefile_targets(makefile: str) -> set[str]:
    """Targets documented with `## help` (the ones `make help` lists)."""
    return set(_TARGET.findall(makefile))


def problems(readme: str, makefile: str, compose: str) -> list[str]:
    section = quick_start_section(readme)
    if not section:
        return [f"README has no '{SECTION}' section"]
    known = makefile_targets(makefile)
    out = [
        f"README names `make {t}` but the Makefile has no documented `{t}` target"
        for t in dict.fromkeys(make_targets_named(section))
        if t not in known
    ]
    out += [
        f"README sets `{v}` but infra/compose.yaml does not read it"
        for v in dict.fromkeys(_ASSIGN.findall(_code(section)))
        if "${" + v not in compose
    ]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--readme", type=Path)
    a = ap.parse_args(argv)
    readme = (a.readme or a.repo / "README.md").read_text()
    makefile = (a.repo / "Makefile").read_text()
    found = problems(readme, makefile, (a.repo / "infra/compose.yaml").read_text())
    for p in found:
        print(f"readme-quickstart: {p}")
    if not found:
        print("readme-quickstart: ok")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
