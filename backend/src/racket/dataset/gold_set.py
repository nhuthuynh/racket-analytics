"""Gold-set manifest v1 and its checks (ST-040; FR-151, QD §8, QD-GD-02..04/-07).

A gold-set manifest is a fixture manifest (``racket.dataset.manifest``) with
``"schema": "gold-set-manifest/v1"`` and the QD §8 fields. ``racket-manifest-check`` runs the
integrity check on every set and this check on gold sets too (docs/data/gold-set-manifest.md).

Pure domain code: label documents arrive parsed (``racket.dataset.filesystem``); no I/O.

Format errors (``ManifestFormatError``, CLI exit 2) are shape problems. Check problems
(CLI exit 1) are rule breaks a well-formed manifest can still have:

* vision sets are split by venue with >= 3 held-out venues and >= 20% of clips
  double-labelled (QD-GD-04; brainstorm-engineering §5.3);
* an admitted facet meets its agreement gate: shot facets kappa >= 0.7 on >= 300 shots
  (QD-TX-03), the error ending kappa >= 0.6 (QD X3); labels carry only admitted shot facets;
* consent: ``synthetic`` sets show nobody; a clip that shows people names the consent
  jurisdiction, US or AU (OQ-06, ADR 0023); ``consent_status`` other than ``synthetic`` or
  ``consented`` (team-recorded, written consent) is refused until the legal review (NFR-070);
* every clip has its own label file in the set, valid against ``full-tag-labels/v1``.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from racket.dataset.labels import LABEL_SCHEMA, SHOT_FACETS, used_facets, validate_labels
from racket.dataset.manifest import (
    CheckResult,
    IntegrityProblem,
    Manifest,
    ManifestFormatError,
)

GOLD_SCHEMA = "gold-set-manifest/v1"

PURPOSES = ("vision", "analytics", "scoring", "fixture")  # QD-GD-04, -03, -02, -07
CONSENT_STATUSES = ("synthetic", "consented")
SPLITS = ("train", "val", "test")
JURISDICTIONS = ("US", "AU")  # ADR 0023, OQ-05
MIN_HELD_OUT_VENUES = 3
MIN_DOUBLE_LABELLED_SHARE = 0.2
# facet -> (minimum kappa, minimum compared items); facets without a gate are recorded only.
AGREEMENT_GATES: Mapping[str, tuple[float, int]] = {
    **dict.fromkeys(SHOT_FACETS, (0.7, 300)),
    "ending": (0.6, 0),
}
RECORDED_FACETS = ("hit", "bounce", "hitter", "rally_boundaries", "winning_side")
_GOLD_FIELDS = (
    "created",
    "purpose",
    "label_schema",
    "rules_version",
    "metric_dict_version",
    "labellers",
    "agreement",
    "venues",
    "clips",
)


def _require(data: Mapping[str, Any], key: str, where: str) -> Any:
    if key not in data:
        raise ManifestFormatError(f"{where} is missing required field {key!r}")
    return data[key]


@dataclass(frozen=True)
class Agreement:
    facet: str
    kappa: float | None
    n: int
    admitted: bool

    @classmethod
    def from_dict(cls, data: object) -> Agreement:
        if not isinstance(data, Mapping):
            raise ManifestFormatError("agreement rows must be objects")
        facet = _require(data, "facet", "agreement row")
        if facet not in AGREEMENT_GATES and facet not in RECORDED_FACETS:
            raise ManifestFormatError(f"agreement: unknown facet {facet!r}")
        kappa = _require(data, "kappa", "agreement row")
        if kappa is not None and (
            isinstance(kappa, bool) or not isinstance(kappa, int | float) or not -1 <= kappa <= 1
        ):
            raise ManifestFormatError(f"agreement: kappa for {facet!r} must be in -1..1 or null")
        n = _require(data, "n", "agreement row")
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ManifestFormatError(f"agreement: n for {facet!r} must be an integer >= 0")
        if "admitted" not in data or not isinstance(data["admitted"], bool):
            raise ManifestFormatError(f"agreement: admitted for {facet!r} must be true or false")
        return cls(facet, None if kappa is None else float(kappa), n, data["admitted"])

    def below_gate(self) -> bool:
        gate = AGREEMENT_GATES.get(self.facet)
        if not self.admitted or gate is None:
            return False
        min_kappa, min_n = gate
        return self.kappa is None or self.kappa < min_kappa or self.n < min_n


@dataclass(frozen=True)
class GoldClip:
    path: str
    label_file: str
    venue_id: str
    double_labelled: bool
    shows_people: bool
    consent_jurisdiction: str | None
    second_label_file: str | None = None

    @property
    def label_files(self) -> tuple[str, ...]:
        if self.second_label_file is None:
            return (self.label_file,)
        return (self.label_file, self.second_label_file)

    @classmethod
    def from_dict(cls, data: object) -> GoldClip:
        if not isinstance(data, Mapping):
            raise ManifestFormatError("gold clip entries must be objects")
        path = _require(data, "path", "gold clip")
        where = f"gold clip {path!r}"
        label_file = _require(data, "label_file", where)
        venue_id = _require(data, "venue_id", where)
        double = _require(data, "double_labelled", where)
        jurisdiction = _require(data, "consent_jurisdiction", where)
        if not isinstance(label_file, str) or not label_file:
            raise ManifestFormatError(f"{where}: label_file must be a path in the set")
        if not isinstance(venue_id, str) or not venue_id:
            raise ManifestFormatError(f"{where}: venue_id must be a non-empty string")
        if not isinstance(double, bool):
            raise ManifestFormatError(f"{where}: double_labelled must be true or false")
        if jurisdiction is not None and not isinstance(jurisdiction, str):
            raise ManifestFormatError(f"{where}: consent_jurisdiction must be a string or null")
        second = data.get("second_label_file")
        if double and not (isinstance(second, str) and second):
            raise ManifestFormatError(
                f"{where}: a double-labelled clip needs second_label_file (the second labeller's)"
            )
        if not double and second is not None:
            raise ManifestFormatError(f"{where}: second_label_file only for a double-labelled clip")
        return cls(
            path=str(path),
            label_file=label_file,
            venue_id=venue_id,
            double_labelled=double,
            shows_people=bool(data.get("shows_people")),
            consent_jurisdiction=jurisdiction,
            second_label_file=second,
        )


def _created(value: object) -> dt.date:
    if not isinstance(value, str):
        raise ManifestFormatError("created must be an ISO date (YYYY-MM-DD)")
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ManifestFormatError(f"created must be an ISO date (YYYY-MM-DD): {exc}") from exc


def _labellers(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list) or not raw:
        raise ManifestFormatError("labellers must be a non-empty list of role IDs")
    ids: list[str] = []
    for item in raw:
        role_id = item.get("role_id") if isinstance(item, Mapping) else None
        if not isinstance(role_id, str) or not role_id or "@" in role_id:
            raise ManifestFormatError(
                "labellers: each entry needs a role_id (a role ID, never a name or email)"
            )
        ids.append(role_id)
    return tuple(ids)


def _venues(raw: object) -> Mapping[str, str]:
    if not isinstance(raw, list) or not raw:
        raise ManifestFormatError("venues must be a non-empty list")
    venues: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            raise ManifestFormatError("venues: entries must be objects")
        venue_id, split = item.get("id"), item.get("split")
        if not isinstance(venue_id, str) or not venue_id or venue_id in venues:
            raise ManifestFormatError(f"venues: id {venue_id!r} must be a unique non-empty string")
        if split not in SPLITS:
            raise ManifestFormatError(f"venues: split of {venue_id!r} must be one of {SPLITS}")
        venues[venue_id] = split
    return venues


@dataclass(frozen=True)
class GoldSet:
    manifest: Manifest
    created: dt.date
    purpose: str
    labellers: tuple[str, ...]
    agreement: tuple[Agreement, ...]
    venues: Mapping[str, str]
    clips: tuple[GoldClip, ...]

    @classmethod
    def from_manifest(cls, manifest: Manifest) -> GoldSet:
        extra = manifest.extra
        if extra.get("schema") != GOLD_SCHEMA:
            raise ManifestFormatError(f"schema must be {GOLD_SCHEMA!r} for a gold set")
        for key in _GOLD_FIELDS:
            _require(extra, key, "gold-set manifest")
        if extra["purpose"] not in PURPOSES:
            raise ManifestFormatError(f"purpose must be one of {PURPOSES}")
        if extra["label_schema"] != LABEL_SCHEMA:
            raise ManifestFormatError(f"label_schema must be {LABEL_SCHEMA!r}")
        if manifest.consent_status not in CONSENT_STATUSES:
            raise ManifestFormatError(
                f"consent_status must be one of {CONSENT_STATUSES}; footage from real users "
                "waits for the legal review (NFR-070)"
            )
        for key in ("rules_version", "metric_dict_version"):
            if extra[key] is not None and not isinstance(extra[key], str):
                raise ManifestFormatError(f"{key} must be a string or null")
        if not isinstance(extra["agreement"], list):
            raise ManifestFormatError("agreement must be a list")
        if not isinstance(extra["clips"], list) or not extra["clips"]:
            raise ManifestFormatError("clips must be a non-empty list")
        clips = tuple(GoldClip.from_dict(c) for c in extra["clips"])
        label_files = [f for c in clips for f in c.label_files]
        if len(set(label_files)) != len(label_files):
            raise ManifestFormatError("label_file: each clip needs its own label file")
        return cls(
            manifest=manifest,
            created=_created(extra["created"]),
            purpose=extra["purpose"],
            labellers=_labellers(extra["labellers"]),
            agreement=tuple(Agreement.from_dict(a) for a in extra["agreement"]),
            venues=_venues(extra["venues"]),
            clips=clips,
        )

    def split_of(self, clip_path: str) -> str | None:
        venue = next((c.venue_id for c in self.clips if c.path == clip_path), None)
        return self.venues.get(venue) if venue is not None else None


class GoldSetCheck:
    """Rule checks of a well-formed gold-set manifest v1 and its label files."""

    @staticmethod
    def check(gold: GoldSet, labels: Mapping[str, object]) -> CheckResult:
        problems: list[IntegrityProblem] = []
        problems += GoldSetCheck._venues(gold)
        problems += GoldSetCheck._agreement(gold, labels)
        problems += GoldSetCheck._consent(gold)
        problems += GoldSetCheck._labels(gold, labels)
        return CheckResult(tuple(problems))

    @staticmethod
    def _venues(gold: GoldSet) -> list[IntegrityProblem]:
        problems = [
            IntegrityProblem("unknown_venue", c.path, c.venue_id)
            for c in gold.clips
            if c.venue_id not in gold.venues
        ]
        if gold.purpose != "vision":
            return problems
        held_out = {c.venue_id for c in gold.clips if gold.venues.get(c.venue_id) == "test"}
        if len(held_out) < MIN_HELD_OUT_VENUES:
            problems.append(
                IntegrityProblem("held_out_venues", "", f"{len(held_out)} < {MIN_HELD_OUT_VENUES}")
            )
        share = sum(c.double_labelled for c in gold.clips) / len(gold.clips)
        if share < MIN_DOUBLE_LABELLED_SHARE:
            problems.append(IntegrityProblem("double_label_share", "", f"{share:.0%} < 20%"))
        return problems

    @staticmethod
    def _agreement(gold: GoldSet, labels: Mapping[str, object]) -> list[IntegrityProblem]:
        problems = [
            IntegrityProblem("kappa_below_gate", a.facet, f"kappa {a.kappa}, n {a.n}")
            for a in gold.agreement
            if a.below_gate()
        ]
        admitted = {a.facet for a in gold.agreement if a.admitted and not a.below_gate()}
        used: set[str] = set()
        for clip in gold.clips:
            for label_file in clip.label_files:
                used |= used_facets(labels.get(label_file))
        problems += [
            IntegrityProblem("facet_not_admitted", facet) for facet in sorted(used - admitted)
        ]
        return problems

    @staticmethod
    def _consent(gold: GoldSet) -> list[IntegrityProblem]:
        problems: list[IntegrityProblem] = []
        synthetic = gold.manifest.consent_status == "synthetic"
        for clip in gold.clips:
            if not clip.shows_people:
                continue
            if synthetic:
                problems.append(IntegrityProblem("consent_contradiction", clip.path))
            elif clip.consent_jurisdiction not in JURISDICTIONS:
                problems.append(
                    IntegrityProblem(
                        "consent_jurisdiction", clip.path, repr(clip.consent_jurisdiction)
                    )
                )
        return problems

    @staticmethod
    def _labels(gold: GoldSet, labels: Mapping[str, object]) -> list[IntegrityProblem]:
        problems: list[IntegrityProblem] = []
        for clip in gold.clips:
            for label_file in clip.label_files:
                problems += GoldSetCheck._label_file(gold, clip, label_file, labels)
        return problems

    @staticmethod
    def _label_file(
        gold: GoldSet, clip: GoldClip, label_file: str, labels: Mapping[str, object]
    ) -> list[IntegrityProblem]:
        if label_file not in gold.manifest.files:
            return [IntegrityProblem("label_not_in_files", label_file)]
        if label_file not in labels:
            return []  # the integrity check already reports the file as missing
        doc = labels[label_file]
        details = [p.describe() for p in validate_labels(doc)]
        named = doc.get("clip") if isinstance(doc, Mapping) else None
        if isinstance(named, str) and named != clip.path:
            details.append(f"clip: names {named!r}, expected {clip.path!r}")
        if not details:
            return []
        return [IntegrityProblem("label_invalid", label_file, "; ".join(details))]


def gold_set_of(manifest: Manifest) -> GoldSet | None:
    """The gold set a manifest declares, None for a plain fixture manifest (no ``schema``).

    An unknown ``schema`` is a format error, so a newer manifest is never checked as a fixture.
    """
    schema = manifest.extra.get("schema")
    if schema is None:
        return None
    if schema != GOLD_SCHEMA:
        raise ManifestFormatError(f"unknown manifest schema {schema!r}; expected {GOLD_SCHEMA!r}")
    return GoldSet.from_manifest(manifest)
