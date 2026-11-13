"""Planted-break helpers for CI-DOC-CHECK-06 (PRC-11.1-11.3, ADR 0056 required ticket b): a sources
register, reference set files, threat notes with their checker, and ticket decisions files, written
into the doc_check_repo.py fixture repository (or a clone of the real one) by each test."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from conftest import REPO_ROOT
from doc_check_repo import write

COST_SCRIPT = REPO_ROOT / "scripts" / "ci" / "check_cost_table.py"
THREAT_TOOL = REPO_ROOT / "docs" / "security" / "tools" / "check_threat_notes.py"
SOURCES = "docs/domain/sources.md"

SOURCES_TEXT = """# Sources register (domain citations)

## 2. Register

| Id | Source | Locator | Claim kind | Used for | Resolve status | Evidence |
|---|---|---|---|---|---|---|
| SRC-0001 | QD table | `scripts/ci/tool.py` | definition | formulas | `resolved` | read |
| SRC-0002 | Rulebook | none on file | rule | rules | `exists-unfetched` | blocked |
"""

THREAT_ROW_OK = "| T6-FT-1 | S | Footage without rights | Gate G1 | V2 | ST-175a | IT-06-08 | D |"
THREAT_ROW_NO_STATUS = (
    "| T6-FT-1 | S | Footage without rights | Gate G1 | V2 | ST-175a | IT-06-08 | |"
)

COST_TABLE = """## Cost per PR

| Round | Tokens or total_cost_usd | Wall time |
|---|---|---|
| implement | not measured | 40 min |
"""


def reference(*citations: str | None, footage: str | None = None) -> str:
    """A reference set file whose entries cite the given ids (None: a footage-sourced entry)."""
    entries = []
    for i, cid in enumerate(citations):
        source: dict[str, str | None] = {"citation_id": cid}
        if cid is None:
            source["footage_id"] = footage or "FT-0001"
        entries.append(
            {"pattern_id": f"AN-{8 + i:02d}", "source_type": "judgment", "source": source}
        )
    return json.dumps({"set": "planted", "version": 1, "entries": entries}, indent=2) + "\n"


def threat_notes(row: str, sprint: str = "06") -> str:
    return (
        f"# Threat notes sprint {sprint}\n\n## 2. Footage\n\n"
        "| Id | STRIDE | Threat | Control | ASVS | Ticket | Test | Status |\n"
        "|---|---|---|---|---|---|---|---|\n"
        f"{row.replace('T6-', f'T{int(sprint)}-')}\n"
    )


def add_threat_tool(root: Path) -> None:
    (root / "docs/security/tools").mkdir(parents=True, exist_ok=True)
    (root / "docs/decisions").mkdir(parents=True, exist_ok=True)
    shutil.copy(THREAT_TOOL, root / "docs/security/tools/check_threat_notes.py")
    write(root, "docs/decisions/README.md", "# Decisions\n")


def run_cost(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(COST_SCRIPT), "--root", str(root), *args],
        capture_output=True,
        text=True,
        timeout=60,
        env={"PATH": "/usr/bin:/bin"},
    )
