"""IT-06-01 (ST-170a; FR-170.R1-R3; ADR 0061 Rules 1 and 3.3): reference loader + filesystem.

* The valid fixture tree (``backend/tests/fixtures/references-valid``) lints with exit 0 and the
  loader returns its v1 entries.
* Each planted fixture tree in ``backend/tests/fixtures/references-invalid/<rule>/`` (one per
  refusal) exits 1, and a failure line names the entry (or the set version) and the field.
* The repository's own ``content/references`` tree lints with exit 0, so the backend suite in CI
  refuses a reference change that breaks a rule.
* A missing path exits 2.

Runs the real CLI against the real pattern catalogue and sources register (no mocks); a planted
tree that needs a pattern the catalogue does not have carries its own ``pattern-catalogue.md``.
Written red first: before ST-170a nothing checks a reference entry.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.support.paths import REPO
from tests.support.references import CATALOGUE, LINT, LOADER, SOURCES, lint_args

VALID = REPO / "backend" / "tests" / "fixtures" / "references-valid"
INVALID = REPO / "backend" / "tests" / "fixtures" / "references-invalid"
CONTENT = REPO / "content" / "references"

# rule folder -> (named entry or set version, field, reason text)
REFUSALS = {
    "missing-source": ("REF-AN09-D-INT", "source", "missing field"),
    "unresolved-citation": ("REF-AN09-D-INT", "source", "unresolved citation"),
    "measured-no-reference-library": (
        "REF-AN09-D-INT",
        "source",
        "footage FTG-0001 does not permit reference-library",
    ),
    "duplicate-entry": ("REF-AN09-D-INT-2", "entry", "duplicate entry"),
    "published-version-edited": ("pb-reference@1", "version", "published version changed"),
    "better-direction-mismatch": (
        "REF-AN09-D-INT",
        "better_direction",
        "differs from the catalogue",
    ),
    "inside-band-point-value": ("REF-AN09-D-INT", "band", "missing field"),
    "published-no-n": ("REF-AN13-D-INT", "n", "missing field"),
    # review round 1 (PE-R1-ST170a-01, F1, COACH-170a-01, SEC-R1-ST170a-01)
    "unsupported-interval-method": ("REF-AN04-D-INT", "interval_method", "none"),
    "citation-unresolved": ("REF-AN09-D-INT", "source", "unresolved citation SRC-0010"),
    "citation-exists-unfetched": ("REF-AN09-D-INT", "source", "unresolved citation SRC-0008"),
    "non-finite-band": ("REF-AN09-D-INT", "band", "must be a finite number"),
    "non-finite-wilson-value": ("REF-AN10-D-INT", "value", "must be a finite number"),
    "non-finite-median-value": ("REF-AN13-D-INT", "value", "must be a finite number"),
}


def _catalogue(root: Path) -> Path:
    """A planted tree may carry its own ``pattern-catalogue.md`` (a pattern the repository
    catalogue does not have yet); otherwise the repository catalogue."""
    planted = root / "pattern-catalogue.md"
    return planted if planted.exists() else CATALOGUE


def _lint(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    capsys.readouterr()
    rc = LINT.load()([*lint_args(root), "--catalogue", str(_catalogue(root))])
    out, err = capsys.readouterr()
    return int(rc), out + err


def test_valid_tree_lints_and_loads(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out = _lint(VALID, capsys)
    assert rc == 0, out

    sets = LOADER.load().load_reference_sets(VALID, CATALOGUE, SOURCES)

    assert [(s.name, s.version) for s in sets] == [("pb-reference", 1)]
    (only,) = sets
    assert [e.id for e in only.entries] == ["REF-AN09-D-INT", "REF-AN13-D-INT"]
    assert only.entries[0].band == (0.45, 0.70)
    assert only.entries[0].citation_id == "SRC-0002"


def test_every_refusal_has_a_planted_fixture() -> None:
    planted = sorted(p.name for p in INVALID.iterdir() if p.is_dir())
    assert planted == sorted(REFUSALS)


@pytest.mark.parametrize("rule", sorted(REFUSALS))
def test_planted_fixture_is_refused_naming_entry_and_field(
    rule: str, capsys: pytest.CaptureFixture[str]
) -> None:
    named, field, reason = REFUSALS[rule]

    rc, out = _lint(INVALID / rule, capsys)

    assert rc == 1, out
    assert any(f"{named}: {field}: " in line and reason in line for line in out.splitlines()), out


@pytest.mark.parametrize("rule", sorted(REFUSALS))
def test_loader_refuses_a_planted_fixture(rule: str) -> None:
    loader = LOADER.load()

    with pytest.raises(loader.ReferenceSetRefused) as refused:
        loader.load_reference_sets(INVALID / rule, _catalogue(INVALID / rule), SOURCES)

    assert refused.value.problems


def test_repository_reference_content_lints(capsys: pytest.CaptureFixture[str]) -> None:
    rc, out = _lint(CONTENT, capsys)

    assert rc == 0, out


def test_missing_path_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc, out = _lint(tmp_path / "nowhere", capsys)

    assert rc == 2, out
