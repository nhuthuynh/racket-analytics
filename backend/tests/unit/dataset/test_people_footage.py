"""People footage storage rule (SEC-S2-TM-06, QA-RV2-12): pure domain, git facts as data.

Negative cases first.
"""

from __future__ import annotations

from typing import Any

import pytest

from racket.dataset.gold_set import GoldSet
from racket.dataset.manifest import FootageStorageCheck, Manifest
from tests.unit.dataset.test_gold_set import a_clip, a_raw

pytestmark = pytest.mark.unit


def consented_gold() -> GoldSet:
    raw: dict[str, Any] = a_raw(consent_status="consented")
    raw["clips"][0] = a_clip(
        1, "V1", shows_people=True, consent_record="CF-2026-001", consent_jurisdiction="AU"
    )
    return GoldSet.from_manifest(Manifest.from_dict(raw))


def test_a_people_clip_exposed_to_git_is_refused() -> None:
    result = FootageStorageCheck.check(["clips/c1.mp4"], exposed_to_git={"clips/c1.mp4"})

    assert [(p.kind, p.path) for p in result.problems] == [("people_in_git", "clips/c1.mp4")]
    assert "private" in result.problems[0].describe()


def test_a_gold_set_manifest_names_its_people_clips() -> None:
    assert consented_gold().manifest.people_clip_paths == ("clips/c1.mp4",)


def test_a_fixture_manifest_names_its_people_clips() -> None:
    manifest = Manifest.from_dict(
        {
            "id": "s",
            "version": 1,
            "licence": "x",
            "consent_status": "consented",
            "files": [],
            "clips": [
                {"path": "a.mp4", "shows_people": True, "consent_record": "CF-1"},
                {"path": "b.mp4", "shows_people": False, "consent_record": None},
            ],
        }
    )
    assert manifest.people_clip_paths == ("a.mp4",)


def test_people_clips_not_exposed_to_git_pass() -> None:
    result = FootageStorageCheck.check(["clips/c1.mp4"], exposed_to_git={"clips/c2.mp4"})

    assert result.passed
