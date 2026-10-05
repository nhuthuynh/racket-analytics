# Sprint 1 report: Sign in, set up a match, upload safely; the scoring engine, test-first

- **Prepared by:** engineering-manager, 2026-10-05, for the sprint review planned on 2026-10-30 with the human product owner (PO).
- **Timing caveat:** the sprint was planned for 2026-10-19 to 2026-10-30. All the work, the integration smoke and three review rounds ran in one compressed agent session on 2026-10-05. Calendar metrics (lead time, time-to-merge, nightly streaks) cannot be measured.
- **Inputs:** lane results, [`smoke.md`](smoke.md), [`review-rounds.md`](review-rounds.md) (rounds 1-3), [`blockers.md`](blockers.md), [`decision-log.md`](decision-log.md), [`test-change-requests.md`](test-change-requests.md), [`test-plan-status.md`](test-plan-status.md), [`ci-status.md`](ci-status.md), ADRs 0023-0029, GitHub Actions and branch listings, and the EM's own re-run of the suites (§5).
- **Machine-readable status:** [`status.json`](status.json). **Progress:** [`progress.md`](progress.md). **Retro:** [`docs/retros/2026-10-30-sprint-01.md`](../../retros/2026-10-30-sprint-01.md). **Process ADR from the retro:** [ADR 0030](../../decisions/0030-finding-disposition-isolated-evidence-and-pre-sliced-stories.md).

## 1. Verdict

> **Dated note, 2026-10-05 (engineering-manager, sprint-close review round 1: PE-R1-S1-02, QA-V1-04).** Under the PO standing rule the **Sprint 1 goal is not demonstrated and Sprint 1 is not done.** [`goal-scorecard.md`](goal-scorecard.md) has no verified row yet; the reviewers' isolated runs at `488d574` already show G01-03, G01-08 and G01-11 as "no". The verdict below describes what is built, not a goal pass. The sprint stays open until a verifier fills all 12 rows "yes" from one isolated run (scorecard §2 status, §3).

**Goal partly met.** All four goal bullets (sprint-01 §1) are built and work locally on real services:

- Sign-in by magic link and sign-out.
- The capture guide and the match setup flow.
- Resumable, validated upload.
- The pure, configurable scoring engine with its provisional tables, property suite and oracle.

25 of 32 committed units are implemented (78%), plus the ST-019 stretch unit. The isolated backend run gives `3 failed, 1060 passed, 6 skipped`. The 3 failures are open blockers that need the PO: phone clips for ST-025, and a nightly run for ST-024.

**No story meets the full story DoD** (0 of 32 units), for three reasons:

1. **CI has not run on any head that holds the Sprint 1 fixes.** The only sprint-01 run, 37298471332 (head `2390e9a`), failed. GitHub `sprint-01` is at `961648e`, local is later, and no CI or nightly run was dispatched. WebKit (iOS Safari, release-blocking per OQ-17) is therefore unverified for ST-013 to ST-019.
2. **The fix loop hit its 3-iteration limit.** Round 3 left 2 blockers and 14 majors open (§6). At close, the EM also found **5 round-1 design blockers** (PD-R1-01..05) that never got a disposition row and are still open in the code or the docs, plus 2 round-1 majors (PD-R1-07, and the WebKit item PE-R1-04/QA-R1-04) (`review-rounds.md`, last table). Under working-agreement §7.5 all of these are escalated to the PO. The implemented count of 25 units is therefore an upper bound: the counting rule checks each lane's own tests, and these defects have no test.
3. **External evidence is open:** the design review (P7, scheduled 2026-10-06), the coach's sign-off on the capture-guide wording, the first nightly oracle run, the mutation baseline, real phone clips and real phones.

The PO's WebKit cookie directive (https for the dev stack, never an insecure cookie) is done. ADR 0029 covers it, and since then no WebKit test has failed at sign-in (CI job 111725272519). The remaining WebKit failures are product and test issues, not cookie issues (S-09).

## 2. Committed vs done per story

Units come from ADR 0010. **Implemented** means: committed, reviewed (3 rounds), and the lane's own tests green in the latest isolated run without depending on an undecided test-change row (the counting rule in `status.json`). **DoD-done** additionally needs a green CI run that includes the story's commits, and all external evidence closed.

