#!/usr/bin/env python3
"""Fill Hypothesis's local-constants cache before a time-budgeted run (CI-DOMAIN-BUDGET, ADR 0049).

On the first example in a process, Hypothesis parses every loaded local module for constants and
caches them under .hypothesis/constants, keyed by source hash. A fresh CI checkout has no cache,
so each xdist worker parses the whole tree (~1.3 s per worker locally, PE-R1-DB-01). This
collects the same selection in one process (importing the same modules) and draws one example,
so the budgeted run reads the cache. It runs no test and changes no generated values.

Usage (in backend, with its env): warm_hypothesis_constants.py PYTEST_ARGS...
Exit: pytest's collection exit code; 3 when the cache stays empty.
"""

from __future__ import annotations

import sys

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.configuration import storage_directory


@settings(max_examples=1, database=None)
@given(st.text())
def _draw(_: str) -> None:
    """One example: Hypothesis scans the modules collection imported."""


def main(argv: list[str]) -> int:
    rc = pytest.main(["-q", "--collect-only", "-p", "no:cacheprovider", *argv])
    if rc != 0:
        return int(rc)
    _draw()
    cache = storage_directory("constants", intent_to_write=False).path
    files = [p for p in cache.glob("*") if not p.name.startswith(".")] if cache.is_dir() else []
    print(f"warm: {len(files)} Hypothesis constants cache entries in {cache}")
    return 0 if files else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
