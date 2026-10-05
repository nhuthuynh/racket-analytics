# Sprint 1 test plan status (tests first)

- **Owner:** senior-qa-engineer. **Date:** 2026-10-05 (Sprint 1 D1). **Branch:** `sprint-01`.
- **Rule (unchanged from Sprint 0):** every test below was written **before** its code and fails on its own for the right reason. Red-first tests carry `red_until(story=…)`, which the Stop hook deselects (`scripts/test-unit.sh`) and CI runs. The implementing story turns them green **without editing them**; a needed change is a row in `test-change-requests.md` for QA. Seams (names the tests call) live in one QA-owned file, `backend/tests/support/contract.py` (ADR 0012); the engine seams match `docs/architecture/scoring-engine.md`, the HTTP seams `docs/architecture/api-sprint-01.md`.
- **DoR item P2 (sprint-01 §14.5):** QA agrees that every criterion in §7 and §14.3 is testable; the level of each is named in §2 below. **Closed** for ST-013..ST-025 (ST-019 stretch: bound in the browser since QA-R2-03).

## 1. How to run

```bash
cd backend
eval "$(bash ../scripts/dev-postgres.sh start >/dev/null; bash ../scripts/dev-postgres.sh url)"
bash ../scripts/dev-objectstore.sh start; eval "$(bash ../scripts/dev-objectstore.sh env)"
export MAILPIT_API_URL=http://127.0.0.1:8025       # Compose mailpit (magic-link tests)
env -u APP_ENV uv run pytest -q -m "red_until"      # the Sprint 1 red-first set
env -u APP_ENV uv run pytest -q -m scoring          # demo step 6 (ST-020/021/022/023)
env -u APP_ENV uv run pytest -q -m "scoring and needs_verification"   # the 19 provisional rows
uv run python -m tests.oracle.differential --sequences 100000 --json oracle.json   # P9 (nightly)
cd ../web && MAILPIT_API_URL=… BASE_URL=… pnpm exec playwright test e2e/sprint-01
```

## 2. Status per story (2026-10-05, before implementation)

Counts are test cases. "Green now" are regression guards or positive controls that already hold on the Sprint 0 code; they must stay green.

