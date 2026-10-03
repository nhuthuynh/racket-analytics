"""Domain code stays framework-free (ddd-guidelines §4.5; QD-TR-01: importable without the API,
DB, GPU or network). Scans source text, so it needs no imports of the modules themselves."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.support.paths import BACKEND

pytestmark = pytest.mark.unit

SRC = BACKEND / "src" / "racket"
FORBIDDEN = {
    "fastapi", "starlette", "sqlalchemy", "alembic", "psycopg", "pydantic", "pydantic_settings",
    "httpx", "boto3", "botocore", "opentelemetry", "uvicorn", "requests",
}  # fmt: skip


def domain_modules() -> list[Path]:
    """Files that hold domain logic: any ``domain.py`` / ``domain/`` package, the sport plug-ins,
    and the pure dataset manifest module."""
    found = [
        p
        for p in SRC.rglob("*.py")
        if p.name == "domain.py" or "domain" in p.relative_to(SRC).parts[:-1]
    ]
    found += list((SRC / "sports").rglob("*.py"))
    found.append(SRC / "dataset" / "manifest.py")
    return sorted(set(found))


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("path", domain_modules(), ids=lambda p: str(p.relative_to(SRC)))
def test_domain_module_imports_no_framework(path: Path) -> None:
    assert imported_roots(path) & FORBIDDEN == set()


def test_scanner_detects_a_forbidden_import(tmp_path: Path) -> None:
    bad = tmp_path / "domain.py"
    bad.write_text("from sqlalchemy.orm import Session\nimport fastapi\n")

    assert imported_roots(bad) & FORBIDDEN == {"sqlalchemy", "fastapi"}
