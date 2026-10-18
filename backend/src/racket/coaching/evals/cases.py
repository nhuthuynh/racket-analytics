"""Eval cases (ST-060): a synthetic Quick Tag script per match, the player's side in it, plan
preferences and the expected outcome (``plan`` or a refusal reason such as ``no_plan_fits``)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

OUTCOMES = frozenset({"plan", "no_plan_fits", "no_weakness"})


class CaseError(ValueError):
    """A case file that cannot be read or is not an eval case."""


@dataclass(frozen=True, slots=True)
class EvalCase:
    id: str
    description: str
    preferences: Mapping[str, Any]
    matches: tuple[Mapping[str, Any], ...]  # {"format", "best_of", "side", "games": [...]}
    expect: str = "plan"


def load_case(path: Path) -> EvalCase:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        case = EvalCase(
            id=str(doc["id"]),
            description=str(doc.get("description", "")),
            preferences=dict(doc["preferences"]),
            matches=tuple(dict(m) for m in doc["matches"]),
            expect=str(doc.get("expect", "plan")),
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CaseError(f"{path.name}: not an eval case ({type(exc).__name__}: {exc})") from exc
    if case.expect not in OUTCOMES:
        raise CaseError(f"{path.name}: expect {case.expect!r} is not one of {sorted(OUTCOMES)}")
    if case.id != path.stem:
        raise CaseError(f"{path.name}: id {case.id!r} is not the file name")
    return case


def load_cases(root: Path) -> list[EvalCase]:
    """Every ``*.json`` case under ``root``, in id order."""
    if not root.is_dir():
        raise CaseError(f"{root}: no such case directory")
    return [load_case(p) for p in sorted(root.glob("*.json"))]