| Story | Units (lanes) | Implemented | DoD | Evidence | Open (owner) |
|---|---|---|---|---|---|
| ST-013 Magic-link sign-in | 3 (BE 2, FE 1) | 3 | 0 | BE `deea4e3`, `93993af`, `625cf0b`; FE `e845c22`, `71da707`. IT-01-01..03 and T-ML-12 green. Magic link with Mailpit: 12 passed (security round 2). QA round 3: `sign-in.spec.ts` 4 passed, `:54 --repeat-each=5` → 5 passed | SEC-R3-S1-01 identity key (PE), SEC-R3-S1-02 idle/cap tests, SEC-R3-S1-03 T-ML-5 test (QA), PD-R3-01 refocus (FE), ASVS 6.3.3 risk (PO), design review, WebKit |
| ST-014 Sign-out clears the device | 1 (FE 1) | 1 | 0 | `673fdc1`; IT-01-04 green; sign-out journey 3 passed (smoke) | WebKit `sign-out.spec.ts:46` (FE), CI |
| ST-015 First run and capture guide | 2 (FE 2) | 2 | 0 | `b40db17`; journey 5 passed; copy matches the wording doc word for word (PD round 3) | WebKit guide track (PD-R1-02, FE), **coach sign-off still `draft`**, design review, CI |
| ST-016 Match setup | 5 (FE 4, BE 1) | 5 | 0 | BE `bcdc7d0`; FE `aa52c48`. IT-01-05 green. `match-setup.spec.ts` 13 passed incl. E2E-01-03 keyboard-only and the reflow matrix | T-UV-10 nickname test (QA), design review, CI |
| ST-017 Resumable upload | 4 (BE 2, FE 2) | 2 | 0 | BE `78902e0`, `c5b5367`; FE `722f0c5`, `111f2d4`. IT-01-06..08 green; E2E-01-02 green on Chromium | BE not counted: its scenarios pass only through Pending TCR row 32(a) (QA-R3-01). PE-R3-01 (BE), PE-R3-03/PD-R3-02, PD-R3-03 (FE), QA-R3-02 (QA), WebKit damaged chunk |
| ST-018 Upload validation | 3 (BE 2, FE 1) | 3 | 0 | BE `1d099e5`, `4aaccbb`; FE `722f0c5`. IT-01-09/10 green; upload-validation.spec green after the disk was freed (6 passed, 2 skipped, PD-R3-07) | PE-R3-02 delete-before-commit (BE); caps provisional until R-05 (ML/PO); CI |
| ST-020 Scoring engine core (a) | 4 (BE 4) | 4 | 0 | `77a5082`, `5999097`, `52953f0`, `131dcb7`, `4f10ba2`. IT-01-12/13 green. Coverage 99% (QA round 2) | Presets PROVISIONAL-UNVERIFIED (OQ-01); scoring-engine.md §2.2/§2.4 amendment (PE); CI |
| ST-021 Match structure (a) | 1 (BE 1) | 1 | 0 | `45eb70d`; M-01..M-08 green | CI; PE-R1-10 nit |
| ST-022 Property suite, oracle, mutation baseline | 2 (QA 2) | 0 | 0 | P1, P2, P4-P8 green under the `ci` profile (P3 skipped, FR-043). Oracle P9 locally: 100,000 sequences, 0 disagreements (lane report) | **Not counted:** no mutation baseline, and no nightly run on GitHub |
| ST-023 Golden tables | 2 (QA 2) | 2 | 0 | `0c152f9`, `47ea499`. 26 `@needs-verification` cases green, reported separately (§5) | Coach review; OQ-01 rulebook files |
| ST-024 Nightly jobs and SLIs | 2 (SRE 2) | 2 | 0 | `595e5a5`; infra `test_nightly_quality.py` green; 4 SLI scenarios green | Nightly never dispatched; `test_nightly_run_completes` red (PO dispatch) |
| ST-025 Phone fixtures and R-05 | 2 (ML 2) | 0 | 0 | `30baddc`, `10170c6`, `281d459`: consent rule, synthetic profile set, protocol | **Blocked:** real phone clips from the PO; 2 tests red on purpose |
| SPIKE-06 Phone-browser upload | 1 (FE 1) | 0 | 0 | `9c1030d`, ADR 0028 Proposed with desktop proxy data | Real iOS Safari / Android Chrome runs (PO or tester) |
| **Committed total** | **32** (BE 12, FE 12, QA 4, SRE 2, ML 2) | **25** (BE 10, FE 11, QA 2, SRE 2, ML 0) | **0** | | |
| ST-019 Footage quality report (stretch) | 1 (FE 1) | 1 | 0 | `6cc2259`; scenario bound in `073d3f3` | Design review, WebKit, CI |

