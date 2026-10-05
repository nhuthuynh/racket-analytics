# Sprint 1 report: Sign in, set up a match, upload safely; the scoring engine, test-first

- **Prepared by:** engineering-manager, 2026-10-05 (final close, after goal verification round 3), for the sprint review with the human product owner (PO) planned for 2026-10-30.
- **Head:** `6f6e44e` on `sprint-01`, plus this close commit (docs only). The tree under goal test was `e76fb96`. Since then only docs have changed (`git diff --stat e76fb96 6f6e44e -- backend web infra scripts` → empty).
- **Timing caveat:** the sprint was planned for 2026-10-19 to 2026-10-30. All the build work, the integration smoke, 3 sprint-close review rounds and 3 goal verification rounds ran in one compressed agent session on 2026-10-05. Calendar metrics (lead time, time-to-merge, nightly streaks) cannot be measured.
- **Inputs:** [`goal-scorecard.md`](goal-scorecard.md) §8 (verification round 3), [`review-rounds.md`](review-rounds.md), [`smoke.md`](smoke.md) §6, [`blockers.md`](blockers.md), [`decision-log.md`](decision-log.md), [`status.json`](status.json), GitHub (`list_workflow_runs`, `list_branches`), and the EM's own runs (§6).
- **Retro:** [`docs/retros/2026-10-30-sprint-01.md`](../../retros/2026-10-30-sprint-01.md). **Process ADRs from the retro:** [0030](../../decisions/0030-finding-disposition-isolated-evidence-and-pre-sliced-stories.md), [0033](../../decisions/0033-reviewer-written-finding-rows-dry-run-methods-and-self-cleaning-evidence.md).

## 1. Goal and scorecard result

> **The Sprint 1 goal is NOT met, so Sprint 1 is not done** (PO standing rule). The independent verifiers (round 3, head `e76fb96`, isolated Compose project `racket-gv3`) measured **10 of 12 metrics met**. Two are "no": **G01-05**, because the evidence ran below the disk floor, and **G01-11**, open defects.
>
> At this close the EM found that **G01-11 was undercounted**. Sprint-close review round 3 raised 16 new findings that never got a row in `review-rounds.md`, so the counter could not see them. With those rows written, `open_defects.py` gives **17 open blocker/major findings, not 11** (§1.2).

Every part of the goal *works* live over https on a fresh stack: sign-in, setup, a multi-GB resumable upload with refusals, and the scoring engine. What blocks the close is the defects and the external evidence, not the journey.

### 1.1 Metrics: target against actual (verification round 3, `goal-scorecard.md` §8)