| Story | Gherkin (tests/features/) | Levels and files | Red now | Green now | Red reason (first failure) |
|---|---|---|---|---|---|
| ST-013 | `sign_in.feature` (§7.1, §14.3.1) | Scenario (API): `backend/tests/features/test_sign_in.py`; Integration IT-01-01..03 + T-ML-1/3/6/7/8/10/14: `backend/tests/integration/test_it_01_01_magic_link.py`; E2E-01-01: `web/e2e/sprint-01/sign-in.spec.ts` | 4 + 10 + 5 | — | `POST /auth/links` → 404; A-01 "Email address" field absent |
| ST-014 | `sign_out.feature` (§7.1, §14.3.2) | Integration IT-01-04: `test_it_01_04_no_store.py`; E2E: `sign-out.spec.ts` | 2 + 3 | — | `GET /me` without `no-store` / no `Clear-Site-Data`; sign-in UI absent |
| ST-015 | `first_run_and_capture_guide.feature` (§7.2, §14.3.3) | E2E only (static client content): `first-run-and-guide.spec.ts` | 5 | — | sign-in UI absent (F-01 follows it) |
| ST-016 | `match_setup.feature` (§7.3, §14.3.4) | Scenario (API): `test_match_setup.py`; Integration IT-01-05 + T-MS-1/3: `test_it_01_05_participants.py`; E2E + E2E-01-03 + reflow 320/360/768/1280: `match-setup.spec.ts` | 4 + 16 + 13 | — | `POST /matches` ignores `participants`; Q-01..Q-07 absent |
| ST-017 | `resumable_upload.feature` (§7.4, §14.3.5) | Scenario (API): `test_resumable_upload.py`; Integration IT-01-06..08 + T-UV-5/6/7/8: `test_it_01_06_tus_extensions.py`; E2E-01-02: `resumable-upload.spec.ts` | 3 + 12 + 6 | 1 + 1 | no checksum/expiration extension; no `upload` object in the read model |
| ST-018 | `upload_validation.feature` (§7.5, §14.3.6) | Scenario (API): `test_upload_validation.py`; Integration IT-01-09/10 + T-UV-1..4: `test_it_01_09_upload_validation.py`; E2E: `upload-validation.spec.ts` | 6 + 5 + 5 | 1 + 2 | no magic-byte or size check; no `rejection` in the read model |
| ST-020 | `scoring_engine_mechanics.feature` (§7.7) | Scenario: `test_scoring_engine_mechanics.py`; static IT-01-12/13: `backend/tests/unit/sports/pickleball/test_rules_static.py` | 10 + 3 | 2 (scanner controls) | `RED until ST-020: seam 'racket.sports.pickleball.rules:RulesConfig'` |
| ST-021 | `match_structure.feature` (§7.10, M-01..M-08) | Scenario: `test_match_structure.py` | 7 | — | `RED until ST-020` (rules), then `ST-021: racket.matches.domain:MatchState` |
| ST-022 | `property_and_oracle.feature` (§14.3.7) | Hypothesis P1-P8: `backend/tests/unit/sports/pickleball/test_rules_properties.py`; scenarios: `test_property_and_oracle.py`; oracle P9: `backend/tests/oracle/` | 8 + 5 + 1 | 1 + 21 (oracle self-tests, positive control) | `RED until ST-020: seam 'racket.sports.pickleball.rules'` |
| ST-023 | `side_out_doubles_provisional.feature` (§7.8), `faults_provisional.feature` (§7.9), M rows in `match_structure.feature` | Scenario: `test_side_out_doubles_provisional.py`, `test_faults_provisional.py` | 13 + 8 | — | `RED until ST-020: seam 'racket.sports.pickleball.rules:PRESETS'` |
| ST-024 | `nightly_quality.feature` (§14.3.8) | Scenario: `test_nightly_quality.py` (SLI arithmetic + the `nightly` key of `status.json`) | 1 | 4 (SLI rows, green since `595e5a5`) | `status.json` has no `nightly` result until the first nightly run on GitHub (needs ST-020 for the oracle) |
| ST-025 | `phone_fixtures.feature` (§14.3.9) | Scenario: `test_phone_fixtures.py` | 3 | — | `fixtures/clips/phones-v1/manifest.json` does not exist |
| ST-019 (stretch) | `footage_quality_report.feature` (§7.6) | Bound after ST-019 was pulled in (`6cc2259`; QA-R2-03). E2E '30 fps video': `web/e2e/sprint-01/footage-quality-report.spec.ts` (fixture `fixtures/clips/phone-profiles-v1/h264-mp4-1080p30.mp4`); wording: Vitest `web/tests/unit/quality-report.test.tsx` | — (written after the story landed; negative control: the same spec with the 1080p60 clip fails at `Recorded at 30 fps`) | 1 + 5 (Vitest) | — |

Backend totals for the Sprint 1 red-first set: `env -u APP_ENV uv run pytest -q -m red_until tests` → `113 failed, 9 passed, 1 skipped, 8 errors` (the 8 errors are the P1-P8 property tests failing in their fixture before Hypothesis starts). Browser: `playwright test e2e/sprint-01` against the Sprint 0 web image → `37 failed, 6 skipped` (36 at the A-01 "Email address" field, 1 at its field count); Sprint 0 journeys on the same stack `7 passed`.

## 3. `@needs-verification` (reported separately; never counted toward a Must FR, QD-QG-P5, ADR 0009)

| Rows | Cases | Feature | Status |
|---|---|---|---|
| SOD-01..SOD-12, SOD-16 (13 rows) | 13 | `side_out_doubles_provisional.feature` | provisional preset `PROVISIONAL-UNVERIFIED`; OQ-01 rulebook not yet supplied |
| F-01..F-06 (6 rows) | 8 (F-06 has 3 cases) | `faults_provisional.feature` | same |
| **Total: 19 rows** | **21 cases** | `-m "scoring and needs_verification"` | removal row by row with the coach once `@rule-<n>` is recorded (QD-TR-07) |

The M rows (M-01..M-08), the §7.7 mechanics, P1-P8 and P9 are **Ready** (explicit inputs, no rulebook claim, ADR 0009 part a) and count toward FR-040/041/044/045 (a) and NFR-002.

## 4. Positive controls and mutants (testing-strategy §3 rule 8)