**Ratio:** 25 / 32 = 0.78 implemented; 0.00 DoD-done. Sprint 0 was 19 / 28 = 0.68 and 0.00.

## 3. Quality gates (sprint-00 §8 per-PR gates plus sprint-01 §8)

"Local" means this sandbox on real services. "CI" means GitHub Actions; no CI run includes the Sprint 1 fixes.

| Gate | Threshold | Status | Command → result |
|---|---|---|---|
| Ruff, mypy, ESLint, tsc | 0 errors | **Pass (local)** | EM, `cf8cd19`: `uv run ruff check .` → All checks passed!; `uv run mypy` → no issues in 76 source files; `pnpm exec tsc --noEmit` rc=0; `pnpm exec eslint --max-warnings=0 .` rc=0 |
| Unit suites; domain suite < 10 s | 100%; < 10 s | **Pass (local)** | QA round 3: `pytest -q -m unit tests/unit` → 718 passed, 1 skipped in 6.58 s. EM: `vitest run` → 31 files, 251 passed |
| Integration and scenario | 100% | **Fail (known blockers)** | EM isolated run: `3 failed, 1060 passed, 6 skipped`. Failures: `test_nightly_run_completes` (no nightly run), `test_phone_fixtures` x2 (no real clips). Skips: 5 IT-00-10 strict (need Compose; QA round 2 on Compose → 37 passed incl. sandbox), 1 P3 (OQ-01) |
| Upload-validation and upload-resume regression suites | 100% | **Pass (isolated), flaky on shared services** | Isolated run: no failure in `test_upload_resume`, `test_it_01_09`, `test_upload_validation`. On the shared object store: `14 / 14 / 12 of 14` passed across 3 runs (QA-R3-02) |
| Rules engine and aggregate coverage | ≥ 95% line, ≥ 90% branch | **Pass (local)** | QA round 2: `--cov=racket.sports.pickleball --cov=racket.matches.domain --cov-branch` → 99% (365 stmts, 1 miss; 90 branches, 1 partial) |
| Property suite P1-P8 | ≥ 1,000 sequences per run, 0 failures | **Pass (local)**; P3 skipped (FR-043, OQ-01) | EM: `HYPOTHESIS_PROFILE=ci pytest -m "scoring and not nightly"` → 204 passed, 1 skipped in 33.18 s (`ci` profile `max_examples=1000`, `tests/conftest.py`) |
| BOLA inventory diff | empty | **Pass (local)** | `test_bola_matrix` and the route inventory green in the isolated run; no new ID route (IT-01-11) |
| `@needs-verification` listed separately | never counted toward a Must FR | **Pass** | EM: `pytest --co -m "scoring and needs_verification"` → 26 cases (21 at planning; PE-R1-03 added positions), all green, reported separately in §5 |
| Keyboard-only journeys, target size ≥ 24 px | 100%; 0 below 24 px | **Fail** | Keyboard-only: E2E-01-03 green. Target size: PD-R1-03 (axe `target-size` on the Q-03 error state) is unfixed; `.error-summary__list a` has no `min-block-size` at `cf8cd19`. PD rounds 2-3 measured Q-01, not Q-03. Q-07 Change links are 24 px against the 48 px flows spec (PD-R1-07, open) |
| axe-core | 0 serious or critical | **Pass (Chromium only)** | PD rounds 2-3: 0 violations at 320 and 360 px. WebKit not run since `2390e9a` |
| Secrets, audit, licence, SBOM | 0 / 0 / 0 | **Not evidenced this sprint** | They run in CI only; no CI run on the current head |
| Test and gold immutability | no unapproved test change | **Fail** | `grep -n Pending test-change-requests.md` → row 32 (committed in `c5b5367` before QA decided it; PE-R3-04) |
| PR size | ≈100 lines; > 400 needs an EM waiver before the commit | **Fail** | 82 commits, median 152.5 changed lines, 12 over 400 (max 2,111, `722f0c5`). 1 waiver recorded on time; 11 accepted late by the EM at close (decision-log) |
| Fresh-context review | no open Blocking; ≤ 3 iterations | **Fail → escalated** | 3 rounds. Open after round 3: 2 blockers (one CI item, reported twice) and 14 majors. Also open, with no disposition since round 1: 5 design blockers and 2 majors (§6) |
| Per sprint: nightly oracle 0 disagreements; mutation baseline | recorded | **Not met** | Oracle 0 disagreements locally (BE lane, 100,000 sequences); nightly never ran on GitHub; no mutation baseline |
| Per sprint: manual screen-reader pass (NFR-027b) | done | **Not done** | No record in the repo |
| Per sprint: flaky rate < 1% | < 1% | **Not measurable** | No CI history. Known flakes: the S-06 sign-in race (fixed in `71da707`), vitest 1 in 9 under load (PE-R3-09), shared-DB and shared-bucket interference (QA-R3-02, SEC-R3-S1-04) |

