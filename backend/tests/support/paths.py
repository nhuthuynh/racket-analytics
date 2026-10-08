"""Repository paths used by tests."""

from __future__ import annotations

from pathlib import Path


def repo_root(start: Path) -> Path:
    """Nearest ancestor of ``start`` that holds both ``docs/`` and ``backend/``.

    ``BACKEND.parent`` is not enough: mutmut 3 runs the tests from a copy in ``backend/mutants/``,
    where it would point at ``backend/`` (VR1-S3-01). Raises ``LookupError`` when there is none.
    """
    for parent in start.resolve().parents:
        if (parent / "docs").is_dir() and (parent / "backend").is_dir():
            return parent
    raise LookupError(f"no repository root (docs/ and backend/) above {start}")


BACKEND = Path(__file__).resolve().parents[2]  # the tree the tests run from (a mutmut copy too)
REPO = repo_root(Path(__file__))
FEATURES = REPO / "tests" / "features"
FIXTURES = REPO / "fixtures"
SYNTHETIC_60S = FIXTURES / "clips" / "synthetic-60s"
SYNTHETIC_CLIP = SYNTHETIC_60S / "clip.mp4"
LONG_4H = FIXTURES / "clips" / "long-4h"
LONG_4H_CLIP = LONG_4H / "clip.mp4"
