#!/usr/bin/env python3
"""Fill Hypothesis's local-constants cache before a budgeted run (CI-DOMAIN-BUDGET, ADR 0049).

A fresh checkout has no .hypothesis/constants, so each xdist worker's first example parsed every
local module (~1.3 s per worker; PE-R1-DB-01). This collects the same selection in one process and
draws one example. It runs no test and changes no generated value (the cache is keyed by source).
Usage (in backend): warm_hypothesis_constants.py PYTEST_ARGS...  Exit: pytest's; 3 if no cache.
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
