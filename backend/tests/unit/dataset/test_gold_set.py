"""Gold-set manifest v1 (ST-040; FR-151, QD §8, QD-GD-04, QD-TX-03, OQ-06 / ADR 0023).

Pure domain: manifest data and parsed label documents arrive as data. Negative cases first.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from racket.dataset.gold_set import GOLD_SCHEMA, GoldSet, GoldSetCheck
from racket.dataset.labels import LABEL_SCHEMA
from racket.dataset.manifest import Manifest, ManifestFormatError

pytestmark = pytest.mark.unit

SHA = "c" * 64


def a_label_doc(clip: str, **facets: str) -> dict[str, Any]:
    return {
        "schema": LABEL_SCHEMA,
        "clip": clip,
        "fps": 60,
        "frame_count": 120,
        "players": ["A1", "A2", "B1", "B2"],
        "rallies": [
            {
                "id": "r1",
                "start_frame": 5,
                "end_frame": 100,
                "outcome": {
                    "ending": "winner",
                    "winning_side": "A",
                    "responsible_player": "A1",
                    "fault_kind": None,
                },
                "events": [{"type": "hit", "frame": 10, "hitter": "A1", "facets": facets}],
            }
        ],
    }


def a_clip(n: int, venue: str, **overrides: Any) -> dict[str, Any]:
    clip: dict[str, Any] = {
        "path": f"clips/c{n}.mp4",
        "label_file": f"labels/c{n}.json",
        "venue_id": venue,
        "double_labelled": n == 1,
        "second_label_file": f"labels/c{n}.second.json" if n == 1 else None,
        "shows_people": False,
        "consent_record": None,
        "consent_jurisdiction": None,
    }
    clip.update(overrides)
    return clip


def a_raw(**overrides: Any) -> dict[str, Any]:
    clips = [
        a_clip(1, "V1"),
        a_clip(2, "V2"),
        a_clip(3, "V3"),
        a_clip(4, "V4"),
        a_clip(5, "V5"),
    ]
    raw: dict[str, Any] = {
        "schema": GOLD_SCHEMA,
        "id": "gs-test",
        "version": 1,
        "created": "2026-10-06",
        "purpose": "vision",
        "label_schema": LABEL_SCHEMA,
        "rules_version": "pickleball-provisional-2026.1",
        "metric_dict_version": "0.1",
        "licence": "CC0-1.0",
        "consent_status": "synthetic",
        "labellers": [{"role_id": "LBL-01", "role": "labeller"}],
        "agreement": [],
        "venues": [
            {"id": "V1", "split": "train"},
            {"id": "V2", "split": "val"},
            {"id": "V3", "split": "test"},
            {"id": "V4", "split": "test"},
            {"id": "V5", "split": "test"},
        ],
        "clips": clips,
    }
    raw.update(overrides)
    paths = [c["path"] for c in raw["clips"]] + [c["label_file"] for c in raw["clips"]]
    paths += [c["second_label_file"] for c in raw["clips"] if c.get("second_label_file")]
    raw.setdefault("files", [{"path": p, "sha256": SHA} for p in paths])
    return raw


def labels_for(raw: dict[str, Any], **facets: str) -> dict[str, object]:
    labels: dict[str, object] = {}
    for c in raw["clips"]:
        for key in ("label_file", "second_label_file"):
            if c.get(key):
                labels[c[key]] = a_label_doc(c["path"], **facets)
    return labels


def gold(raw: dict[str, Any]) -> GoldSet:
    return GoldSet.from_manifest(Manifest.from_dict(raw))


def kinds(raw: dict[str, Any], labels: dict[str, object] | None = None) -> list[tuple[str, str]]:
    labels = labels if labels is not None else labels_for(raw)
    result = GoldSetCheck.check(gold(raw), labels)
    return [(p.kind, p.path) for p in result.problems]


# --- format: negative cases first ----------------------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        "created",
        "purpose",
        "label_schema",
        "rules_version",
        "metric_dict_version",
        "labellers",
        "agreement",
        "venues",
        "clips",
    ],
)
def test_a_gold_manifest_without_a_qd8_field_is_malformed(field: str) -> None:
    raw = a_raw()
    del raw[field]
    with pytest.raises(ManifestFormatError, match=field):
        gold(raw)


def test_a_manifest_without_the_gold_schema_is_not_a_gold_set() -> None:
    raw = a_raw()
    del raw["schema"]
    with pytest.raises(ManifestFormatError, match="schema"):
        gold(raw)


@pytest.mark.parametrize("created", ["06/10/2026", "2026-13-01", 20261006, ""])
def test_created_must_be_an_iso_date(created: object) -> None:
    with pytest.raises(ManifestFormatError, match="created"):
        gold(a_raw(created=created))


@pytest.mark.parametrize("purpose", ["training", "", None])
def test_purpose_is_one_of_the_qd_gold_sets(purpose: object) -> None:
    with pytest.raises(ManifestFormatError, match="purpose"):
        gold(a_raw(purpose=purpose))


def test_label_schema_must_be_v1() -> None:
    with pytest.raises(ManifestFormatError, match="label_schema"):
        gold(a_raw(label_schema="full-tag-labels/v9"))


@pytest.mark.parametrize("status", ["unknown", "user-opt-in", "public"])
def test_consent_status_is_synthetic_or_consented_only(status: str) -> None:
    # Footage from real users needs the legal review first (NFR-070, ADR 0023 OQ-05/OQ-06).
    with pytest.raises(ManifestFormatError, match="consent_status"):
        gold(a_raw(consent_status=status))


@pytest.mark.parametrize(
    "labellers",
    [[], [{"role_id": "ivy@example.com", "role": "labeller"}], [{"role": "labeller"}], ["LBL"]],
)
def test_labellers_are_role_ids_not_people(labellers: object) -> None:
    with pytest.raises(ManifestFormatError, match="labellers"):
        gold(a_raw(labellers=labellers))


def test_venue_ids_are_unique_and_splits_known() -> None:
    with pytest.raises(ManifestFormatError, match="venue"):
        gold(a_raw(venues=[{"id": "V1", "split": "train"}, {"id": "V1", "split": "test"}]))
    with pytest.raises(ManifestFormatError, match="split"):
        gold(a_raw(venues=[{"id": "V1", "split": "holdout"}]))


@pytest.mark.parametrize(
    "field", ["label_file", "venue_id", "double_labelled", "consent_jurisdiction"]
)
def test_a_gold_clip_needs_its_gold_fields(field: str) -> None:
    raw = a_raw()
    del raw["clips"][0][field]
    with pytest.raises(ManifestFormatError, match=field):
        gold(raw)


@pytest.mark.parametrize(
    "entry",
    [
        {"facet": "spin", "kappa": 0.8, "n": 400, "admitted": True},
        {"facet": "trajectory", "kappa": 1.4, "n": 400, "admitted": True},
        {"facet": "trajectory", "kappa": 0.8, "n": -1, "admitted": True},
        {"facet": "trajectory", "kappa": 0.8, "n": 400},
    ],
)
def test_agreement_rows_are_well_formed(entry: dict[str, Any]) -> None:
    with pytest.raises(ManifestFormatError, match="agreement"):
        gold(a_raw(agreement=[entry]))


# --- check: negative cases -----------------------------------------------------------


def test_a_vision_set_needs_three_held_out_venues() -> None:
    raw = a_raw(
        venues=[
            {"id": "V1", "split": "train"},
            {"id": "V2", "split": "train"},
            {"id": "V3", "split": "train"},
            {"id": "V4", "split": "test"},
            {"id": "V5", "split": "test"},
        ]
    )
    assert kinds(raw) == [("held_out_venues", "")]


def test_a_held_out_venue_without_clips_does_not_count() -> None:
    raw = a_raw()
    raw["clips"] = [c for c in raw["clips"] if c["venue_id"] != "V5"]
    raw["files"] = [f for f in raw["files"] if "c5" not in f["path"]]
    assert ("held_out_venues", "") in kinds(raw)


def test_a_clip_from_an_unlisted_venue_fails() -> None:
    raw = a_raw()
    raw["clips"][0]["venue_id"] = "V9"
    assert ("unknown_venue", "clips/c1.mp4") in kinds(raw)


def test_a_vision_set_needs_a_fifth_of_clips_double_labelled() -> None:
    raw = a_raw()
    raw["clips"][0].update(double_labelled=False, second_label_file=None)
    assert kinds(raw) == [("double_label_share", "")]


@pytest.mark.parametrize(
    "entry",
    [
        {"facet": "trajectory", "kappa": 0.69, "n": 400, "admitted": True},
        {"facet": "trajectory", "kappa": 0.75, "n": 299, "admitted": True},
        {"facet": "ending", "kappa": 0.59, "n": 50, "admitted": True},
    ],
)
def test_an_admitted_facet_below_its_agreement_gate_fails(entry: dict[str, Any]) -> None:
    raw = a_raw(agreement=[entry])
    assert kinds(raw) == [("kappa_below_gate", entry["facet"])]


def test_labels_may_carry_only_admitted_shot_facets() -> None:
    raw = a_raw(agreement=[{"facet": "trajectory", "kappa": 0.4, "n": 400, "admitted": False}])
    assert ("facet_not_admitted", "trajectory") in kinds(raw, labels_for(raw, trajectory="dink"))


def test_a_synthetic_set_cannot_show_people() -> None:
    raw = a_raw()
    raw["clips"][0].update(
        shows_people=True, consent_record="forms/c1.pdf", consent_jurisdiction="US"
    )
    assert ("consent_contradiction", "clips/c1.mp4") in kinds(raw)


@pytest.mark.parametrize("jurisdiction", [None, "UK", ""])
def test_a_clip_with_people_names_a_covered_jurisdiction(jurisdiction: str | None) -> None:
    raw = a_raw(consent_status="consented")
    raw["clips"][0].update(
        shows_people=True, consent_record="CF-2026-001", consent_jurisdiction=jurisdiction
    )
    assert kinds(raw) == [("consent_jurisdiction", "clips/c1.mp4")]


def test_label_file_must_be_a_file_of_the_set() -> None:
    raw = a_raw()
    raw["files"] = [f for f in raw["files"] if f["path"] != "labels/c2.json"]
    labels = labels_for(raw)
    del labels["labels/c2.json"]
    assert ("label_not_in_files", "labels/c2.json") in kinds(raw, labels)


def test_an_invalid_label_file_fails_and_names_the_file_and_problem() -> None:
    raw = a_raw()
    labels = labels_for(raw)
    labels["labels/c3.json"]["fps"] = 0  # type: ignore[index]
    result = GoldSetCheck.check(gold(raw), labels)
    assert [(p.kind, p.path) for p in result.problems] == [("label_invalid", "labels/c3.json")]
    assert "fps: must be a positive integer" in result.problems[0].describe()


def test_a_label_file_for_another_clip_fails() -> None:
    raw = a_raw()
    labels = labels_for(raw)
    labels["labels/c3.json"]["clip"] = "clips/c4.mp4"  # type: ignore[index]
    assert kinds(raw, labels) == [("label_invalid", "labels/c3.json")]


def test_a_double_labelled_clip_needs_its_second_label_file() -> None:
    raw = a_raw()
    raw["clips"][0]["second_label_file"] = None
    with pytest.raises(ManifestFormatError, match="second_label_file"):
        gold(raw)


def test_a_single_labelled_clip_has_no_second_label_file() -> None:
    raw = a_raw()
    raw["clips"][1]["second_label_file"] = "labels/c2.second.json"
    with pytest.raises(ManifestFormatError, match="second_label_file"):
        gold(raw)


def test_the_second_label_file_is_checked_like_the_first() -> None:
    raw = a_raw()
    labels = labels_for(raw)
    labels["labels/c1.second.json"]["players"] = ["A1"]  # type: ignore[index]
    assert kinds(raw, labels) == [("label_invalid", "labels/c1.second.json")]


def test_two_clips_cannot_share_one_label_file() -> None:
    raw = a_raw()
    raw["clips"][1]["label_file"] = "labels/c1.json"
    with pytest.raises(ManifestFormatError, match="label_file"):
        gold(raw)


# --- check: positive cases -----------------------------------------------------------


def test_a_complete_synthetic_vision_set_passes() -> None:
    assert kinds(a_raw()) == []


def test_admitted_facets_at_the_gate_pass_and_may_be_labelled() -> None:
    raw = a_raw(
        agreement=[
            {"facet": "trajectory", "kappa": 0.70, "n": 300, "admitted": True},
            {"facet": "ending", "kappa": 0.60, "n": 40, "admitted": True},
            {"facet": "hitter", "kappa": None, "n": 0, "admitted": False},
        ]
    )
    assert kinds(raw, labels_for(raw, trajectory="drop")) == []


def test_a_consented_set_with_us_and_au_participants_passes() -> None:
    raw = a_raw(consent_status="consented")
    raw["clips"][0].update(
        shows_people=True, consent_record="CF-2026-001", consent_jurisdiction="US"
    )
    raw["clips"][1].update(
        shows_people=True, consent_record="CF-2026-002", consent_jurisdiction="AU"
    )
    assert kinds(raw) == []


def test_venue_rules_apply_to_vision_sets_only() -> None:
    raw = a_raw(purpose="analytics", venues=[{"id": f"V{i}", "split": "test"} for i in (1, 2)])
    for c in raw["clips"]:
        c.update(venue_id="V1", double_labelled=False, second_label_file=None)
    assert kinds(raw) == []


def test_split_of_a_clip_is_the_split_of_its_venue() -> None:
    g = gold(a_raw())
    assert g.split_of("clips/c1.mp4") == "train"
    assert g.split_of("clips/c4.mp4") == "test"


def test_the_check_does_not_change_its_inputs() -> None:
    raw = a_raw()
    labels = labels_for(raw)
    before = copy.deepcopy(labels)
    GoldSetCheck.check(gold(raw), labels)
    assert labels == before


# --- which manifests are gold sets (used by racket-manifest-check) --------------------


def test_an_unknown_manifest_schema_is_malformed_not_skipped() -> None:
    from racket.dataset.gold_set import gold_set_of

    with pytest.raises(ManifestFormatError, match="schema"):
        gold_set_of(Manifest.from_dict(a_raw(schema="gold-set-manifest/v2")))


def test_a_fixture_manifest_without_schema_is_not_a_gold_set() -> None:
    from racket.dataset.gold_set import gold_set_of

    raw = a_raw()
    del raw["schema"]
    assert gold_set_of(Manifest.from_dict(raw)) is None


def test_a_gold_manifest_is_read_as_a_gold_set() -> None:
    from racket.dataset.gold_set import gold_set_of

    found = gold_set_of(Manifest.from_dict(a_raw()))
    assert found is not None
    assert found.purpose == "vision"
