# 0035. Gold-set manifest v1 and Full Tag labels v1, checked by racket-manifest-check

- **Status:** Proposed (accepted on review by principal-engineer and senior-qa-engineer; consent part on review by security-privacy-engineer, R8)
- **Date:** 2026-10-06
- **Deciders:** senior-ml-cv-engineer (author); principal-engineer, senior-qa-engineer (reviewers)
- **Consulted:** security-privacy-engineer (consent, US and AU), pickleball-domain-coach (endings, facets)
- **Related:** ST-040, FR-150, FR-151, NFR-070, NFR-078, QD §8, QD-GD-02..07, QD-TX-01..03, QD X3, OQ-05, OQ-06, ADR 0023, ADR 0004, context map C2 / R9 / R10

## Context and problem statement

FR-151 needs every gold set to carry a manifest with QD §8's fields, frozen per sprint, split by venue with ≥ 3 held-out venues. FR-150's Full Tag tool needs an export format. Neither existed: `racket-manifest-check` (ST-011, ST-025) only checks hashes, versions and per-clip consent. Without a schema, the first labelled match (QD-GD-03 for R1 metrics, QD-GD-04 for M1) would set the format by accident, and leakage across venues or unagreed facets would only be found after an eval report used them.

## Decision drivers

- Gold sets are never edited to raise a score; problems must be caught before an eval reads the set (EP/ENG-27, EP/ENG-28).
- Consent (OQ-06, ADR 0023): only synthetic, empty-court or team-recorded footage with written consent, participants in the US or AU; nothing from real users before the legal review (NFR-070).
- One vocabulary with Match & Scoring (slots, sides, endings, fault kinds) so gold outcomes can drive the scoring and analytics evals (QD-GD-02/-03) without a mapping layer.
- Pure domain code with no I/O (ddd-guidelines §4.5); one CI gate, not a second tool.

## Considered options

1. **Extend `racket-manifest-check`: a manifest with `"schema": "gold-set-manifest/v1"` is checked as a gold set; labels are JSON per clip and labeller (`full-tag-labels/v1`), frame-based** (chosen).
   - Good: one gate in CI already (`scripts/ci/check_fixtures.sh`); fixture manifests stay valid unchanged; an unknown schema id fails (exit 2) instead of passing as a fixture; per-file labels keep the sha256 rule per file and make a single changed label visible.
   - Bad: hand-written validator (≈ 250 lines) instead of a JSON Schema library; JSON is verbose for long matches (≈ 1-2 MB per match, judgment).
2. **JSON Schema documents plus a generic validator (e.g. `jsonschema`).**
   - Good: standard, tool support in editors.
   - Bad: cross-field rules (responsible-player side, events inside rallies, venue split, κ gates, admitted facets) still need code; a new runtime dependency and licence check for the backend; two places to read the rules.
3. **Reuse an existing sport schema (ShuttleSet, DOM/CV-18) or a COCO/MOT layout.**
   - Good: known formats.
   - Bad: ShuttleSet is badminton and serves as a schema reference only; COCO/MOT carry boxes and tracks, not rallies, outcomes or facets; our outcome vocabulary would still need a mapping.
4. **Do nothing until footage exists.**
   - Bad: the first set defines the format implicitly; FR-151 has no check; ST-040 not met.

## Decision outcome

Option 1. Details in `docs/data/gold-label-schema.md`; capture and consent rules in `docs/data/gold-capture-protocol.md`.

- **Manifest v1** adds `schema`, `created`, `purpose` (vision, analytics, scoring, fixture), `label_schema`, `rules_version`, `metric_dict_version`, `labellers` (role IDs only, `@` refused), `agreement` (facet, κ, n, admitted), `venues` (id, split) and per clip `label_file`, `second_label_file` (double-labelled), `venue_id`, `consent_jurisdiction`.
- **Rules:** vision sets need ≥ 3 held-out venues with clips and ≥ 20% double-labelled clips (QD-GD-04); an admitted shot facet needs κ ≥ 0.7 on ≥ 300 shots (QD-TX-03), an admitted `ending` κ ≥ 0.6 (QD X3); labels carry only admitted shot facets; `consent_status` ∈ {synthetic, consented}; a synthetic set shows nobody; a clip with people names US or AU.
- **Labels v1:** frames, not milliseconds (hit timing is judged per frame, CV-T07); slots A1/A2/B1/B2; endings and fault kinds pinned equal to Match & Scoring's by a unit test; `position` refused (derived by rule, QD-TX-01); bounce visibility and optional court position in metres.
- **Example set** `fixtures/gold/example-full-tag-v1` (synthetic, schema-only labels, no admitted facets because no agreement was measured) keeps the gold path exercised by CI on every PR. It is not an evaluation set.

### Consequences

- Good: the first real set is checked the day it is committed; leakage across venues is impossible by construction (split is per venue); unagreed facets cannot enter; consent and jurisdiction are machine-checked.
- Bad: gates (κ 0.7 / n 300, 20%, 3 venues) are judgment values from QD and the engineering brainstorm; changing one needs a new ADR. The QA committed-set test (`tests/integration/dataset/test_committed_fixture_sets.py`) runs only the integrity part; the gold part runs through the CLI in CI (asked of QA to add, progress row 2026-10-06).
- Neutral: Full Tag (FR-150) is not built; this fixes its export format only.

## Evidence

- `cd backend && env -u APP_ENV uv run pytest -q tests/unit/dataset/` → 176 passed (2026-10-06; red first: `ModuleNotFoundError: racket.dataset.labels` / `gold_set`, and 3 failing `second_label_file` tests before that rule).
- `bash scripts/ci/check_fixtures.sh HEAD` → `OK … example-full-tag-v1 v1, gold set (vision), 11 files`, rc 0.
- Negative CLI runs on tampered copies: edited label → rc 1 `[label_invalid]` naming `labels/c3.json` and both problems; one held-out venue moved to train → rc 1 `[held_out_venues]` (2 < 3); `schema` v2 → rc 2; unparsable label → rc 1 `[label_invalid]` with the JSON error.
- Example set rebuilt twice: identical sha256 for all files (deterministic encoder flags).
