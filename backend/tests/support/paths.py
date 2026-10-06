"""Repository paths used by tests."""

from __future__ import annotations

from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
REPO = BACKEND.parent
FEATURES = REPO / "tests" / "features"
FIXTURES = REPO / "fixtures"
SYNTHETIC_60S = FIXTURES / "clips" / "synthetic-60s"
SYNTHETIC_CLIP = SYNTHETIC_60S / "clip.mp4"
LONG_4H = FIXTURES / "clips" / "long-4h"
LONG_4H_CLIP = LONG_4H / "clip.mp4"