## 4. Definition of Done (sprint-01 §9 plus the sprint-level DoD)

| Item | Met? | Evidence |
|---|---|---|
| ST-013, ST-017, ST-018 carry threat-model notes and a security review with no open Blocking finding | **Partly** | `threat-model-sprint-01.md` (`cea394a`); 3 security rounds; no security blocker is open. **Majors are open**: SEC-R3-S1-01/02/03, and some controls are marked C without a test |
| No rule literal outside `RulesConfig` (IT-01-12); no I/O import (IT-01-13) | **Yes** | Both green in the isolated run |
| Test report shows provisional counts as `@needs-verification`, separate from Ready | **Partly** | This report §5 and `test-plan-status.md` do this. A signed Sprint 1 QA test report (as in Sprint 0) does not exist |
| SPIKE-06 ADR and the R-05 measurement note written | **Partly** | ADR 0028 (Proposed, no real-device data); `docs/data/phone-fixtures.md` holds the R-05 decision rule, but **no measurement** |
| Sprint 2 stories meet the DoR, incl. the approved `Match` aggregate design doc | **No** | The PE's Match aggregate design doc (rallies, corrections, score as projection) is not written (PE kickoff report); Sprint 2 DoR not checked |
| Retro 0 actions reviewed first in retro 1 | **Yes** | Retro §1 |
| Every story meets the story-level DoD | **No** | §2: 0 of 32 units |
| `status.json`, `progress.md` up to date | **Yes (at close)** | Refreshed 2026-10-05 (closes QA-R3-04); they were stale in every round (retro M2) |
| Delivery metrics recorded | **Partly** | Retro §2; DORA metrics are N/A (nothing deployed, no PRs) |
| Every significant decision has an ADR | **Yes** | ADRs 0023-0030. Small decisions in `decision-log.md` (80+ rows) |

## 5. Test counts by level

EM re-run, 2026-10-05, at `cf8cd19`. Backend on its own Postgres 16 and SeaweedFS (`RA_DEV_STATE` in the scratchpad, stopped afterwards), with the shared Mailpit (`MAILPIT_API_URL=http://127.0.0.1:8025`). Marker counts overlap (a regression test is also an integration test).

| Level | Count | Command → result |
|---|---|---|
| Backend, all | 1,069 collected | `cd backend && env -u APP_ENV uv run pytest -q -p no:cacheprovider -rfEs` → **3 failed, 1060 passed, 6 skipped in 139.76s** |
| Backend unit | 761 | `--co -m unit` → 761/1069 |
| Backend integration | 218 | `--co -m integration` → 218/1069 |
| Backend scenario (pytest-bdd) | 90 | `--co -m scenario` → 90/1069 |
| Backend mandatory regression | 39 | `--co -m regression` → 39/1069; all green |
| Scoring (Ready + provisional) | 206 | `--co -m scoring` → 206; `-m "scoring and not nightly"` (ci profile) → 204 passed, 1 skipped |
| of which `@needs-verification` | **26** | `--co -m "scoring and needs_verification"` → 26 (19 rows SOD-01..12, 16, F-01..06 plus the PE-R1-03 position cases). Never counted toward a Must FR |
| Nightly (100,000-sequence oracle) | 1 | `--co -m nightly` → 1; passed locally in 56.7 s (BE lane); not run on GitHub |
| Web unit (Vitest) | 251 | `cd web && pnpm exec vitest run` → 31 files, 251 passed |
| Infra | 245 | `cd infra && env -u S3_ENDPOINT_URL uv run pytest -q` → 245 passed in 50.23s |
| E2E Playwright Chromium | 51 | QA round 2 (fresh stack at `961648e`): 44 passed, 6 skipped, 0 failed. Round 3 (stack at `cf8cd19`): 34 passed, 11 failed, 6 skipped; all 11 are upload journeys failing on `No more free space left` in the object store, an environment fault. The EM did not re-run E2E |
| E2E WebKit | — | Not runnable in the sandbox (`/opt/pw-browsers` has Chromium only). Last CI result (`2390e9a`): 4 WebKit-only failures (S-09) |

