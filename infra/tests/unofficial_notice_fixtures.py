"""Shared helpers for the FIX-03-2c tests: load the checker, build small plan/dictionary texts."""

from __future__ import annotations

import importlib.util
import sys
from types import ModuleType

from conftest import REPO_ROOT, SCRIPTS_DIR

SCRIPT = SCRIPTS_DIR / "measure" / "unofficial_notice.py"
PLAN = REPO_ROOT / "docs" / "sprints" / "sprint-03.md"
DICTIONARY = REPO_ROOT / "docs" / "domain" / "metric-dictionary.md"

OLD_WORDS = 'the score sheet and every metric card say "unofficial"'
NEW_WORDS = 'the score sheet and every stats page say "unofficial", once before the first card'


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("unofficial_notice", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["unofficial_notice"] = module
    spec.loader.exec_module(module)
    return module


def plan(words: str | None) -> str:
    if words is None:
        return "### 0.2 Product-owner decisions applied\n\n- **Accept all recommendations.** x\n"
    return (
        "### 0.2 Product-owner decisions applied\n\n"
        f"- **Rulebook PDFs later (OQ-01).** Presets stay `PROVISIONAL-UNVERIFIED`; {words}. "
        "Rule-dependent metric rows count toward no Must FR (QD-QG-P5).\n"
    )


def dictionary(words: str) -> str:
    return (
        "## 0. Rules\n\n"
        "5. **Rules dependence:** while that is `PROVISIONAL-UNVERIFIED`, the stats page carries "
        'the same "unofficial scoring (rules not yet verified)" notice as the score sheet, '
        f"{words}.\n"
        "6. **Versioning:** x\n"
    )
