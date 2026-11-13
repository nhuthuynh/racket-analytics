# QA-REF-GOLD decisions

Per-ticket decision file (working-agreement §3). Ticket: QA-REF-GOLD, "Frozen expected values for reference v1 × GS-PAT-1, written before the extractors; integrity test" (`docs/sprints/sprint-06.md` §3.3). Story ST-170 (reference pattern set). Owner: senior-qa-engineer; reviewer of the values: pickleball-domain-coach (writer/reviewer split, kickoff QA-3). Review tier 1 (ADR 0056). Covers FR-171.R2-R4 (AN-09, AN-13 measures; AN-08 as the ST-171d stretch) and FR-172.R1 (with R2-R4: states and order), ADR 0061 Rule 6 (JSON vectors are the port's conformance suite).

## 1. What is frozen

| File (under `backend/tests/regression/golden_patterns/`) | Content |
|---|---|
| `vectors/measures.gs-pat-1-v1.json` | AN-09, AN-08, AN-13 per match × side of GS-PAT-1 v1: value, n, interval, interval_method, low_sample, rankable, n_excluded, definition_version, unavailable_reason (compared), n_censored for AN-13 (compared), plus k, mix, samples, l and exclusions per reason (for the port and the hand-count cross-check) |
| `vectors/gaps.gs-pat-1-v1.golden-reference-v1.json` | 6 cases (gp1-doubles × sides A, B × level bands beginner, intermediate, advanced): input rows (frozen measure, better_direction, min_n, catalogue order, rallies lost on the linked ADR 0003 cell, reference band or none) and the expected state, side, gap size, rank and order |
| `references/golden-reference/v1.json` + `references/references.lock` | the reference set the gap cases use (8 `judgment` doubles entries, status `draft`), linted rc 0 by `racket-reference-lint` |
| `golden.lock.json` | sha256 of the four files above and of the input `docs/domain/hand-counts/GS-PAT-1-v1.json`, in change rows that each name an ADR |

Expected results on the gap cases (gap size in band widths):

| Case | AN-09 | AN-08 | AN-13 | Order |
|---|---|---|---|---|
| G1-A-INT | no clear gap (overlap) | not enough data (19 of 20) | no clear gap (touching ends 3 = 3) | none |
| G1-B-INT | not enough data (18 of 20) | no clear gap (overlap) | no clear gap (touching ends) | none |
| G1-A-ADV | weakness above band, 0.136 | not enough data | weakness below, 0.250 | AN-13, AN-09 (size beats catalogue order) |
| G1-B-ADV | not enough data | weakness below, 0.312 | weakness below, 0.250 | AN-08, AN-13 |
| G1-A-BEG | weakness above band, 0.536 | not enough data | no reference yet | AN-09 |
| G1-B-BEG | not enough data | no clear gap (better side) | no reference yet | none |

## 2. Decisions

| Date | Role | Decision | Evidence | Reason |
|---|---|---|---|---|
| 2026-11-13 | senior-qa-engineer | **The gap cases use a QA golden reference set, not COACH-6c's `content/references` v1.** COACH-6c is not merged (it waits on CI-REF-BASE-LOCK); the ticket must land before ST-171b/c and ST-172a. The golden set is test content in the reference-set/v1 schema (lint rc 0), every entry `judgment`, status `draft`, citing SRC-0002 (the A2/A6 rules it exercises), never a coaching claim and never shipped | `references/golden-reference/v1.json`; `test_integrity.py::test_golden_reference_set_lints` | Vectors must exist before the code they judge (kickoff QA-3); the product content will change by version, the conformance vectors must not. The real v1 × GS-PAT-1 replay is IT-06-06 (ST-172b) |
| 2026-11-13 | senior-qa-engineer | **Measures are QA's own count, then checked against the coach's.** A QA replay written from catalogue v0.1 §0-§5 (no product, no `scripts/measure/`, no `pattern_example.py`) gave the vectors; it equals the coach's hand count bucket by bucket (0 differences), and gp2-singles was recounted by hand from the rally sheet. The IT `test_measure_vectors_equal_the_coach_hand_count` keeps the two counts tied | §4 below | ADR 0044 writer/reviewer split; a frozen file written from the code under test proves nothing |
| 2026-11-13 | senior-qa-engineer | **No edit without an ADR:** a frozen file's sha256 must equal its last lock row; a row is valid only with a `docs/decisions/NNNN-*.md` that exists, names QA-REF-GOLD and authorised no earlier row, in date order; every file under `vectors/` and `references/` must be locked. The lock sits under `backend/tests/`, so editing it also needs `qa-approved-test-change` | `integrity.py`; unit `tests/unit/test_golden_patterns_integrity.py`; `tests/features/golden_patterns.feature` | Sprint plan §3.3 "a hash test refuses edits without an ADR"; ADR 0061 Rule 3.1 "Adding a method is a new ADR note with QA-REF-GOLD vectors" |
| 2026-11-13 | senior-qa-engineer | **The GS-PAT-1 v1 input fixture is hashed too.** A coach edit to it turns the integrity test red; a changed fixture is GS-PAT-1 v2 with new vectors and a new ADR | lock row 1 | The vectors are only true for the exact labels they were counted on |
| 2026-11-13 | senior-qa-engineer | **Product goldens are `red_until` their stories**, one file per story so `red_until_report.py` names it: `test_golden_an09.py` ST-171b, `test_golden_an13.py` ST-171c, `test_golden_an08.py` ST-171d, `test_golden_gap.py` ST-172a. The per-PR gate selects `not red_until`; the report fails when a row passes, so each story removes its marker (TCR row) in its own PR | §4 red evidence | Sprint plan: "the golden test is red until the extractors exist (recorded)" |
| 2026-11-13 | senior-qa-engineer | **Seams are QA proposals**, confirmed with the implementing lane at story start (`tests/support/contract.py` rule): `racket.analytics.patterns.full_tag:full_tag_measures(labels)` returning `measures[pattern][side]` of `PatternMeasure` (AN-13 with `n_censored`, FR-171.R4), and `racket.coaching.weakness.reference_gap:conformance_case(case)` taking a gaps case's `rows` and returning `results` and `order`. A seam or binding change is a TCR row; a vector change is an ADR | `seams.py`, `_measure_case.py`, `test_golden_gap.py` | ADR 0061 Rule 6: the JSON vectors are what a port must pass unchanged; the Python entry points can be renamed without touching them |
| 2026-11-13 | senior-qa-engineer | **AN-13 below n = 6 keeps `interval_method: order_statistic_median` with no interval** (gp2-singles, n = 2) | measures vector | The method is the pattern's (catalogue §1); FR-171.R4: "below n = 6 the interval does not exist", never a Wilson interval |
| 2026-11-13 | senior-qa-engineer | **Not frozen (stated in the gaps file `not_frozen`):** (a) a pattern with neither a reference nor min_n: whether it reads "no reference yet" or "not enough data" is not fixed by FR-172.R2/R3 or ADR 0061 Rule 3; asked of the principal-engineer and business-analyst for ST-172a (open question Q-GOLD-1); (b) equal gap sizes: GS-PAT-1's Wilson edges give none, so the rallies-lost and catalogue-order tie-breaks are ST-172a unit and property tests; (c) singles: every gp2-singles measure is low-sample and no singles reference exists, so it would only hit (a). gp2-singles measures are frozen | gaps vector `not_frozen` | A frozen value for an undecided rule would decide it without the owner |
| 2026-11-13 | senior-qa-engineer | **Rallies lost on the linked ADR 0003 cell are 0 for AN-08, AN-09 and AN-13:** no weakness-catalogue §5 cell has them as its primary metric | `docs/domain/weakness-catalogue.md` §5 | ADR 0061 Rule 3.5: "with no linked cell the term is 0" |
| 2026-11-13 | senior-qa-engineer | **Floats are unrounded, compared at 1e-9 absolute** | `tolerance_abs` in both vectors | ADR 0061 Rule 6 "rounding only at serialisation"; a port's last-ulp difference is not a defect |
| 2026-11-13 | senior-qa-engineer | **One red-commit test fix before the first push:** `test_gap_reference_rows_are_the_golden_reference_entries` compared a reference `status` the gap rows do not carry (the ACL filters by status before the gap rule, ADR 0061 Rule 1, so status is not a gap input); it now compares `version`. No assertion weakened | commit after `6459f5ad` | Nothing pushed yet; no TCR row needed for a test that never reached `main` (ST-170a precedent) |

## 3. Not met: waiting on

| Item | Waiting on | What the team prepares |
|---|---|---|
| Product goldens green (G06-02, G06-03) | ST-171b, ST-171c, ST-171d (stretch), ST-172a | the vectors, seams and `red_until` rows in this PR |
| Coach review of the vectors (writer/reviewer split) | pickleball-domain-coach on this PR | the hand-count cross-check IT and the §1 table |
| State precedence (Q-GOLD-1) | principal-engineer, business-analyst (ST-172a start) | an additive vector file with a new ADR once decided |

## 4. Evidence

QA replay against the coach's hand count (scratch script, not committed; standard library):

```text
$ python3 -I qa_replay.py docs/domain/hand-counts/GS-PAT-1-v1.json
gp1-doubles A AN-09 16 20 0.8 0.5839825677481064 0.919342337420202 excl 4
gp1-doubles A AN-13 [0, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 4] (2.0, (1, 3), 3) n 12 cens 13 excl 12
...
qa-replay: 0 difference(s) against the coach hand count
```

Red (commit `6459f5ad`, before any frozen file): `cd backend && uv run pytest -q tests/unit/test_golden_patterns_integrity.py tests/regression/golden_patterns tests/features/test_golden_patterns.py` → `39 failed`: "RED until QA-REF-GOLD: no integrity check", "frozen file .../vectors/measures.gs-pat-1-v1.json is missing", "golden.lock.json is missing", lint `references.lock: missing`.

Green (frozen files and `integrity.py`): same command → `24 failed, 34 passed`; the 24 are exactly the `red_until` rows, each "RED until ST-171b|ST-171c|ST-171d|ST-172a: seam ... is not implemented yet (ModuleNotFoundError ...)". Gate selection `-m "not red_until"` → 34 passed.

Harness self-check (temporary modules, deleted, never committed): with a product stand-in built from the QA replay and the ADR 0061 Rule 3 text, the 30 golden rows pass; with one gap state flipped, 8 of 12 gap rows fail.

## 5. Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd | Note |
|---|---|---|---|
| Author build | not measured | not measured | the session does not expose per-ticket wall time or cost to the agent |