Skips: 5 IT-00-10 strict tests need Compose (green on Compose in QA round 2); 1 P3 rally-scoring property is blocked on FR-043 / OQ-01. Six E2E rows skip on purpose, and each names its API-level binding.

## 6. Escalation to the human product owner (working-agreement §7.5 and §8)

The fix loop reached iteration 3. These findings stay open, and each has an owner and a proposed next step. Full rows are in `review-rounds.md` round 3.

| Finding | Severity | What is wrong | Owner | Proposed next step |
|---|---|---|---|---|
| PE-R3-05 / QA-R3-05 | blocker | No CI or nightly run since `2390e9a`; WebKit and the nightly oracle are unverified | **PO** (push and dispatch), sre-devops-engineer | PO pushes `sprint-01` at the sprint-close head, dispatches `ci.yml` then `nightly-quality.yml`; SRE records the run IDs. Decision D1 below |
| SEC-R3-S1-01 | major | Accounts are keyed by a 64-bit HMAC under `AUTH_EMAIL_KEY`; rotating the key orphans every account. Docs say the opposite | principal-engineer, security-privacy-engineer | ADR amendment before any non-dev deployment |
| SEC-R3-S1-02, SEC-R3-S1-03 | major | Session idle-timeout and 10-session cap have no killing test; T-ML-5, T-UV-9, T-UV-10 marked C without tests | senior-qa-engineer | Tests first; until then the threat-model rows go back from C |
| PE-R3-01, PE-R3-02 | major | 429 before 400 on malformed metadata; probe refusal deletes the object before the commit | senior-backend-engineer | Red-first fixes before any Sprint 2 upload story |
| PE-R3-03/PD-R3-02, PD-R3-01, PD-R3-03 | major | Wrong 429 copy; error summary does not refocus; 'trouble' state never shows | senior-frontend-engineer | Red-first fixes before any Sprint 2 FE story |
| PE-R3-04/QA-R3-01, QA-R3-02 | major | TCR row 32 Pending and disputed; whole-bucket diffs in tests | senior-qa-engineer | Reject 32(a), round the slice up; assert only own keys |
| QA-R3-03 | major | No smoke at the round-2 head; disk exhaustion | sre-devops-engineer | Prune, precheck the disk, re-run the smoke at the fixed head |
| PD-R1-01 | **blocker** (round 1, no disposition) | M-02 shows 'Video received' and 'Checking video…' together after an upload | senior-frontend-engineer | Red-first unit test, then drop `!!file` once the match is decided |
| PD-R1-02, PD-R1-04 (= PE-R1-04, QA-R1-04, S-09) | **blocker** (round 1) | WebKit: guide captions off and no fallback; no 'Your upload will stop' on sign-out | senior-frontend-engineer | Diagnose from the CI traces; needs a WebKit CI run (D1) |
| PD-R1-03, PD-R1-07 | **blocker** / major (round 1) | Error-summary links below 24 px on Q-03; Q-07 Change links 24 px against 48 px | senior-frontend-engineer | Target-size tokens on both; add the `wcag22aa` axe tag |
| PD-R1-05 | **blocker** (round 1) | Capture-guide wording still `draft`; ST-015 was merged without the coach sign-off | pickleball-domain-coach (via product-manager) | Sign off at the 2026-10-06 design review |

**Decisions needed from the PO** (options and recommendation; until answered, agents continue only on independent work):

| # | Question | Options | Recommendation |
|---|---|---|---|
| D1 | How will CI evidence reach GitHub each round? | (a) The PO pushes and dispatches by hand each round. (b) The PO allows the orchestrator to push `sprint-*` branches, with no force push, and the SRE adds `push: branches: [sprint-*]` to `ci.yml`. (c) Agents open PRs | **(b)**. Every story's DoD waits on CI. In two sprints the human-only path produced 1 run per sprint (judgment) |
| D2 | Accept the escalated majors as Sprint 2 carry-over, fixed before any new Sprint 2 story starts? | Accept / re-plan Sprint 2 | Accept, and size the carry-over into Sprint 2 capacity (about 10 units including deferred minors, judgment) |
| D3 | ASVS 6.3.3 residual risk of the single-factor magic link | Accept the risk in an ADR / pull passkeys into R1 | Accept for dev and internal use now; decide before any real-user beta (blockers.md row 1) |
| D4 | Inputs only the PO can give | OQ-01 rulebook PDFs (need-by 2026-11-16); ≥ 5 phone models of real clips for ST-025; real iOS Safari and Android Chrome runs for SPIKE-06; OQ-13 budget amount; OQ-20 recruitment; branch protection (`list_branches`: `main` `protected: false`) | Supply the phone clips and device runs first: they unblock 3 units (ST-025, SPIKE-06) and the R-05 caps |
| D5 | US + AU legal review scope (OQ-05, PO input 2026-10-05) | — | Recorded in ADR 0023 (note) and `open-questions.md`; review must cover US state privacy/biometric law and the AU Privacy Act 1988 / APPs before any real-user beta |

