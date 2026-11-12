"""ST-084b acceptance: the rally F1 matcher is pure, with no I/O. Kept apart from
``test_rally_f1.py`` because the nightly mutation run rewrites the module (mutmut adds its own
import), and this file reads the module's source text."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import racket.dataset.rally_f1 as rally_f1_module

pytestmark = pytest.mark.unit

ALLOWED = {"__future__", "collections", "dataclasses", "math", "typing"}


def test_the_matcher_imports_only_pure_standard_modules_and_opens_nothing() -> None:
    source = Path(rally_f1_module.__file__).read_text()
    tree = ast.parse(source)
    imported = {
        a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    imported |= {
        n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module
    }
    assert imported <= ALLOWED
    called = {
        n.func.id
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    }
    assert not called & {"open", "print", "input", "exec", "eval", "__import__"}
