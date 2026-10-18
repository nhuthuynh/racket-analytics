"""The drill library as the eval reads it (ST-060): every ``<id>/v<n>.json`` document by
``id@version`` for the graders, the domain ``Drill`` values for the planner, and a
``library_version`` (sha256 of the canonical documents)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from racket.coaching.drills.lock import LOCK_NAME
from racket.coaching.plan.domain import Drill


@dataclass(frozen=True, slots=True)
class EvalLibrary:
    root: str
    docs: Mapping[str, Mapping[str, Any]]
    drills: tuple[Drill, ...]
    version: str


def find_repo(start: Path) -> Path | None:
    """The nearest ancestor holding ``content/drills/library.lock``."""
    for parent in (start, *start.parents):
        if (parent / "content" / "drills" / LOCK_NAME).is_file():
            return parent
    return None


def load_library(root: Path) -> EvalLibrary:
    if not root.is_dir():
        raise FileNotFoundError(f"{root}: no such drill library")
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(root.glob("*/v*.json"))]
    blob = json.dumps(docs, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return EvalLibrary(
        root=str(root),
        docs={f"{d['id']}@{d['version']}": d for d in docs},
        drills=tuple(Drill.from_document(d) for d in docs),
        version="sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest(),
    )