| ID | Measure | Target | Actual | Met |
|---|---|---|---|---|
| G01-01 | Live goal journey over https, fresh account per run | 5 of 5 runs pass | 5/5, rc=0, every step ok (resume from offset 689684 after a 40% drop, damaged chunk 460, 12 GB 413, PDF 415, 401 after sign-out) | yes |
| G01-02 | IT-01-01..13 plus regression suites, real services | 100%, 13/13 ids, 0 skipped; regression 100% | 69/69, `missing []`; regression 41/41; strict sandbox 10 passed on Compose | yes |
| G01-03 | Playwright Chromium, all specs, then a flake check | 100% of non-skipped, ≤ 6 named skips, 0 flaky ×3 | 52 passed, 6 skipped, 0 failed; ×3: 135 passed, 0 flaky. Chromium only; the repeat covers `e2e/sprint-01` only (QA-R3-E2E-01) | yes |
| G01-04 | API read latency at 50 RPS for 60 s | p95 ≤ 300 ms, p99 ≤ 800 ms, ≥ 99.5%, ≥ 47.5 RPS, 0 unexpected 4xx | p95 12.79 ms, p99 49.52 ms, 100%, 50.01 RPS, 0 unexpected | yes |
| G01-05 | Upload throughput, ≥ 1 GB 1080p60 file over https | ≥ 50 Mbit/s, offset = length, run above the 10 GB disk floor | 541.8 Mbit/s, offset = size, rc=0, but `disk_free_gb_end 9`: invalid evidence | **no** |
| G01-06 | Real-time goal steps (p95 over the 5 G01-01 runs) | (a) sign-in ≤ 10 s; (b) final byte to facts ≤ 30 s | (a) 1.058 s; (b) 0.879 s | yes |
| G01-07 | Scoring correctness | 100% (P3 skip only); ≥ 19 `@needs-verification` cases all pass; ≤ 90 s | 204/205 (P3 skip, FR-043); 26/26 provisional cases, listed separately; 32.5 s | yes |
| G01-08 | Differential oracle; mutation baseline | 100,000 sequences, 0 disagreements; baseline recorded | 0 disagreements; mutation 0.8654 (373/431), cold | yes |
| G01-09 | Coverage | Backend changed lines ≥ 85%; rules and aggregates ≥ 95% line and ≥ 90% branch; web ≥ 80% | 95%; 99.4% line, 98.7% branch; web 90.22% | yes |
| G01-10 | Accessibility on Sprint 1 screens | 0 serious/critical axe; every screen family; 0 targets < 24×24; E2E-01-03 passes | 19 axe checks, 0 violations, families A F/G Q U M, 0 small targets, E2E-01-03 passed (Chromium) | yes |
| G01-11 | Open blocker/major defects | 0 | Verifier: 11 (rc=1); GitHub open bug issues 0. **EM recount at this close: 17** (§1.2) | **no** |
| G01-12 | Fast tests | Domain < 10 s; backend unit ≤ 60 s; 0 failed | 7.4 s; 8.3 s; 0 failed. EM re-run: `763 passed, 1 skipped in 7.19s` | yes |
| DEMO | Sprint-01 §12 demo, end to end in real time | All steps | Steps 1-6 and 8 passed live (Pixel 7 Chromium, 1.05 GB file, a real 120 s offline, closed-tab resume to "Video received"). Step 7: no *nightly* result (local oracle and mutation only). Step 9 is for the PO | partly |