- Scoring suite against a throwaway fake of the seams (scratchpad, never committed): `68 passed, 1 skipped`. Five mutants each caught: receiving side scores → 10 failed; replay scores → 6; NVZ fault reversed → 6; no court switch → 1 (SOD-06); target off by one → 7.
- Oracle: reproduces every SOD/F row read from the feature files; a deliberately wrong engine is caught with a minimal disagreeing sequence (`backend/tests/oracle/test_oracle.py`, `mutants.py`). Against the fake, the 100,000-sequence scenario passes in 42.6 s.
- Every refusal test in IT-01-04/05/06/09 sits next to its accepted case in the same file (valid MP4, valid doubles/singles, good chunk after a bad one, `/me` before sign-out).
- IT-01-12/13 scanners: positive controls on temporary files.

## 5. Skips (each with a reason and a pointer)

| Test | Reason | Covered by |
|---|---|---|
| `test_p3_rally_scoring_every_counted_rally_scores` | Rally scoring is blocked (FR-043, OQ-01) | written when rally scoring is Ready |
| E2E "is 16 minutes old" | needs a 16-minute wait | `test_sign_in.py` with `MAGIC_LINK_TTL_SECONDS=2` |
| E2E singles-three and two-"me" rows | not enterable in the UI (two fields; radios) | `test_match_setup.py`, IT-01-05 |
| E2E "The unfinished upload has expired" | needs a 24 h wait | `test_resumable_upload.py` with `UPLOAD_EXPIRY_SECONDS=1` |
| E2E "Carlos tries to send data" | no UI path for another user | `test_resumable_upload.py`, BOLA matrix |
| E2E "a 12 GB video", "Declared size above the cap" | a 12 GB file cannot be handed to the browser in CI | `test_upload_validation.py`, IT-01-09; FE Vitest for the client size check |

## 6. New fixtures and helpers

- `fixtures/clips/long-4h/` (203 KB, real 14,400 s 64×64 1 fps H.264, CC0, no people) from `scripts/fixtures/generate_long_4h.sh`; its manifest passes `tests/integration/dataset` (`12 passed`).
- `backend/tests/support/`: `scoring.py` (call parsing, P1-P8 checks), `golden_tables.py` (rows read from the feature files), `mailpit.py`, `auth.py`, `copy.py` (API code → flows copy, api-sprint-01 §1.1), `tus_ext.py`, `media.py`. `web/e2e/helpers/sprint-01.ts` (Mailpit sign-in, setup answers, padded multi-chunk MP4).

## 7. Routed to other roles (ADR 0022 routing)

| # | Item | Owner |
|---|---|---|
| R1 | `docs/architecture/scoring-engine.md` §2.4 defers positions to Sprint 2, but sprint-01 §7.8 / ST-023 keep SOD-06 (and SOD-05's court switch) in Sprint 1. Amend §2.4 with `server_player` and `right_court_player` (QD-RE-03 names, as in `contract.py`), or ask the EM to move SOD-06 | principal-engineer |
| R2 | CI integration job: export `MAILPIT_API_URL` (Mailpit UI port) and the app's `MAIL_SMTP_URL`; without them the magic-link tests fail in CI by design (`CI=true`) | sre-devops-engineer |
| R3 | PR CI: deselect `-m "not nightly"` (the 100,000-sequence scenario takes ~43 s); the nightly job runs it (or the `tests.oracle.differential` CLI, as `595e5a5` does) | sre-devops-engineer |
| R4 | Confirm the QA seam proposals at story start: auth log event names (`AUTH_LOG_EVENTS`), `racket.matches.domain:Participants`, `racket.video_ingest.domain:UploadPolicy`, env names `UPLOAD_EXPIRY_SECONDS`, `UPLOAD_MAX_BYTES`, `MAGIC_LINK_TTL_SECONDS` | senior-backend-engineer |
| R5 | `fixtures/clips/phones-v1/manifest.json` per-clip entries (`device_model`, `fps`, `vfr`, `shows_people`, `consent_record`) and the consent rule in `racket-manifest-check` | senior-ml-cv-engineer |
| R6 | Selectors and copy in `web/e2e/sprint-01/` follow flows-sprint-01 exactly (role, label, text). A needed change is a test-change row, not an edit | senior-frontend-engineer |
| R7 | `status.json` test fields for ST-022/ST-023 (implemented units) from this file | engineering-manager |
