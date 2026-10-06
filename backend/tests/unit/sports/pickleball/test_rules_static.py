"""IT-01-12 and IT-01-13 (ST-020; NFR-079; QD-TR-01; docs/architecture/scoring-engine.md §1).

IT-01-12: no rule value as a literal in the rules engine outside ``presets.py`` (the engine
compares against ``config.*`` fields only). Allowed everywhere: 0 and 1; in ``state.py`` the
named server-number constants ``FIRST_SERVER`` and ``SECOND_SERVER``.
IT-01-13: the rules engine imports only the standard-library modules the design allows, and
nothing from ``racket.platform``, the DB, HTTP, time, randomness or I/O.

Each scanner has a positive control on a temporary file (testing-strategy rule 8). The scans
of the real package are RED until ST-020 creates it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.support import contract
from tests.support.paths import BACKEND

pytestmark = pytest.mark.scoring

RULES = BACKEND / contract.RULES_PACKAGE_DIR
ALLOWED_IMPORTS = {
    "__future__",
    "dataclasses",
    "enum",
    "types",
    "typing",
    "collections",
    "functools",
}
ALLOWED_NUMBERS = {0, 1}
NAMED_CONSTANTS = {"FIRST_SERVER", "SECOND_SERVER"}
LITERAL_FILES_ALLOWED = {"presets.py"}


def rules_files() -> list[Path]:
    if RULES.is_dir():
        return sorted(RULES.rglob("*.py"))
    module = RULES.with_suffix(".py")
    if module.is_file():
        return [module]
    pytest.fail(
        f"RED until ST-020: the rules engine {contract.RULES_PACKAGE_DIR} does not exist yet",
        pytrace=False,
    )


def forbidden_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    bad: set[str] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        for name in names:
            root = name.split(".")[0]
            own = name.startswith("racket.sports.pickleball.rules")
            if root not in ALLOWED_IMPORTS and not own:
                bad.add(name)
    return bad


def rule_literals(path: Path) -> list[str]:
    if path.name in LITERAL_FILES_ALLOWED:
        return []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    exempt: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign | ast.AnnAssign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id in NAMED_CONSTANTS for t in targets):
                exempt |= {id(n) for n in ast.walk(node)}
    found = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, int | float)
            and not isinstance(node.value, bool)
            and node.value not in ALLOWED_NUMBERS
            and id(node) not in exempt
        ):
            found.append(f"{path.name}:{node.lineno}: {node.value!r}")
    return found


# ------------------------------------------------------------------ positive controls
def test_import_scanner_flags_platform_time_and_io(tmp_path: Path) -> None:
    bad = tmp_path / "engine.py"
    bad.write_text(
        "from __future__ import annotations\nimport datetime\nimport random\n"
        "from racket.platform.db import get_session\nfrom dataclasses import dataclass\n"
        "from racket.sports.pickleball.rules.config import RulesConfig\nfrom . import state\n"
    )
    assert forbidden_imports(bad) == {"datetime", "random", "racket.platform.db"}


def test_literal_scanner_flags_rule_values_but_not_presets_or_named_servers(tmp_path: Path) -> None:
    engine = tmp_path / "engine.py"
    engine.write_text("def over(a, b):\n    return a >= 11 and a - b >= 2 and b >= 0\n")
    state = tmp_path / "state.py"
    state.write_text("FIRST_SERVER = 1\nSECOND_SERVER: int = 2\nx = 1\n")
    presets = tmp_path / "presets.py"
    presets.write_text("TARGET = 11\nMARGIN = 2\n")
    assert rule_literals(engine) == ["engine.py:2: 11", "engine.py:2: 2"]
    assert rule_literals(state) == []
    assert rule_literals(presets) == []


# ------------------------------------------------------------------ the real package
def test_it_01_13_rules_engine_imports_nothing_but_the_allowed_stdlib() -> None:
    problems = {str(p.relative_to(BACKEND)): forbidden_imports(p) for p in rules_files()}
    assert {k: v for k, v in problems.items() if v} == {}


def test_it_01_12_no_rule_literal_outside_presets() -> None:
    found = [hit for p in rules_files() for hit in rule_literals(p)]
    assert found == []


def test_presets_hold_the_provisional_preset() -> None:
    files = {p.name for p in rules_files()}
    assert "presets.py" in files or RULES.with_suffix(".py").is_file()