**Why G01-05 is "no":** the throughput is 10 times the target. But both runs ended at 9 GB free, under the 10 GB floor (`docs/ops/disk-and-prune.md`), so the evidence is invalid. Removing the stale images of earlier rounds needs human approval (the session's permission policy denied it). This is a host-capacity problem, not a product defect. ADR 0033 rule 3 stops the pile-up from recurring. The PO approves the image removal (item P5), then any verifier reruns §4 G01-05 with ≥ 12 GB free.

### 1.2 Open blocker and major findings at close (G01-11)

`python3 scripts/measure/open_defects.py docs/sprints/01/review-rounds.md` → rc=1, **open 17**. Aliases are counted once.

| # | Finding (family) | Sev. | What is open | Who can close it |
|---|---|---|---|---|
| 1 | PE-R3-05 family (QA-R1-06, PE-R2-02, QA-R2-02, QA-R3-05, QA-R2V-01) | blocker | No green CI run on a head with the Sprint 1 fixes. CI run 37372059078 (`ci.yml`, head `e76fb96`) is still `queued`. `main` is unprotected | PO P1 (partly done: pushed at `e76fb96`, `ci.yml` dispatched); SRE records the run |
| 2 | DEMO-07 | blocker | No nightly result for demo step 7. `nightly-quality.yml` cannot be dispatched until it exists on `main` (dispatch → 404) | PO P1 (merge or add the workflow to `main`) |
| 3 | S-08 / QA-R2V-08 | major | `test_nightly_run_completes` correctly red: no nightly run | as #2 |
| 4 | WebKit family (PD-R1-02, PD-R1-04, PE-R1-04, QA-R1-04, S-09, QA-R2V-06, PD-R2R-01) | blocker | Guide captions and fallback, and the sign-out "Your upload will stop" dialog, are unverified on WebKit (release-blocking, OQ-17) | senior-frontend-engineer after the WebKit job of run 37372059078 |
| 5 | S-07 / QA-R2V-07 | blocker | ST-025 has no real phone recordings; 2 scenarios red on purpose | PO P3 (clips, or approve the carry-over) |
| 6 | SEC-R4-S1-04 / BLK-ASVS-6.3.3 | major | Single-factor sign-in, residual risk at ASVS L2 6.3.3 (ADR 0031 Proposed) | PO P2. Blocks a real-user beta, not dev use |
| 7 | QA-R2V-11 | major | The ADR 0031 half (the ADR 0032 half is done, `3194096`) | PO P2 |
| 8 | SEC-R3-S1-01 / SEC-R4-S1-01 | major | Account identity is still the 64-bit `email_key`; fix is ST-013b (ADR 0032 Accepted). Gate before any non-dev deployment | senior-backend-engineer in Sprint 2; PO P4 approves the carry-over |
| 9 | PD-R2R-03 | major | The G-01 consent and minors line has not shipped. Security accepted the wording in review round 3 | senior-frontend-engineer, test-first |
| 10 | PD-R1-06 / PD-R2R-02 / QA-R2V-12 | major | The DoR P7 flows design review has not been held. Decisions due 2026-10-06, otherwise DR-01 in Sprint 2 | principal-designer (chair) with the participants |
| 11 | QA-R2V-03 | blocker | The meta-finding "G01-11 not met"; closes when 1-10 and 12-17 close | engineering-manager |
| 12 | **SEC-R6-S1-01** (new, round 3) | blocker | A NUL character in the e-mail address (unauthenticated) or in the match title gives a 500. Still reproduces: `normalise_email('a\x00b@example.com')` returns the address | senior-backend-engineer (sprint-02 C-01) |
| 13 | **PE-R3R-01** (new) | major | Parallel upload creations get past the open-upload quota (8 × 201 against a cap of 3) | senior-backend-engineer (C-02) |
| 14 | **PD-R3V-01** (new) | major | After a server error the upload panel offers no recovery | senior-frontend-engineer (C-03) |
| 15 | **QA-R3-E2E-01 / PD-R3V-02** (new) | major | `walking-skeleton.spec.ts` has a timing-window flake | senior-qa-engineer (C-04) |
| 16 | **QA-R3-E2E-02** (new) | major | Playwright evidence is not isolated between concurrent agents | sre-devops-engineer (C-05) |
| 17 | **QA-R3-GATE-01** (new) | major | Manual screen-reader pass (NFR-027b) not done and had no disposition | senior-qa-engineer with a human tester (C-06); PO P4 |

Rows 12-17 had no `review-rounds.md` row until this close (retro M10; ADR 0033 rule 1). Row 12 is a real product defect found by security review that **every goal metric missed**, because no method sends control characters.

## 2. The four goal bullets

| Bullet | Works live? | Evidence | Still open |
|---|---|---|---|
| 1. Magic-link sign-in; sign-out leaves nothing | **Yes (Chromium)** | G01-01 steps 1-2 and 9; `sign-in.spec.ts`, `sign-out.spec.ts` green; demo steps 1 and 8 | WebKit (#4); ASVS 6.3.3 (#6); identity key (#8); NUL address 500 (#12) |
| 2. Capture guide; doubles/singles setup, one question per page, error summary | **Yes (Chromium)** | G01-03 `match-setup.spec.ts` incl. E2E-01-03; G01-10 0 violations; demo steps 2-3 | Consent line (#9); design review (#10); NUL title 500 (#12) |
| 3. Multi-GB upload survives a drop and a closed tab; bad files refused with a reason | **Yes** | G01-01 (40% drop, resume, 460, 413, 415); demo step 4 with 1.05 GB (goal round 2: 2.98 GB); G01-05 541.8 Mbit/s (invalid only for disk) | Quota race (#13); server-error recovery (#14); real phones (SPIKE-06, ST-025) |
| 4. Pure, configurable scoring engine, test-first; provisional tables `@needs-verification`; property suite and oracle green | **Yes** | G01-07 204/205 + 26/26 provisional; G01-08 oracle 0/100,000, mutation 0.8654; G01-09 99.4%/98.7% | Rulebook PDFs (OQ-01); nightly run on GitHub (#2) |

## 3. Committed vs done per story

Units come from ADR 0010. **Implemented** = committed, reviewed, and the lane's own tests green in an isolated run (the `status.json` `counting_rule`). **DoD-done** additionally needs a green `ci-gate` run whose head includes the story's commits, plus all external evidence closed.

| Story | Units | Implemented | DoD-done | Open (owner) |
|---|---|---|---|---|
| ST-013 Magic-link sign-in | 3 | 3 | 0 | #1, #4, #6, #8, #12 (BE), design review |
| ST-014 Sign-out clears the device | 1 | 1 | 0 | #1, #4 |
| ST-015 First run and capture guide | 2 | 2 | 0 | #1, #4, #9, #10. Coach sign-off done (decision-log, pickleball-domain-coach row) |
| ST-016 Match setup | 5 | 5 | 0 | #1, #10, #12 (title) |
| ST-017 Resumable upload | 4 | 4 | 0 | #1, #4, #13, #14, #15 |
| ST-018 Upload validation | 3 | 3 | 0 | #1; caps provisional until ST-025 |
| ST-020 Scoring engine core (a) | 4 | 4 | 0 | #1; presets PROVISIONAL-UNVERIFIED (OQ-01) |
| ST-021 Match structure (a) | 1 | 1 | 0 | #1 |
| ST-022 Property suite, oracle, mutation baseline | 2 | 2 | 0 | #1, #2 (first nightly oracle on GitHub) |
| ST-023 Golden tables | 2 | 2 | 0 | #1; coach review; rule numbers (OQ-01) |
| ST-024 Nightly jobs and SLIs | 2 | 2 | 0 | #1, #2, #3 |
| ST-025 Phone fixtures and R-05 | 2 | 0 | 0 | **Blocked** on #5 |
| SPIKE-06 Phone-browser upload | 1 | 0 | 0 | **Partial**: real iOS Safari and Android Chrome runs |
| **Committed total** | **32** | **29** (BE 12, FE 11, QA 4, SRE 2, ML 0) | **0** | |
| ST-019 Footage quality report (stretch) | 1 | 1 | 0 | #1, design review |

**Ratio:** 29/32 = 0.906 implemented, 0.00 DoD-done. Sprint 0: 19/28 = 0.68 and 0.00. Every story waits on the same thing: a green CI run (#1). The 3 missing units are all external inputs: phone clips (2) and real devices (1).

## 4. Quality gates (sprint-00 §8 per-PR gates plus sprint-01 §8)

"Local" means isolated runs in this sandbox on real services. "CI" means GitHub Actions.

| Gate | Threshold | Status | Evidence |
|---|---|---|---|
| Lint and types (ruff, mypy, ESLint, tsc) | 0 errors | Pass (local) | Smoke §6: `tsc --noEmit` rc=0, `eslint .` rc=0; ruff clean on the harness (scorecard commit) |
| Domain unit suite time | < 10 s | **Pass** | G01-12: 7.4 s; EM: `pytest -q -m unit` → `763 passed, 1 skipped in 7.19s` |
| Rules engine and aggregate coverage | ≥ 95% line, ≥ 90% branch | **Pass** | G01-09: 99.4% line, 98.7% branch |
| Property suite P1-P8 | ≥ 1,000 sequences, 0 failures | **Pass**; P3 skipped (FR-043, OQ-01) | G01-07 |
| Upload-validation and upload-resume regression | 100% | **Pass** | G01-02: 41/41 |
| BOLA inventory diff | empty | **Pass** | G01-02 requires `test_bola_matrix` → present and passed |
| `@needs-verification` listed separately | never counted toward a Must FR | **Pass** | G01-07: 26 cases in their own report |
| Keyboard-only journeys and target size | 100%; 0 below 24×24 | **Pass (Chromium)** | G01-10: E2E-01-03 passed, 0 small targets; PD-R1-03/07 fixed in `6dde8b5` |
| axe-core | 0 serious/critical | **Pass (Chromium)** | G01-10: 19 checks, 0 violations |
| Secrets, audit, licence, SBOM | 0 / 0 / 0 | **Not evidenced** | Only in CI. Run 37372059078 is queued |
| Test and gold immutability | no unapproved change | **Pass** | `grep -c Pending docs/sprints/01/test-change-requests.md` → 0 |
| PR / commit size | ≈ 100 lines; > 400 needs a waiver before the commit | **Fail (late waivers)** | 139 commits, median 94 changed lines, 13 over 400. 2 waivers were given on time (`8c4c7fa` and one earlier); 11 were accepted late (decision-log) |
| Fresh-context review | no open Blocking; ≤ 3 iterations | **Fail → escalated** | 3 sprint-close review rounds and 3 goal rounds; 17 blocker/major findings open (§1.2) |
| Nightly oracle; mutation baseline | 0 disagreements; recorded | **Partly** | Local: 0/100,000 and 0.8654. No nightly run on GitHub (#2) |
| Manual screen-reader pass (NFR-027b) | done | **Not done** | QA-R3-GATE-01 (#17) |
| Flaky rate (NFR-074) | < 1% | **Pass locally, with a known gap** | G01-03 0 flaky ×3 on `e2e/sprint-01`. Root specs are never repeated; one timing flake is known (#15). No CI history |
| Smoke before review (ADR 0022) | at the review head | **Partly** | `smoke.md` §6 at `8e58d4d`. The later heads were exercised by goal rounds 1-3, but `smoke.md` has no entry for them (QA-R3-SMOKE-01, C-12) |

## 5. Definition of Done (sprint-01 §9 plus sprint level)

| Item | Met? | Evidence |
|---|---|---|
| ST-013, ST-017, ST-018: threat-model notes and a security review with no open Blocking | **No** | SEC-R6-S1-01 (blocker, ST-013 address path) and PE-R3R-01 (ST-017 quota race) are open |
| No rule literal outside `RulesConfig` (IT-01-12); no I/O import (IT-01-13) | **Yes** | G01-02 includes `test_rules_static` → passed |
| Provisional counts shown as `@needs-verification`, separate from Ready | **Yes** | G01-07; §6 |
| SPIKE-06 ADR and R-05 measurement note | **Partly** | ADR 0028 Proposed (proxy data only); `docs/data/phone-fixtures.md` has the rule but no measurement |
| Sprint 2 stories meet the DoR, including the approved Match aggregate design doc | **Partly** | `docs/architecture/match-aggregate.md` written (`869b1d9`), status Proposed: its PR review needs GitHub. DR-01 is open |
| Retro 0 actions reviewed first in retro 1 | **Yes** | Retro §1 |
| Every story meets story-level DoD | **No** | 0 of 32 units (§3) |
| Sprint goal demonstrated live, every metric met (PO standing rule) | **No** | 10 of 12 (§1) |
| `status.json` and `progress.md` current | **Yes** | Refreshed in this close commit from `6f6e44e` |
| Delivery metrics recorded | **Yes (proxies)** | Retro §2 |
| Every significant decision has an ADR | **Yes** | ADRs 0023-0033. Small decisions are in `decision-log.md` |

## 6. Test counts by level

The EM ran these at `6f6e44e` on 2026-10-05; the verifier's round-3 results come from `e76fb96` (same code). Marker counts overlap: a regression test is also an integration test.

| Level | Count | Command → result |
|---|---|---|
| Backend, all | 1,084 collected | `cd backend && env -u APP_ENV uv run pytest --co -q` → `1084 tests collected`. QA review round 3, isolated, at `fb9e7d6` (same backend code): `3 failed, 1080 passed, 1 skipped`. The 3 failures are the PO-blocked S-07 ×2 and S-08 |
| Backend unit | 764 | `--co -m unit` → 764/1084. EM run: `763 passed, 1 skipped in 7.19s` |
| Backend integration | 230 | `--co -m integration` → 230/1084. G01-02: `223 passed, 2 skipped` (2 Sprint 0 strict-sandbox cases need Compose) plus 10 strict-sandbox cases on Compose |
| Backend scenario (pytest-bdd) | 90 | `--co -m scenario` → 90/1084 |
| Mandatory regression | 39 | `--co -m regression` → 39/1084; G01-02 regression rate 41/41 (with the BOLA and rules-static selection) |
| Scoring (Ready plus provisional) | 206 | `--co -m scoring` → 206; G01-07 `204 passed, 1 skipped in 31.50s` |
| of which `@needs-verification` | **26** | `--co -m "scoring and needs_verification"` → 26; all passed and reported separately (SOD-01..12, SOD-16, F-01..06 and position cases). Never counted toward a Must FR |
| Nightly (100,000-sequence oracle) | 1 | `--co -m nightly` → 1; G01-08 local run 0 disagreements in 57 s |
| Coverage run | — | G01-09: `1067 passed, 1 skipped, 4 deselected` (nightly and the 3 PO-blocked tests by node id, decision-log QA-R2V-04) |
| Web unit (Vitest) | 269 | `cd web && pnpm exec vitest run` → `31 passed` files, `269 passed` |
| Infra | 305 | `cd infra && uv run pytest -q -p no:cacheprovider` → `305 passed in 57.73s` |
| E2E Playwright Chromium | 58 | G01-03: `52 passed, 6 skipped`, 0 failed; `--repeat-each=3` on `e2e/sprint-01` → `135 passed, 18 skipped`, 0 flaky |
| E2E WebKit | — | Not runnable here (`/opt/pw-browsers` has Chromium only). CI run 37372059078 queued at close |

The 6 E2E skips are named, and each names its API-level binding. The backend has 1 skip: P3 rally scoring (FR-043, OQ-01).

## 7. Decisions and inputs needed from the PO

Until these are answered, agents work only on independent items (working-agreement §8). The list is the same as the blockers.md EM row (items P1-P4), with P5 added at this close.

| # | Ask | Options | EM recommendation |
|---|---|---|---|
| P1 | CI evidence | Push and dispatch have been done once (`e76fb96`, run 37372059078 queued). Remaining: (a) put `nightly-quality.yml` on `main` so it can be dispatched; (b) turn on branch protection for `main`; (c) decide D1 for future rounds | (a) and (b) now. D1 option (b): the orchestrator pushes `sprint-*` without force, and CI runs on `push: sprint-*` |
| P2 | ASVS 6.3.3 residual risk (ADR 0031) | Accept for R1 / passkeys in R1 | Accept for dev and internal use now; passkeys before any real-user beta (security and PM positions in ADR 0031) |
| P3 | Real phone recordings for ST-025 | Supply ≥ 5 models incl. VFR / carry ST-025 to Sprint 2 | Approve the carry-over now and supply the clips by Sprint 2 planning (2026-11-02) |
| P4 | Carry-over of the open majors and blockers (§1.2 rows 8-17) to Sprint 2, fixed before new stories | Accept / re-plan Sprint 2 | Accept: sprint-02 rows C-01..C-06 first, then ST-013b, ST-042, DR-01. About 12 units (§8) |
| P5 | Disk for G01-05 | Approve removing the stale `racket-*` images of finished rounds, or add disk | Approve the removal; a verifier reruns G01-05 at ≥ 12 GB free |
| — | Standing inputs | OQ-01 rulebook PDFs (need-by 2026-11-16); OQ-05 legal review for US and AU before any real-user beta; OQ-13 budget; OQ-20 recruitment; a VoiceOver/TalkBack tester for C-06 | — |

## 8. Carry-over to Sprint 2

| Item | Units (judgment) | Owner | Where |
|---|---|---|---|
| Open blockers/majors C-01..C-06 (NUL 500, quota race, upload recovery, E2E flake, evidence isolation, screen-reader pass) | ~6 | BE, FE, QA, SRE, PO | `sprint-02.md` §3 EM carry-over |
| Deferred minors and nits C-07..C-38 | ~6 | per row | same |
| ST-013b account identity (gate before non-dev deployment) | 1 | senior-backend-engineer | `sprint-02.md` §3 |
| ST-042 least-privilege worker credentials (gate) | 2 | BE + SRE | `sprint-02.md` §3 |
| ST-025 remaining part (after the PO's clips) | 1 | senior-ml-cv-engineer | `sprint-02.md` §3 |
| DR-01 flows design review (if not held by 2026-10-06) | 0.5 | principal-designer | `sprint-02.md` §3 |
| PD-R2R-03 consent line on G-01 | 0.5 | senior-frontend-engineer | ST-015 reopen |
| WebKit family: triage from the CI traces of run 37372059078 | ~1 | senior-frontend-engineer | after P1 |
| SPIKE-06 real-device runs; ADR 0028 decision | 1 | senior-frontend-engineer with the PO or a tester | — |
| Match aggregate design-doc PR review (Sprint 2 DoR) | — | principal-engineer | after P1 |
| G01-05 rerun at ≥ 12 GB free | — | sre-devops-engineer after P5 | C-15 |

The Sprint 0 carry-over is unchanged except where noted: ST-002 GitHub evidence is now pushed and dispatched once, but has no green run and no branch protection; ST-010 WebKit is unverified.

## 9. Demo outcome (sprint-01 §12, run live by the round-3 verifiers)

| Step | Shown? | Evidence |
|---|---|---|
| 1. Request a link, open it from Mailpit, clean address bar | **Yes** | Signed in in 1.55 s, no token in the URL |
| 2. First run and capture guide, video muted | **Yes** | 6 checklist items; no autoplay; "unofficial" shown |
| 3. Doubles setup, error summary, rally scoring disabled, Check your answers | **Yes** | Error summary and page title `Error: …`; `aria-disabled` rally scoring |
| 4. Large upload, offline at 40%, close the tab, resume | **Yes** | 1.05 GB here, 120 s offline, resumed at 60% after closing the tab, "Video received" (goal round 2: 2.98 GB) |
| 5. PDF renamed `.mp4`; 4-hour file | **Yes** | Both refused with their copy |
| 6. `pytest -m scoring` live, provisional rows separate | **Yes** | 204 passed, 26 provisional |
| 7. Nightly oracle result and mutation baseline | **Partly** | Local oracle and mutation only; no nightly run (#2) |
| 8. Sign out, offline reopen, nothing left | **Yes** | No participant names or match data visible |
| 9. SPIKE-06/SPIKE-01 results; ask OQ-12, OQ-18 | **PO at the review** | — |

## 10. Delivery metrics (summary; detail in the retro §2)

139 commits on `sprint-01` (`c32b878^..HEAD`): 18 feat, 32 test, 26 fix, 60 docs, 2 ci, 1 style. Median 94 changed lines per commit (Sprint 0: about 15,000); 13 over 400. 49 commits came after the smoke at `488d574`: 12 fix, 7 test, 30 docs. DORA metrics are N/A: nothing was deployed and no PRs were opened. CI ran 3 times in total, and only once on a head with the Sprint 1 fixes (still queued).

## 11. History of this report's verdict

- 2026-10-05, first close at `9195ea9`: "goal partly met", 25/32. This was written before any goal measurement and was superseded (PE-R1-S1-02, QA-V1-04).
- 2026-10-05, sprint-close review rounds 1-2: dated notes added (not demonstrated; 29/32 after the round-1 fixes).
- 2026-10-05, goal rounds 1-3: 11/12, 11/12 and 10/12 met; G01-11 "no" in every round.
- 2026-10-05, this rewrite (PE-R3R-04, QA-R3-DOC-01): the verdict is taken from the round-3 scorecard, and the open count is corrected from 11 to 17.
