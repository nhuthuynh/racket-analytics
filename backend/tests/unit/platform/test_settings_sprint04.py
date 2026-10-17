"""Sprint 4 settings (ST-067; api-sprint-04 §11; ADR 0003, ADR 0023, ADR 0051 rules 2 and 4):
the weakness unit, the four R1 feature flags (default off) and their interim values. Negative
cases first. The last tests pin ``infra/env.example`` to the same defaults."""

from __future__ import annotations

import pytest

from racket.platform.settings import ConfigurationError, Settings
from tests.support.paths import REPO

pytestmark = pytest.mark.unit

BASE = {"APP_ENV": "test", "DATABASE_URL": "postgresql://r:p@db:5432/r", "S3_BUCKET_MEDIA": "m"}
FLAGS = tuple(
    f"FEATURE_{f}" for f in ("AGE_GATE", "RETENTION_SETTING", "TRAINING_CONSENT", "QUOTAS")
)
VALUES = ("AGE_MINIMUM", "RETENTION_CHOICES_DAYS", "RETENTION_DEFAULT_DAYS")
NEW = ("COACHING_WEAKNESS_UNIT", *FLAGS, *VALUES, "MATCH_CREATIONS_PER_HOUR", "STORAGE_QUOTA_BYTES")
BAD = {
    "COACHING_WEAKNESS_UNIT": ("points_lost_per_game", "RALLIES_LOST_PER_GAME", "rallies lost"),
    **dict.fromkeys(FLAGS, ("yes", "on", "2")),
    "AGE_MINIMUM": ("17", "0", "eighteen"),
    "RETENTION_CHOICES_DAYS": (",", "0,90", "-30,90", "30,²", "30,90,90", "30;90", "none,none"),
    "RETENTION_DEFAULT_DAYS": ("60", "x", "None"),  # "none" is lower case only
    "MATCH_CREATIONS_PER_HOUR": ("0", "-5", "ten"),
    "STORAGE_QUOTA_BYTES": ("0", "-5", "ten", "²"),
}
REFUSED = [(name, value) for name, values in BAD.items() for value in values]


def build(**overrides: str) -> Settings:
    return Settings.from_env({**BASE, **overrides})


@pytest.mark.parametrize(("name", "value"), REFUSED)
def test_a_bad_value_refuses_to_start_and_names_the_setting(name: str, value: str) -> None:
    with pytest.raises(ConfigurationError, match=name):
        build(**{name: value})


def test_a_default_outside_custom_choices_refuses_to_start() -> None:
    with pytest.raises(ConfigurationError, match="RETENTION_DEFAULT_DAYS"):
        build(RETENTION_CHOICES_DAYS="30,90", RETENTION_DEFAULT_DAYS="none")


def test_defaults_are_the_interim_values_with_every_flag_off() -> None:
    s = build()
    assert s.coaching_weakness_unit == "rallies_lost_per_game"
    assert [getattr(s, flag.lower()) for flag in FLAGS] == [False] * 4
    assert (s.age_minimum, s.retention_choices_days, s.retention_default_days) == (
        18,
        (30, 90, 365, None),
        90,
    )
    assert (s.match_creations_per_hour, s.storage_quota_bytes) == (10, 20 * 1024**3)


@pytest.mark.parametrize("flag", FLAGS)
@pytest.mark.parametrize(("raw", "on"), [("true", True), ("1", True), ("FALSE", False)])
def test_each_flag_parses_on_its_own(flag: str, raw: str, on: bool) -> None:
    s = build(**{flag: raw})
    assert [getattr(s, f.lower()) for f in FLAGS] == [on and f == flag for f in FLAGS]


def test_configured_values_are_read() -> None:
    s = build(
        COACHING_WEAKNESS_UNIT=" rallies_lost_per_game ",
        AGE_MINIMUM="21",
        RETENTION_CHOICES_DAYS="none, 30,7",
        RETENTION_DEFAULT_DAYS="none",
        MATCH_CREATIONS_PER_HOUR="3",
        STORAGE_QUOTA_BYTES="1000",
    )
    assert (s.coaching_weakness_unit, s.age_minimum) == ("rallies_lost_per_game", 21)
    assert (s.retention_choices_days, s.retention_default_days) == ((None, 30, 7), None)
    assert (s.match_creations_per_hour, s.storage_quota_bytes) == (3, 1000)
    assert set(NEW) <= set(s.redacted())  # the startup log line shows them


def test_public_config_is_the_flags_and_the_unit_and_nothing_else() -> None:
    s = build(FEATURE_TRAINING_CONSENT="true", STORAGE_QUOTA_BYTES="5", AGE_MINIMUM="30")
    assert s.public_config() == {
        "features": {
            "age_gate": False,
            "retention_setting": False,
            "training_consent": True,
            "quotas": False,
        },
        "coaching": {"weakness_unit": "rallies_lost_per_game"},
    }


def test_env_example_lists_each_new_setting_off_and_interim_with_its_source() -> None:
    lines = (REPO / "infra" / "env.example").read_text().splitlines()
    values = dict(ln.split("=", 1) for ln in lines if ln and not ln.startswith("#"))
    assert set(NEW) <= set(values), sorted(set(NEW) - set(values))
    assert [values[flag] for flag in FLAGS] == ["false"] * 4
    assert build(**{name: values[name] for name in NEW}) == build()
    for name in NEW:
        comment = lines[lines.index(f"{name}={values[name]}") - 1]
        assert comment.startswith("# interim"), (name, comment)
        assert "OQ-" in comment, (name, comment)
