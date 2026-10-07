"""Rule L11 / IT-03-12 regression (goal round 1): any JSON value in a label's ``type`` is a
refusal, never a crash. An unhashable value (a list or an object) raised ``TypeError`` from the
membership test, which the API answered with 500."""

from __future__ import annotations

from typing import Any

import pytest

from racket.dataset.full_tag import FullTagSession, LabelRefused

pytestmark = [pytest.mark.unit]

SESSION = FullTagSession(clip="match:x", fps=60, frame_count=3600, players=("A1", "A2", "B1", "B2"))


@pytest.mark.parametrize("kind", [[], ["hit"], {}, {"a": 1}, None, 1, 1.5, True])
def test_a_type_of_any_json_value_is_refused(kind: Any) -> None:
    with pytest.raises(LabelRefused):
        SESSION.add({"type": kind, "frame": 10, "hitter": "B1"})
