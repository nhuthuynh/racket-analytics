"""RulesConfig and PRESETS (ST-020; sprint-01 §5 rows 1-4; scoring-engine.md §2.2-§2.3).

BE unit tests, negative cases first. Every value here is an explicit test input, never a
rulebook claim (ADR 0009 part a).
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from racket.sports.pickleball.rules import (
    PRESETS,
    InvalidRulesConfig,
    MatchFormat,
    RulesConfig,
    ScoringSystem,
    Side,
)

pytestmark = [pytest.mark.unit, pytest.mark.scoring]


def _values(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "rules_version": "TEST-1",
        "scoring_system": "side_out",
        "format": "doubles",
        "points_to_win": 11,
        "win_by": 2,
        "first_service_single_server": True,
    }
    values.update(overrides)
    return values


def _refused(**overrides: Any) -> InvalidRulesConfig:
    with pytest.raises(InvalidRulesConfig) as caught:
        RulesConfig(**_values(**overrides))
    return caught.value


@pytest.mark.parametrize("value", [0, -1, True, 11.0, "11", None])
def test_points_to_win_below_one_or_not_an_int_is_refused(value: Any) -> None:
    error = _refused(points_to_win=value)
    assert error.field == "points_to_win"
    assert error.reason == "invalid"
    assert "points_to_win" in str(error)


@pytest.mark.parametrize("value", [0, -2, False, 2.5, None])
def test_win_by_below_one_or_not_an_int_is_refused(value: Any) -> None:
    error = _refused(win_by=value)
    assert error.field == "win_by"
    assert "win_by" in str(error)


@pytest.mark.parametrize("value", ["", "badminton", "SIDE_OUT", None, 1])
def test_unknown_scoring_system_is_refused(value: Any) -> None:
    error = _refused(scoring_system=value)
    assert (error.field, error.reason) == ("scoring_system", "unknown")


def test_rally_scoring_is_known_but_unsupported_until_verified() -> None:
    error = _refused(scoring_system="rally")  # FR-043: blocked on OQ-01
    assert (error.field, error.reason) == ("scoring_system", "unsupported")


@pytest.mark.parametrize("value", ["triples", "", None])
def test_unknown_format_is_refused(value: Any) -> None:
    error = _refused(format=value)
    assert (error.field, error.reason) == ("format", "unknown")


def test_singles_is_known_but_unsupported_in_sprint_1() -> None:
    error = _refused(format="singles")  # ST-035
    assert (error.field, error.reason) == ("format", "unsupported")


@pytest.mark.parametrize("value", ["", "   ", "has space", "semi;colon", None, 7])
def test_rules_version_must_be_a_short_identifier(value: Any) -> None:
    assert _refused(rules_version=value).field == "rules_version"


@pytest.mark.parametrize("value", [1, 0, "yes", None])
def test_first_service_flag_must_be_a_bool(value: Any) -> None:
    assert _refused(first_service_single_server=value).field == "first_service_single_server"


def test_every_field_is_required_with_no_hidden_default() -> None:
    for name in _values():
        values = _values()
        del values[name]
        with pytest.raises(TypeError):
            RulesConfig(**values)


def test_fields_are_keyword_only() -> None:
    with pytest.raises(TypeError):
        RulesConfig("TEST-1", "side_out", "doubles", 11, 2, True)  # type: ignore[misc]


def test_invalid_config_is_a_value_error_not_a_domain_error() -> None:
    assert issubclass(InvalidRulesConfig, ValueError)


def test_a_valid_config_is_immutable_and_compares_by_value() -> None:
    config = RulesConfig(**_values())
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.points_to_win = 15  # type: ignore[misc]
    assert config == RulesConfig(**_values())
    assert hash(config) == hash(RulesConfig(**_values()))


def test_string_inputs_become_enum_members() -> None:
    config = RulesConfig(**_values())
    assert config.scoring_system is ScoringSystem.SIDE_OUT
    assert config.format is MatchFormat.DOUBLES
    assert config.scoring_system == "side_out"
    assert config.format == "doubles"


def test_side_other() -> None:
    assert Side.A.other is Side.B
    assert Side.B.other is Side.A
    assert Side["A"] is Side.A


def test_only_the_provisional_preset_ships() -> None:
    assert list(PRESETS) == ["PROVISIONAL-UNVERIFIED"]
    preset = PRESETS["PROVISIONAL-UNVERIFIED"]
    assert preset.rules_version == "PROVISIONAL-UNVERIFIED"
    with pytest.raises(TypeError):
        PRESETS["USAP-2026"] = preset  # type: ignore[index]
