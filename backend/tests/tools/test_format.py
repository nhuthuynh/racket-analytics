"""The test-side renderer of user-visible values (mirrors the web formatDuration)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests.support.format import facts_display, format_duration


def test_negative_duration_rejected() -> None:
    with pytest.raises(ValueError, match="negative"):
        format_duration(-1)


@pytest.mark.parametrize(
    ("ms", "text"), [(0, "0:00"), (59_499, "0:59"), (60_000, "1:00"), (3_600_000, "1:00:00")]
)
def test_human_units(ms: int, text: str) -> None:
    assert format_duration(ms) == text


def test_fixture_facts_render_as_in_the_sprint_goal() -> None:
    media = {"duration_ms": 60_000, "fps": 60, "width": 1920, "height": 1080}

    assert facts_display(media) == ("1:00", "60 fps", "1920×1080")


@given(st.integers(min_value=0, max_value=10 * 3600 * 1000))
def test_seconds_field_is_always_two_digits(ms: int) -> None:
    assert len(format_duration(ms).split(":")[-1]) == 2
