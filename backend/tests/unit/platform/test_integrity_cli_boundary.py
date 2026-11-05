"""ST-076b (PE-PLAN05-05; context map C4, rule 1): the ``racket-integrity`` CLI in platform
reads the corrections only through Match & Scoring's port. ``racket.platform.integrity``
imports ``corrections_fingerprint`` from ``racket.matches.public`` and nothing else of
``racket.matches``; no ``racket.matches.scorebook`` module; it never names the corrections
table. Static scan with ``ast`` (importing would load the port's own scorebook imports).
Also: usage and configuration errors exit 2 without touching a database.
"""

from __future__ import annotations

import ast
import tomllib

import pytest

from tests.support.paths import BACKEND

pytestmark = pytest.mark.unit

CLI = BACKEND / "src" / "racket" / "platform" / "integrity.py"
PORT = BACKEND / "src" / "racket" / "matches" / "public.py"


def boundary_violations(source: str) -> list[str]:
    """What in ``source`` breaks the rule; empty when it holds."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found += [f"import {a.name}" for a in node.names if a.name.startswith("racket.matches")]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module == "racket.matches.public":
                found += [
                    f"from racket.matches.public import {a.name}"
                    for a in node.names
                    if a.name != "corrections_fingerprint"
                ]
            elif node.module == "racket.matches" or node.module.startswith("racket.matches."):
                found.append(f"from {node.module} import ...")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "match_corrections" in node.value:
                found.append("names the match_corrections table")
    return found


def test_the_cli_imports_only_corrections_fingerprint_from_the_port() -> None:
    source = CLI.read_text(encoding="utf-8")
    assert boundary_violations(source) == []
    assert "from racket.matches.public import corrections_fingerprint" in source


@pytest.mark.parametrize(
    "planted",
    [
        "from racket.matches.scorebook.integrity import corrections_fingerprint\n",
        "from racket.matches.scorebook import repository\n",
        "import racket.matches.scorebook.repository\n",
        "from racket.matches import public\n",
        "from racket.matches.public import corrections_fingerprint, purge_match\n",
        "QUERY = 'SELECT count(*) FROM match_corrections'\n",
    ],
    ids=["direct-integrity", "scorebook-repository", "import-scorebook", "whole-port",
         "second-export", "reads-table"],  # fmt: skip
)
def test_a_planted_direct_import_or_table_read_fails_the_check(planted: str) -> None:
    source = CLI.read_text(encoding="utf-8") + planted
    assert boundary_violations(source) != []


def test_the_port_publishes_corrections_fingerprint_from_the_scorebook_module() -> None:
    tree = ast.parse(PORT.read_text(encoding="utf-8"))
    imported = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "racket.matches.scorebook.integrity"
    ]
    assert [[a.name for a in n.names] for n in imported] == [["corrections_fingerprint"]]


def test_racket_integrity_is_a_console_script() -> None:
    project = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["scripts"]["racket-integrity"] == "racket.platform.integrity:main"


def test_usage_errors_exit_2(monkeypatch: pytest.MonkeyPatch) -> None:
    from racket.platform import integrity

    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody@127.0.0.1:1/none")
    assert integrity.main(["--expect-count", "x", "--expect-sha256", "0" * 64]) == 2
    assert integrity.main(["--expect-count", "3"]) == 2  # both expectations or neither
    assert integrity.main(["--expect-count", "3", "--expect-sha256", "zz"]) == 2
    assert integrity.main(["--expect-count", "-1", "--expect-sha256", "0" * 64]) == 2
    assert integrity.main(["--nope"]) == 2


def test_missing_database_url_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    from racket.platform import integrity

    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert integrity.main([]) == 2
