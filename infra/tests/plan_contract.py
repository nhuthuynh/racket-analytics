"""FIX-04-1b test support: the closed ``POST /me/plan`` body read from the contract itself.

The rules come from the §2.1 table of docs/architecture/api-sprint-04.md (PE-4), so a harness
that drifts from the contract fails here instead of on the live stack (G04-02 a and c were
unreachable: every POST /me/plan of live_plan.py lacked ``equipment`` and ``level`` -> 422).
Standard library only; no product imports.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from conftest import REPO_ROOT

CONTRACT = REPO_ROOT / "docs" / "architecture" / "api-sprint-04.md"
_CELL = re.compile(r"(?<!\\)\|")  # a cell border; "\|" inside a cell is a literal bar
_RANGE = re.compile(r"integer (\d+)-(\d+)")


@dataclass(frozen=True)
class Field:
    name: str
    required: bool
    rule: str

    def code(self, value: Any) -> str | None:
        """The contract's field code for a present value, None when the value is valid."""
        if self.rule.startswith("integer"):
            if not isinstance(value, int) or isinstance(value, bool):
                return "invalid"
            bounds = _RANGE.match(self.rule)
            low, high = (int(bounds[1]), int(bounds[2])) if bounds else (0, 10**9)
            return None if low <= value <= high else "out_of_range"
        allowed = set(re.findall(r"`([a-z_]+)`", self.rule.split("(")[0]))
        if self.rule.startswith("unique items"):
            if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                return "invalid"
            if not set(value) <= allowed:
                return "unknown_value"
            return "duplicate" if len(set(value)) != len(value) else None
        if not isinstance(value, str):
            return "invalid"
        return None if value in allowed else "unknown_value"


def fields(text: str | None = None) -> dict[str, Field]:
    """The rows of the §2.1 body table, in contract order."""
    text = CONTRACT.read_text() if text is None else text
    section = text.split("### 2.1", 1)[1].split("### 2.2", 1)[0]
    found = {}
    for line in section.splitlines():
        cells = [c.strip() for c in _CELL.split(line.strip())[1:-1]]
        if len(cells) == 3 and re.fullmatch(r"`[a-z_]+`", cells[0]):
            name = cells[0].strip("`")
            found[name] = Field(name, cells[1].startswith("yes"), cells[2])
    return found


def problems(body: Any, table: dict[str, Field] | None = None) -> list[tuple[str | None, str]]:
    """(field, code) pairs the contract gives for this body; [] when it would be accepted."""
    table = fields() if table is None else table
    if not isinstance(body, dict):
        return [(None, "invalid")]
    found: list[tuple[str | None, str]] = []
    found += [(None, "unknown_field")] * bool(set(body) - set(table))
    for name, f in table.items():
        code = f.code(body[name]) if name in body else ("required" if f.required else None)
        found += [(name, code)] if code else []
    return found
