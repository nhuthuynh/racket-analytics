"""Context-map rule 1 (docs/architecture/context-map.md §4; R2-02): a bounded context reads
another context only through that context's published port, never its domain, repository,
ORM models or service.

A module in ``racket.<A>`` may import from ``racket.<B>`` (B != A) only:
* ``racket.<B>.public`` or ``racket.<B>.events`` — the published port of every context;
* ``racket.players.api`` — R1 Open Host Service (the ``CurrentAccount`` dependency);
* ``racket.analysis_jobs.{domain,queue,stage}`` — R7 Open Host Service (job runtime:
  ``JobKey``, ``JobQueue.enqueue``, the ``Stage`` protocol);
* anything in ``racket.sports`` — R5 Published Language (sport plug-ins).
``racket.platform`` is the shared kernel, and ``racket.worker`` / ``racket.migrations`` are
composition roots, so they are not contexts and are not checked as sources.
Scans source text with ``ast``; no module is imported.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.support.paths import BACKEND

pytestmark = pytest.mark.unit

SRC = BACKEND / "src" / "racket"
NOT_CONTEXTS = {"platform", "worker", "migrations"}
PORT_MODULES = {"public", "events"}
OPEN_HOST = {
    "racket.players.api",  # R1
    "racket.analysis_jobs.domain",  # R7
    "racket.analysis_jobs.queue",  # R7
    "racket.analysis_jobs.stage",  # R7
}
PUBLISHED_LANGUAGE = {"sports"}  # R5


def contexts() -> list[str]:
    return sorted(
        p.name
        for p in SRC.iterdir()
        if p.is_dir() and (p / "__init__.py").exists() and p.name not in NOT_CONTEXTS
    )


def imported_modules(path: Path) -> set[str]:
    """Every ``racket.*`` module a file imports. ``from racket.<B> import x`` counts as
    ``racket.<B>.x`` (``x`` is a submodule or a name re-exported from the package root)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            if node.module.count(".") == 1:
                found |= {f"{node.module}.{alias.name}" for alias in node.names}
            else:
                found.add(node.module)
    return {m for m in found if m.startswith("racket.")}


def _allowed(target: str) -> bool:
    parts = target.split(".")
    if parts[1] in NOT_CONTEXTS or parts[1] in PUBLISHED_LANGUAGE:
        return True
    if len(parts) >= 3 and parts[2] in PORT_MODULES:
        return True
    return any(target == m or target.startswith(m + ".") for m in OPEN_HOST)


def violations(path: Path, own_context: str) -> list[str]:
    known = set(contexts())
    return sorted(
        module
        for module in imported_modules(path)
        if module.split(".")[1] != own_context
        and module.split(".")[1] in known
        and not _allowed(module)
    )


def context_files() -> list[tuple[str, Path]]:
    return [(ctx, p) for ctx in contexts() for p in sorted((SRC / ctx).rglob("*.py"))]


def test_the_scanner_finds_contexts() -> None:
    assert {"matches", "video_ingest", "players", "analysis_jobs"} <= set(contexts())
    assert "platform" not in contexts()


def test_scanner_flags_a_reach_into_another_contexts_internals(tmp_path: Path) -> None:
    bad = tmp_path / "service.py"
    bad.write_text(
        "from racket.video_ingest.domain import UploadStatus\n"
        "from racket.video_ingest import repository\n"
        "import racket.players.models\n"
        "from racket.video_ingest.public import media_summary\n"
        "from racket.players.api import CurrentAccount\n"
        "from racket.analysis_jobs.queue import JobQueue\n"
        "from racket.platform.errors import NotFound\n"
        "from racket.matches.domain import Match\n"
    )

    assert violations(bad, own_context="matches") == [
        "racket.players.models",
        "racket.video_ingest.domain",
        "racket.video_ingest.repository",
    ]


def _id(value: object) -> str:
    return str(value.relative_to(SRC)) if isinstance(value, Path) else str(value)


@pytest.mark.parametrize(("context", "path"), context_files(), ids=_id)
def test_a_context_reads_another_only_through_its_published_port(context: str, path: Path) -> None:
    assert violations(path, context) == []
