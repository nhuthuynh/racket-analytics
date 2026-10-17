#!/usr/bin/env python3
"""Fill Hypothesis's local-constants cache before a budgeted run (CI-DOMAIN-BUDGET, ADR 0049).

A fresh checkout has no .hypothesis/constants, so each xdist worker's first example parsed every
local module (~1.3 s per worker; PE-R1-DB-01). This collects the same selection in one process,
imports the rest of each source package collection touched (a test can import a module inside a
function: create_app() imports every router; PR #111 run 39073707402 left 26 of 110 entries to
the workers), and runs Hypothesis's local-constants scan. It runs no test and changes no
generated value (the cache is keyed by source; each worker still scans only what it imported).
Usage (in backend): warm_hypothesis_constants.py PYTEST_ARGS...  Exit: pytest's; 3 if no cache.
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from types import ModuleType

import pytest
from hypothesis.configuration import storage_directory
from hypothesis.internal.conjecture.providers import _get_local_constants
from hypothesis.internal.constants_ast import is_local_module_file


class _Collected:
    """Records the modules of the collected test files (pytest plugin)."""

    def __init__(self) -> None:
        self.test_modules: set[str] = set()

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        for item in session.items:
            module = getattr(item, "module", None)
            if module is not None:
                self.test_modules.add(module.__name__)


def _local(module: ModuleType) -> bool:
    path = getattr(module, "__file__", None)
    return path is not None and is_local_module_file(path)


def import_source_packages(test_modules: set[str]) -> tuple[int, int]:
    """Import every submodule of each local top-level package collection imported, except the
    packages that hold collected tests. Returns (imported, failed); a module that cannot be
    imported outside its runtime (e.g. an Alembic env.py) is skipped, as the workers skip it."""
    test_roots = {name.split(".")[0] for name in test_modules}
    roots = sorted(
        name
        for name, module in list(sys.modules.items())
        if "." not in name and name not in test_roots and hasattr(module, "__path__")
        and _local(module)
    )  # fmt: skip
    imported = failed = 0
    for root in roots:
        package = sys.modules[root]
        for info in pkgutil.walk_packages(package.__path__, f"{root}.", onerror=lambda _: None):
            try:
                importlib.import_module(info.name)
                imported += 1
            except Exception:  # noqa: BLE001 - warming is best effort; the run parses it anyway
                failed += 1
    return imported, failed


def main(argv: list[str]) -> int:
    collected = _Collected()
    rc = pytest.main(["-q", "--collect-only", "-p", "no:cacheprovider", *argv], plugins=[collected])
    if rc != 0:
        return int(rc)
    imported, failed = import_source_packages(collected.test_modules)
    print(f"warm: imported {imported} source modules ({failed} not importable here)")
    # The scan a worker's first example runs (writes one cache entry per local source module).
    # Called directly: a single drawn example may not reach it (no entry in a bare project).
    _get_local_constants()
    cache = storage_directory("constants", intent_to_write=False).path
    files = [p for p in cache.glob("*") if not p.name.startswith(".")] if cache.is_dir() else []
    print(f"warm: {len(files)} Hypothesis constants cache entries in {cache}")
    return 0 if files else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