## 7. Carry-over to Sprint 2

| Item | Units (judgment) | Owner |
|---|---|---|
| ST-017 BE lane (TCR row 32, PE-R3-01) | 2 (already planned) | senior-backend-engineer, senior-qa-engineer |
| ST-022 mutation baseline and first nightly oracle run | 2 (already planned) | senior-qa-engineer, sre-devops-engineer |
| ST-025 real phone clips, R-05 measurement | 2 (already planned) | senior-ml-cv-engineer after the PO supplies clips |
| SPIKE-06 real-device runs | 1 (already planned) | senior-frontend-engineer with the PO or a tester |
| Open blockers and majors from rounds 1-3 (FE 7, BE 1 beyond ST-017, QA 3, PE 1, coach 1) | about 8 new | per §6 |
| Deferred minors and nits from rounds 1-3 (about 17) | about 2 | per `review-rounds.md` round 3 tables |
| External evidence: design review P7 (2026-10-06), coach wording sign-off, security and PE reviews, manual screen-reader pass, Sprint 1 QA test report | — | principal-designer, pickleball-domain-coach, security-privacy-engineer, principal-engineer, senior-qa-engineer |
| Match aggregate design doc (Sprint 2 DoR) | — | principal-engineer |
| Sprint 0 carry-over still open: ST-002 GitHub evidence (branch protection, labels, secret, nightly streak); ST-010 WebKit; SPIKE-01 reviews | — | PO with sre-devops-engineer; senior-frontend-engineer; principal-engineer and security-privacy-engineer |

## 8. Demo outcome (sprint-01 §12)

The review is on 2026-10-30, so this is a dry-run against the demo script, based on the evidence above.

| Step | Can it be shown today? | Evidence or gap |
|---|---|---|
| 1. Request a link, open it from Mailpit, clean address bar | **Yes (desktop Chromium)** | IT-01-01; `sign-in.spec.ts` green; the token is removed by `replaceState` (security round 2). Not shown on a phone browser |
| 2. First-run screen and capture guide, video muted | **Yes (Chromium)** | `first-run-and-guide.spec.ts` 5 passed. WebKit captions fail (PD-R1-02, last CI) |
| 3. Doubles setup with error summary, disabled rally scoring, Check your answers | **Yes** | `match-setup.spec.ts` 13 passed |
| 4. ~3 GB upload, airplane mode at 40%, close tab, resume | **Partly** | E2E-01-02 runs at reduced scale (48 MiB, 10 s offline). SPIKE-06 proxy: 1 GiB in 25.6 s, resumed after a closed tab. No ~3 GB phone fixture and no phone |
| 5. PDF renamed `match.mp4`; 4-hour file | **Yes** | `upload-validation.spec.ts` green after freeing disk; real 4-hour fixture `fixtures/clips/long-4h` |
| 6. `pytest -m scoring` live, provisional rows reported separately | **Yes** | 204 passed, 1 skipped; 26 `@needs-verification` cases listed separately |
| 7. Nightly oracle result and mutation baseline | **No** | Nightly never ran on GitHub; no mutation baseline. Only the local 100,000-sequence run can be shown |
| 8. Sign out, offline, reopen: nothing left | **Yes (Chromium)** | `sign-out.spec.ts` 3 passed |
| 9. SPIKE-06 and SPIKE-01 results; ask OQ-12 and OQ-18 | **Partly** | ADR 0028 has proxy data only; OQ-12 answered (ADR 0015 Accepted); OQ-18 needs real-device data |

## 9. Delivery metrics

See the retro, §2. Summary: 82 commits on `sprint-01` (`c32b878^..HEAD`): 18 feat, 25 test, 13 fix, 23 docs, 2 ci, 1 style. Median 152.5 changed lines per commit (Sprint 0: about 15,000). 12 commits were over 400 lines. 18 commits came after the smoke (review-fix work). DORA metrics are N/A: nothing was deployed and no PRs were opened.
