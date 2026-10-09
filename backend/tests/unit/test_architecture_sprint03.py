"""The framework-free guard of ``test_architecture.py`` extended to the Sprint 3 domain code
(QA-R1S3-11; ddd-guidelines §4.5; analytics-snapshots.md §8).

``test_architecture.domain_modules()`` finds ``domain.py``/``domain/`` packages, the sport
plug-ins and the dataset manifest. The Sprint 3 domain code does not follow the ``domain``
naming, so it is listed here by context:

- ``racket/analytics/``: every module except the adapter modules (``ADAPTER_MODULES``: the same
  names the other contexts use for HTTP, persistence, application services and public
  interfaces), so the ``MetricSnapshot`` code of ST-046 is scanned the day it lands;
- ``racket/coaching/drills/``: every module (schema, rules, lock, the lint CLI);
- ``racket/dataset/full_tag.py`` and the ``labels.py`` it builds on.

A new file in these places is scanned without a change here. The accepted Sprint 0 test file
is not edited (TCR row 2026-10-07, principal-engineer).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.test_architecture import FORBIDDEN, SRC, imported_roots

pytestmark = pytest.mark.unit

ADAPTER_MODULES = frozenset(
    {"api.py", "repository.py", "service.py", "schemas.py", "public.py", "worker.py"}
)
WHOLE_PACKAGES = (("analytics",), ("coaching", "drills"))
SINGLE_FILES = (("dataset", "full_tag.py"), ("dataset", "labels.py"))


def sprint_03_domain_modules(root: Path = SRC) -> list[Path]:
    found: list[Path] = []
    for parts in WHOLE_PACKAGES:
        package = root.joinpath(*parts)
        found += [p for p in package.rglob("*.py") if p.name not in ADAPTER_MODULES]
    found += [root.joinpath(*parts) for parts in SINGLE_FILES]
    return sorted(set(found))


def _tree(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def test_a_new_analytics_module_with_a_framework_import_is_caught(tmp_path: Path) -> None:
    """Negative case first: a snapshot module that imports SQLAlchemy is scanned and fails."""
    _tree(
        tmp_path,
        {
            "analytics/snapshot.py": "import sqlalchemy as sa\n",
            "analytics/repository.py": "import sqlalchemy as sa\n",
            "coaching/drills/new_rule.py": "from pydantic import BaseModel\n",
            "dataset/full_tag.py": "",
            "dataset/labels.py": "",
        },
    )

    scanned = {p.relative_to(tmp_path).as_posix() for p in sprint_03_domain_modules(tmp_path)}

    assert "analytics/snapshot.py" in scanned
    assert "coaching/drills/new_rule.py" in scanned
    assert "analytics/repository.py" not in scanned  # an adapter may use the framework
    assert imported_roots(tmp_path / "analytics" / "snapshot.py") & FORBIDDEN == {"sqlalchemy"}


def test_the_sprint_03_domain_files_that_exist_today_are_scanned() -> None:
    scanned = {p.relative_to(SRC).as_posix() for p in sprint_03_domain_modules()}

    assert {
        "analytics/starter_stats.py",
        "analytics/uncertainty.py",
        "analytics/attribution.py",
        "analytics/sheet.py",
        "dataset/full_tag.py",
        "dataset/labels.py",
        "coaching/drills/rules.py",
        "coaching/drills/lock.py",
        "coaching/drills/schema_check.py",
        "coaching/drills/lint.py",
    } <= scanned
    assert all(p.exists() for p in sprint_03_domain_modules())


@pytest.mark.parametrize("path", sprint_03_domain_modules(), ids=lambda p: str(p.relative_to(SRC)))
def test_sprint_03_domain_module_imports_no_framework(path: Path) -> None:
    assert imported_roots(path) & FORBIDDEN == set()
