# Sprint 2: Quick Tag to score sheet (spec M0 "Done when", labelled unofficial)

- **Dates:** Mon 2026-11-02 → Fri 2026-11-13
- **Planning:** 2026-11-02 · **Sprint review:** 2026-11-13 · **Retrospective:** 2026-11-13
- **Retro file:** `docs/retros/2026-11-13-sprint-02.md` from [`docs/retros/TEMPLATE.md`](../retros/TEMPLATE.md). Format: **Mad/Sad/Glad**. Focus area: **domain correctness and the coach's verification flow** [EP/ENG-15].
- **Status:** Planned; refined at Sprint 2 planning on **2026-10-05** by the engineering-manager with the product-manager, principal-engineer, business-analyst and senior-qa-engineer (§0). Like Sprint 1, the work runs in a compressed session before the planned dates; the planned dates are kept for the review and the retro. Branch `sprint-02`, based on `sprint-01` at `2b97fa0`. **Preconditions** (status in §0.1):
  - the `Match` aggregate design doc (principal-engineer, Sprint 1) is approved [DPA/DESIGN-15];
  - the Quick Tag flow, keyboard map and score-sheet states (principal-designer) are done;
  - ADR 0009 is ratified (otherwise ST-029, ST-032, ST-034 and ST-035 drop to their mechanics only, see §3.1).
- **Goal scorecard (PO standing rule):** [`docs/sprints/02/goal-scorecard.md`](02/goal-scorecard.md), 12 metrics G02-01..G02-12, each measured on the live local stack.
- **Progress and status:** `docs/sprints/02/progress.md`, `docs/sprints/02/status.json`. Decisions: `docs/sprints/02/decision-log.md`. Blockers and the PO list: `docs/sprints/02/blockers.md`. Findings: `docs/sprints/02/review-rounds.md`.
- **Related ADRs:** 0002, 0003 (rallies-lost unit, for the data captured here), 0007, 0009, 0010, 0022, 0023, 0029, 0030, 0032, 0033. Citation prefixes: working-agreement §0.

## 0. Planning record (2026-10-05)

### 0.1 Preconditions

| Precondition | Status at planning | Consequence |
|---|---|---|
| ADR 0009 ratified | **Met** (ADR 0023, 2026-10-05) | The rules stories run under the (a)/(b) split. The rulebook PDFs are not supplied yet (OQ-01, PO input 2026-10-05), so the only preset stays `PROVISIONAL-UNVERIFIED`, provisional rows stay `@needs-verification`, and every score sheet says "unofficial" |
| `Match` aggregate design doc approved | **Not met:** `docs/architecture/match-aggregate.md` is **Proposed** | Design review on D1 (principal-engineer chairs; senior-backend-engineer, senior-qa-engineer, pickleball-domain-coach, security-privacy-engineer). ST-026..ST-032 code starts only after it is approved. The carry-over fixes (§3, rows C-01..C-06) and ST-041 run first |
| API contract for Sprint 2 | **Not met:** no `docs/architecture/api-sprint-02.md` | principal-engineer, D2. Until then the harness assumptions live in `scripts/measure/tagcontract.py` (decision-log 2026-10-05) |
| Quick Tag, key map and score-sheet flows with all states | **Not met:** only `docs/design/flows-sprint-01.md` exists; its DoR P7 review is not held (DR-01) | principal-designer: DR-01 on D1 (hard date 2026-11-02), then `docs/design/flows-sprint-02.md` on D2. No Sprint 2 UI story starts before both |
| Sprint 1 DoD met, or carry-over re-sized | **Not met:** Sprint 1 closed "goal not met" (10 of 12; 17 open blocker/major) | Carry-over sized here (§2, §3) and approved by the PO (P4) |

These are recorded as an Open row in `docs/sprints/02/blockers.md`. The stories in §3 are **Ready on condition** (§14.2): each condition has an owner and a day.

### 0.2 Product-owner decisions applied (ADR 0023; `docs/requirements/po-input-2026-10-05.md`)

- **Accept all recommendations.** Nothing in this plan departs from an accepted OQ recommendation.
- **Jurisdictions US and AU (OQ-05).** No real-user beta in Sprint 2, so no story changes. The legal review (NFR-070) must cover both; ST-040's capture protocol and consent form say so.
- **https for the dev stack, no insecure-cookie flag (ADR 0029).** Every live goal method runs over https through `web-tls` (scorecard §4.0). No story may add an insecure-cookie switch.
- **Rulebook PDFs later (OQ-01).** Scoring stays `PROVISIONAL-UNVERIFIED`; rule-dependent scenarios keep `@needs-verification`; the score sheet says "unofficial scoring (rules not yet verified)" (FR-055). Need-by for official scoring in R1: Sprint 3 planning, 2026-11-16 (P7).

### 0.3 Retro 1 actions applied (`docs/retros/2026-10-30-sprint-01.md` §9)

| Action | How this plan applies it |
|---|---|
| A1 CI, nightly, branch protection | Row W-01 (SRE, committed): triage CI run 37377206126 to owners, WebKit first; the PO list item P1 (labels, protection, merge to `main` so the nightly can run) |
| A2 C-01, C-02, C-03 red-first before any new story | They are the first items of their lanes (§3.2 order). No ST-026..ST-037 code is committed before C-01 and C-02 are "Fixed" in `review-rounds.md` |
| A3 ADR 0033 rule 3 (self-cleaning evidence) | Rows C-05, C-15, C-23 (SRE, committed); the scorecard §4.0 tears down with `down -v --rmi local`, uses `--output` and the E2E lock |
| A4 testing-strategy rule L11 (fuzz every JSON string field, a concurrency case for every limit) | Row QA-FUZZ (QA, committed): the rule text plus IT-02-10 (fuzz) and IT-02-11 (quota concurrency); C-04 and C-06 |
| A5 ADR 0033 rules 1, 2, 4 | The 17 open Sprint 1 families are carried as Open rows into `docs/sprints/02/review-rounds.md` on day 1; every scorecard method has a dry-run row (scorecard §6); the PO list (P1-P9, dated) is sent on day 1 (blockers.md) |

### 0.4 What changed from the outline

- **Capacity:** the outline committed BE 12.5 and FE 12.5 before any carry-over existed. With the carry-over first, ST-034, ST-035, ST-038 and ST-028b move to stretch, and ST-042 moves to Sprint 3 (decision-log 2026-10-05; PO item P4).
- **Goal:** "A match that starts mid-game, and singles matches, are scored too" leaves the committed goal (stretch). A fifth goal bullet makes the carry-over part of the goal: the Sprint 1 blockers and majors are fixed first and none is open at the close.
- **New rows:** ST-028a/b split, W-01, QA-ACC, QA-FUZZ, SRE-MEDIA and SRE-SMOKE (§3); IT-02-10..IT-02-12 and E2E-02-06 (§6); story cards and the DoR check (§14); build lanes (§15).

## 1. Sprint goal

- A player tags every rally of an uploaded match by tapping or by keyboard (start, end, winning side, ending, optional responsible player). Each tag shows the new score at once and announces it to screen readers.
- The player opens a score sheet that lists every rally with server, score before and after, winner and ending. The score is computed by replaying the rules, never stored as an editable value, and the sheet is labelled "unofficial scoring (rules not yet verified)" (FR-055).
- The player can undo any tag and correct any rally. Later rallies are re-scored in one step. Rallies that a correction pushes past the end of a game are kept and marked "needs your decision", never deleted. Every change is in an audit trail.
- Every rally row opens the video at that rally, through a short-lived link.
- The Sprint 1 blockers and majors are fixed first (C-01..C-06, ST-013b), and none is open at the close.

**How it is measured:** the 12 metrics of [`02/goal-scorecard.md`](02/goal-scorecard.md), on the live local stack over https (PO standing rule).

**Stretch, not goal:** a match that starts mid-game (ST-034) and singles matches (ST-035), under the provisional preset (§0.4).

This demonstrates spec M0's "Done when": *a user can tag a match by hand and get a score sheet*. It is "correct" only in the unofficial sense until OQ-01 is answered and NFR-003 passes (ADR 0009).

**Not in this sprint:** stats (Sprint 3), training plans (Sprint 4), worker least-privilege credentials (ST-042, Sprint 3), correction consequences and gaps (stretch here), age gate and retention settings (Sprint 4).

## 2. Capacity (ADR 0010)

Load factor **80% (12.8 units per lane)**, kept from Sprint 1 (decision-log 2026-10-05: the ADR 0010 rule would give 0 on the `dod_done` ratio; the implemented ratios are 0.68 and 0.906, median 0.79; retro 1 §10). Minors and nits of the carry-over (C-07..C-38) go into the review-loop reserve, which is the uncommitted rest of each lane.

| Lane | Committed | Stretch (in order) | Streams (ADR 0010, ≤ 2, disjoint) |
|---|---|---|---|
| BE | 12.5: C-01 1, C-02 1, ST-013b 1, ST-026 2, ST-027 2, ST-030 0.5, ST-031 2, ST-032 2, ST-037 1 | ST-035 1, ST-034 1, ST-038 1, BE minors C-07..C-09, C-14, C-16, C-17, C-19, C-25..C-28 | 1: `matches` (aggregate, tagging, corrections, projection API). 2: `players` and `video_ingest` (C-01, C-02, ST-013b, ST-037 media URLs), then `sports/pickleball` (stretch ST-035, ST-034) |
| FE | 12.0: C-03 1, ST-027 4, ST-028a 1, ST-029 1, ST-030 2, ST-031 1, ST-032 1, ST-037 1 | ST-028b 1, ST-034 0.5, FE minors C-20, C-21, C-30, C-36, C-37, then ST-033, ST-036 | 1: Quick Tag, keyboard, announcements (`web/src/app/matches/[matchId]/tag`). 2: score sheet, corrections, undo, rally video (`web/src/app/matches/[matchId]/sheet`), after C-03 in the upload panel |
| QA | 11.5: ST-041 2, QA-ACC 2, ST-039 (QA) 2, QA-FUZZ 1, C-04 0.5, C-06 1, C-22 0.5, C-31 0.5, C-32 0.5, C-34 0.5, scorecard dry-runs 1 | — | 1: golden tables, scenario steps, fuzz and ITs (`backend/tests`, `tests/features`). 2: Playwright specs, timing spec, a11y (`web/e2e`) |
| SRE | 8.0: W-01 1, ST-039 (SRE) 1, SRE-MEDIA 1, SRE-SMOKE 1, C-05 0.5, C-11 0.5, C-12 0.5, C-13 0.5, C-15 0.5, C-18 0.5, C-23 0.5, C-29 0.5 | ST-042 (SRE half) only if BE pulls ST-042 forward | 1: CI, Locust, smoke (`.github/`, `infra/tests`). 2: Compose, TLS proxy, object store (`infra/compose.yaml`, `infra/tls`, `infra/docker`) |
| ML | 2.0: ST-040 2 | ST-025 (carried) 1, only when the PO recordings exist (P3) | 1: `docs/data`, `backend/src/racket/dataset` |
| **Total** | **46.0** | | |

The BE and FE lanes are the bottleneck: 12.5 and 12.0 of 12.8. The other lanes carry the carry-over, CI and evidence work. If C-01 or C-02 takes more than its size, the BE stretch is the first to go, then ST-037 (BE) moves to stretch with the PO told (judgment).

## 3. Committed backlog

| Story | Title | FR / NFR | Owner (R) | Required reviewers | Size | Depends on |
|---|---|---|---|---|---|---|
| ST-026 | `Match` aggregate persistence: games, rallies, outcome inputs; score as a projection by replay | FR-049 (backend); NFR-075 | BE | QA, principal-engineer | M | design doc; ST-020, ST-021 |
| ST-027 | Quick Tag a rally | FR-050; NFR-012, NFR-028, NFR-030 | BE (M) + FE (L) | QA, principal-designer, pickleball-domain-coach, principal-engineer (API contract) | M+L | ST-026 |
| ST-028a | Keyboard tagging, the `?` key map, single-key shortcuts that can be turned off (split 2026-10-05; remapping is ST-028b, stretch) | FR-051; NFR-034 | FE | QA, principal-designer | S | ST-027 |
| ST-029 | Score call and polite announcement after each tag | FR-048 (call format provisional) | FE | QA, principal-designer, pickleball-domain-coach | S | ST-027 |
| ST-030 | Score sheet with the "unofficial scoring" label | FR-049, FR-055; NFR-011, NFR-029, NFR-033, NFR-034 | FE (M) + BE (XS) | QA, principal-designer, pickleball-domain-coach | M+XS | ST-026 |
| ST-031 | Undo and correction audit | FR-052 | BE (M) + FE (S) | QA, principal-engineer, security-privacy-engineer (audit) | M+S | ST-026 |
| ST-032 | Corrections replay the score; conflicting rallies kept (a) | FR-053 (a); NFR-013 | BE (M) + FE (S) | QA, principal-engineer, pickleball-domain-coach | M+S | ST-031, ST-041 |
| ST-037 | Jump to the video moment with short-lived media URLs | FR-027; NFR-014, NFR-055 | BE (S) + FE (S) | QA, security-privacy-engineer | S+S | ST-027 |
| ST-039 | E2E journey v1 and performance baseline | NFR-010, NFR-012, NFR-013, NFR-017 (baselines) | QA (M) + SRE (S) | principal-engineer, sre-devops-engineer | M+S | ST-030 |
| ST-040 | Gold-set label schema, manifest v1 and footage capture protocol | FR-151 (prep for QD-GD-03/-04/-07) | ML | QA, security-privacy-engineer (consent), pickleball-domain-coach | M | OQ-06 |
| ST-041 | Golden tables written first: SOS rows, declared starts SOD-13..15, corrections C-01..C-04 (rows of stretch stories carry `red_until` that story) | NFR-001 (provisional rows) | QA | pickleball-domain-coach, principal-engineer | M | — |

**Planning additions (2026-10-05, engineering-manager; retro 1 A1, A4, A5):**

| Row | Title | FR / NFR | Owner (R) | Required reviewers | Size | Depends on |
|---|---|---|---|---|---|---|
| W-01 | CI triage, WebKit first: read CI run 37377206126 (`ci-gate` red on PR #1) and every later run; route each failure to its owner as an Open row in `review-rounds.md` (the 8 `[webkit]` failures to senior-frontend-engineer when they are product defects, to QA when they are test defects); keep `docs/sprints/02/ci-status.md`; dispatch `nightly-quality.yml` once it is on `main` | NFR-024, NFR-074; retro 1 A1 | SRE | senior-qa-engineer, senior-frontend-engineer | S | PO item P1 for the merge |
| QA-ACC | Acceptance first: the Gherkin step modules for §7.1-§7.4 and §7.6, and the Playwright specs E2E-02-02..E2E-02-06 written red before their stories (`red_until` the story) | FR-049..FR-053, FR-027 | QA | principal-engineer (API contract use), principal-designer (UI states) | M | api-sprint-02.md (D2), flows-sprint-02.md (D2) |
| QA-FUZZ | Testing-strategy rule L11: every JSON string field at the API boundary gets a Hypothesis test with control and surrogate characters (4xx, never 5xx, no row written; IT-02-10); every limit gets a concurrency case (IT-02-11 for the upload quota) | NFR-023, NFR-058; retro 1 A4, M15 | QA | security-privacy-engineer, senior-backend-engineer | S | — (red before C-01, C-02) |
| SRE-MEDIA | Media serving for ST-037: presigned GET from the object store through the https origin, HTTP range requests (206), TTL ≤ 15 min from config, CORS limited to the web origin; no session token in any media URL | FR-027; NFR-055 | SRE | security-privacy-engineer, senior-backend-engineer | S | ST-037 (BE) API |
| SRE-SMOKE | Integration smoke before review round 1 on an isolated, self-cleaning stack (ADR 0022, ADR 0033 rule 3), recorded in `docs/sprints/02/smoke.md` | working-agreement §7 step 1a | SRE | senior-qa-engineer | S | the integrated tree |

**Moved out at planning (decision-log 2026-10-05; PO item P4):**

| Story | Title | FR / NFR | Owner (R) | Size | Now |
|---|---|---|---|---|---|
| ST-034 | Start the score sheet mid-game (a) | FR-046 (a) | BE (S) + FE (XS) | S+XS | Stretch 2. SOD-13..SOD-15 are written first by ST-041 with `red_until(story="ST-034")` |
| ST-035 | Side-out singles (a) | FR-042 (a) | BE | S | Stretch 1. SOS rows written first by ST-041 with `red_until(story="ST-035")` |
| ST-038 | Abandoned uploads expire | FR-024; NFR-066 (d) | BE | S | Stretch 3 (a gate before any non-dev deployment; none is planned in Sprint 2) |
| ST-028b | Remap tagging keys | FR-051 | FE | S | Stretch 4 |
| ST-042 | Least-privilege credentials for the media sandbox worker | NFR-054 | BE + SRE | S+S | Sprint 3 (its finding SEC-R5-S1-01 is already "Deferred"; a gate before any non-dev deployment) |
| GATE-BETA-ASVS-6.3.3 | Re-review of ADR 0031 (single-factor magic link, ASVS 6.3.3) before any real-user beta opens: the PO chooses option 1 again with a review date before general availability, or option 2 (passkeys) | ASVS 6.3.3; threat model T-ML-13, S1-F1 | human PO (decider); security-privacy-engineer (input); engineering-manager (puts it on the beta plan) | — | A gate before any real-user beta, like ST-042 and ST-038 before any non-dev deployment. Added 2026-10-06 (review round 1, SEC-R4-S1-04 / QA-R2V-11; PO decision P2) |

**Security carry-over from Sprint 1 (proposed 2026-10-05 by sre-devops-engineer, review round 2, SEC-R5-S1-01; EM confirms at planning).** *Planning 2026-10-05: ST-013b confirmed and committed (its finding is an open major); ST-042 moved to Sprint 3 (table above).*

| Story | Title | FR / NFR | Owner (R) | Required reviewers | Size | Depends on |
|---|---|---|---|---|---|---|
| ST-042 | Least-privilege credentials for the media sandbox worker (threat model S1-F3, v0 F-1). The worker gets its own Postgres role with SELECT/UPDATE only on the job, media and upload tables, and no access to `sessions`, `sign_in_*` or `accounts`; the worker also gets its own S3 key. Then a test shows that a worker-uid process reading `/proc/1/environ` can no longer read `sessions` | NFR-054; ASVS 14.x (judgment) | BE (grants migration, S) + SRE (Compose roles, SeaweedFS identity, S) | security-privacy-engineer, principal-engineer | S+S | — |
| ST-013b | Account identity is the stored normalised address, not the 64-bit HMAC `email_key` (ADR 0032 option 1; SEC-R3-S1-01 / SEC-R4-S1-01). New migration: `accounts.email` unique, `email_key` kept as the log/rate-limit pseudonym only (not unique); the address rides the `sign_in_links` row and is nulled when the link is used or refused; legacy dev accounts are claimed once by `email_key`. QA's red tests 1-5 in ADR 0032 first (rotation keeps the account; a forced `email_key` collision gives two accounts) | NFR-057, NFR-069; ADR 0025, 0027, 0032 | BE | QA (red tests 1-5), security-privacy-engineer, principal-engineer | S | ADR 0032 Accepted |

ST-042 is a **gate before any non-dev deployment**, like S1-F2 and ST-038. **GATE-BETA-ASVS-6.3.3** is a gate before any real-user beta: ADR 0031 was accepted by the PO on 2026-10-06 (option 1) for R1 on the condition that it is re-reviewed before a real-user beta opens. ST-013b (carried 2026-10-05 by senior-backend-engineer, sprint-close review round 2, SEC-R4-S1-01) is the same kind of gate; until it ships, `AUTH_EMAIL_KEY` must never be rotated where accounts must be kept. The Sprint 1 part is already done: the mailer no longer holds the S3 key.

**ML carry-over from Sprint 1 (proposed 2026-10-05 by senior-ml-cv-engineer, sprint-close review round 2, S-07 / QA-R2V-07; the PO approves via blockers.md item P3, the EM confirms at planning):**

| Story | Title | FR / NFR | Owner (R) | Required reviewers | Size | Depends on |
|---|---|---|---|---|---|---|
| ST-025 (carried) | Phone-file fixture set `phones-v1` and upload-cap measurement (R-05), remaining part only: the PO hands over real recordings from ≥ 5 phone models incl. one VFR file (empty court or consenting team members, OQ-06) per `docs/data/phone-fixtures.md` §3; senior-ml-cv-engineer runs `scripts/fixtures/build_phone_manifest.py`, makes `phone_fixtures.feature` "Coverage of the set" and "Probe every fixture" green unchanged, and writes the R-05 numbers on FR-023 conflict K12. The consent rule, build tool, `phone-profiles-v1` shape set and recording protocol are already done in Sprint 1 | NFR-025; FR-023 (caps) | ML | QA, security-privacy-engineer, sre-devops-engineer (LFS or object store if a clip is over 15 MiB, P6) | S | PO recordings (input needed by Sprint 2 planning, 2026-11-02) |

Until ST-025 lands, ST-018 keeps the provisional 10 GB / 150 min caps and the device-specific 60 fps menu paths stay hidden. If the recordings are not in hand at planning, ST-025 stays out of the committed load (it cannot start without them) and the blocker row stays Open. *Planning 2026-10-05: the recordings are not in hand (no `fixtures/clips/phones-v1/`), so ST-025 is ML stretch and S-07 stays an Open blocker (PO item P3).*

**Design carry-over from Sprint 1 (proposed 2026-10-05 by principal-designer, sprint-close review round 2, PD-R1-06 / QA-R2V-12; applies only if the asynchronous review is not complete by end of 2026-10-06, flows §10.2; the EM confirms at planning).** *Planning 2026-10-05: confirmed; the review is not held (PD-R1-06 still Open), so DR-01 is committed and is due on D1.*

| Story | Title | FR / NFR | Owner (R) | Required reviewers | Size | Depends on |
|---|---|---|---|---|---|---|
| DR-01 (carried) | Finish the DoR P7 flows design review of `docs/design/flows-sprint-01.md` §10.1: the remaining "Decision at review" cells, then the chair records the outcome in §10, amends U-04 (R-2a, R-2b) and adds the §6 quota, conflict and rate-limit states (R-5). **Hard date: 2026-11-02 (planning).** No Sprint 2 UI story starts before it | DoR P7; NFR-030..NFR-037 | principal-designer (chair) | pickleball-domain-coach, senior-frontend-engineer, business-analyst, security-privacy-engineer, product-manager | XS | Participants' decisions |

**EM carry-over from the Sprint 1 review (engineering-manager, 2026-10-05, sprint close after goal round 3; ADR 0030 rule 1, PE-R3R-05).** These rows are open Sprint 1 findings. Every deferred finding has one row here with an owner, so none is lost. **C-01..C-06 are blockers or majors.** They are fixed red-first before any new Sprint 2 story starts, unless the PO re-plans (blockers.md item P4; retro 1 final action A2). The minors and nits (C-07..C-38) go into the review-loop reserve. Sizes are judgment. Total: about 6 units for C-01..C-06 and about 6 units for C-07..C-38, inside the 10-12 unit carry-over reserve of the Sprint 1 retro.

| Row | Finding(s) | Work | Owner (R) | Reviewer | Size |
|---|---|---|---|---|---|
| C-01 | SEC-R6-S1-01 (blocker) | Refuse Cc/Cs characters in `normalise_email` and in the match title check. Red first: unit tests, plus an IT asserting 422 `email_invalid` / `title_invalid` and no row written | senior-backend-engineer | senior-qa-engineer, security-privacy-engineer | S |
| C-02 | PE-R3R-01 (major) | Take the per-owner lock before `_check_quota`. Red first: a concurrency IT (8 parallel creations → 3 × 201) | senior-backend-engineer | senior-qa-engineer, security-privacy-engineer | S |
| C-03 | PD-R3V-01 (major), with PD-R3-04 | U-01 server-error state per flows §6: "Try again" keeps the transfer, no contradictory "No video yet", and `support_ref` shown | senior-frontend-engineer | principal-designer, senior-qa-engineer | S |
| C-04 | QA-R3-E2E-01 / PD-R3V-02 (major) | `walking-skeleton.spec.ts`: hold the PATCH until the progress text is checked; add the root specs to the G01-03 repeat. TCR row first | senior-qa-engineer | sre-devops-engineer | XS |
| C-05 | QA-R3-E2E-02 (major) | Evidence E2E runs use `--output` under the run directory and take the E2E evidence lock (ADR 0033 rule 3) | sre-devops-engineer | senior-qa-engineer | XS |
| C-06 | QA-R3-GATE-01 (major) | Manual screen-reader pass (NFR-027b) on the Sprint 1 screens with VoiceOver (iOS) and TalkBack (Android), by a human with devices; results in `docs/sprints/02/a11y-manual.md`. Due 2026-11-13 | senior-qa-engineer (plan, record), human PO (devices or tester) | principal-designer | S |
| C-07 | PE-R3R-02 | Sign-in mail sent in `after_commit`; record the at-least-once or at-most-once choice | senior-backend-engineer | principal-engineer | XS |
| C-08 | PE-R3R-03 | Pin DB `TimeZone=UTC`, or format timestamps in UTC; unit test with a non-UTC session | senior-backend-engineer | senior-qa-engineer | XS |
| C-09 | QA-R3-TEST-01 | Regression test: unknown key and non-object body on `POST /auth/links` | senior-backend-engineer | senior-qa-engineer | XS |
| C-10 | PE-R3R-06 | `JobKey.match_id` overload: rename to `subject_id` or document it in context map R7 | principal-engineer | senior-backend-engineer | XS |
| C-11 | SEC-R6-S1-02 | Do not publish the API port to the host, or document that T-ML-8 holds only behind web-tls | sre-devops-engineer | security-privacy-engineer | XS |
| C-12 | QA-R3-SMOKE-01 | `smoke.md` §7 at the sprint-close head | sre-devops-engineer | senior-qa-engineer | XS |
| C-13 | SRE-G2-01 | OTLP metrics exporter: point it at a metrics backend, or switch metrics export off in dev | sre-devops-engineer | — | XS |
| C-14 | SRE-G2-02 | `ClientDisconnect` during PATCH is not logged as a 5xx | senior-backend-engineer | sre-devops-engineer | XS |
| C-15 | G01-05 goal round 3 | Teardown of every evidence stack uses `down -v --rmi local` (ADR 0033 rule 3); rerun G01-05 with ≥ 12 GB free once the human approves removing the stale images | sre-devops-engineer, human PO | senior-qa-engineer | XS |
| C-16 | PE-R2-S1-05 | Upload creation: defer `_discard` deletes until after commit; test with expired session plus malformed metadata | senior-backend-engineer | senior-qa-engineer | XS |
| C-17 | SEC-R5-S1-02 | Durable pending-delete for a refused original (outbox row), or an `originals/` reconciliation in ST-038; T-UV-3 note | senior-backend-engineer, principal-engineer | security-privacy-engineer | S |
| C-18 | SEC-R5-S1-03 | `ALLOWED_ORIGINS=${PUBLIC_WEB_ORIGIN}` in env.example and the CI E2E env; infra test | sre-devops-engineer | security-privacy-engineer | XS |
| C-19 | SEC-R5-S1-04 | Refuse `DEV_IDENTITY_ENABLED=true` outside dev/test (red unit test first) | senior-backend-engineer | security-privacy-engineer | XS |
| C-20 | PD-R2R-05 | "You can still tag this match." only after a consequence finding | senior-frontend-engineer | principal-designer | XS |
| C-21 | PD-R2R-06 | M-01 date in the viewer's time zone; flows M-01 status copy | senior-frontend-engineer | principal-designer | XS |
| C-22 | PD-R2R-08 | axe and target-size checks on A-02, U-01 trouble/paused/stopped, the 429 states and M-02 with the report | senior-qa-engineer | principal-designer | XS |
| C-23 | PD-R2R-10 | Disk precheck at the start of every E2E evidence run (not only live_goal) | sre-devops-engineer | senior-qa-engineer | XS |
| C-24 | QA-R2V-14 | Scorecard §4.0 template documents the host-port remap for isolated stacks | engineering-manager | senior-qa-engineer | XS |
| C-25 | PE-R1-06 | `DEV_WEB_ORIGIN` default to the https origin | senior-backend-engineer | — | XS |
| C-26 | PE-R1-07 | `_check_inputs` rejects a game-over state without a winner | senior-backend-engineer | senior-qa-engineer | XS |
| C-27 | PE-R1-10 | `match_state.py:97` nit | senior-backend-engineer | — | XS |
| C-28 | SEC-R1-S1-04 | `used_at IS NULL` predicate on the exchange UPDATE, assert rowcount 1 | senior-backend-engineer | security-privacy-engineer | XS |
| C-29 | SEC-R1-S1-05 | HSTS in the deployment ADR's acceptance criteria | sre-devops-engineer | security-privacy-engineer | XS |
| C-30 | PD-R1-09 / PD-R2R-07 | M-01 `error.tsx` with support_ref, skeleton loading rows, offline message | senior-frontend-engineer | principal-designer | S |
| C-31 | PE-R2-04 | Recheck `test_worker_crash` on a shared DB once isolation lands | senior-qa-engineer | — | XS |
| C-32 | PE-R3-06 | Test-isolation follow-up (retro 1 A2) | senior-qa-engineer | — | XS |
| C-33 | PE-R1-09 / PE-R3-07 | Amend api-sprint-01 §2.4 and scoring-engine.md §2.2/§2.4 (rolling window) | principal-engineer | senior-backend-engineer | XS |
| C-34 | PE-R3-08 / QA-R2V-13 | Reword the 0-0-2 seam comment in `contract.py` | senior-qa-engineer | principal-engineer | XS |
| C-35 | PD-R3-04 | Support reference in the upload server error (with C-03) | senior-frontend-engineer | principal-designer | XS |
| C-36 | PD-R3-06 | Distinct names for several resume banners on M-01 | senior-frontend-engineer | principal-designer | XS |
| C-37 | PD-R2-06 / PD-R2R-11 | F-01 link target; 48 px touch targets for the menu and secondary links (design review R-6) | senior-frontend-engineer, principal-designer | — | XS |
| C-38 | PD-R3-05 / PD-R2R-09 | Quota, conflict and rate-limit states in flows §6 (DR-01, R-5) | principal-designer, product-manager | security-privacy-engineer | XS |

**Stretch, in this order:** ST-035, ST-034, ST-038, ST-028b (table above), the carry-over minors in each lane, then ST-033 Correction consequences (FR-054; FE S + BE XS) and ST-036 Gaps and resync (FR-047; BE XS + FE XS, sized S overall). A stretch story starts only when its lane's committed stories are implemented and their review round 1 is held.

### 3.1 Acceptance notes per story

- **ST-026:** one command changes one aggregate in one transaction (ddd-guidelines §4.1). Score before/after is computed by `fold` over stored outcome inputs and is never an editable column (FR-049; ENG §3.2). Every stored output carries `rules_version` (NFR-075). A golden replay of stored rallies reproduces the stored score sheet byte for byte (QD-TR-04).
- **ST-027:** controls per FR-050 and DES FR-UX-60: rally start, rally end, winner side, ending (winner, unforced error, forced error, fault, replay), optional responsible player, optional fault subtype. Controls are ≥ 48 dp with no overlap of the focused control [DPA/DESIGN-10, DPA/DESIGN-07]. No dragging is needed (NFR-030) [DPA/DESIGN-05]. The optimistic score update appears within 200 ms p95 (NFR-012a). FR-050 now states the R1 behaviour: "the video continues from the end of rally 7, ready to mark rally 8"; jumping to the next rally start waits for FR-087 in R2 (review-log RL-02, 2026-10-03).
- **ST-028a:** key map shown with `?` (DES FR-UX-61). Single-key shortcuts can be turned off (WCAG SC 2.1.4 "turn off" option; remapping is ST-028b, stretch). Keyboard tagging gives a score sheet identical to tapping (FR-051).
- **ST-029:** after each tag or correction, a polite live region announces "Rally 7: them. Score 4-6-1." (FR-048, DES FR-UX-62). The call format is provisional; its scenario is tagged `@needs-verification` until the coach verifies it.
- **ST-030:** a semantic table with caption and row headers, readable at 360 px by stacking (FR-049, DES FR-UX-70). Markers for corrected rallies ("corrected by you") and conflicts in text, not colour alone (NFR-034). The label "unofficial scoring (rules not yet verified)" appears on every score sheet while any rule in the scoring path is unverified (FR-055).
- **ST-031:** every tag and correction can be undone. Corrections are append-only rows (who, when, field, old value, new value) and set `corrected_by_user` (FR-052). The table is protected against UPDATE and DELETE at the database level (judgment).
- **ST-032:** changing rally *k* replays *k..n* atomically. If a correction ends or un-ends a game, the affected rallies are marked "needs your decision" (FR-053). The mechanics (replay equals a fresh fold; undo restores a byte-identical sheet: C-01, C-04) are Ready. The game-end cases (C-02, C-03) are tagged `@needs-verification` (ADR 0009). Server-confirmed state arrives within 1.5 s p95 for a 3-game match (NFR-013).
- **ST-034:** the user declares a starting score and serving side; impossible states are refused (FR-046). Rows SOD-13..SOD-15 are `@needs-verification`.
- **ST-035:** two-number call; a rally lost by the server is a side-out; serving court by parity of the server's score (FR-042). All rows `@needs-verification`.
- **ST-037:** rally rows link to the video at the rally's start time (FR-027). Media is served by presigned URLs with TTL ≤ 15 min, never with session tokens in the URL (NFR-055) [AQS/SEC-05 14.2.1], with HTTP range support for seeking. Click to first frame playing ≤ 1.5 s p95 on the reference profile (NFR-014; reference profile pending OQ-17).
- **ST-038:** an upload not completed within 24 h (configurable) expires; its bytes are freed and it is no longer listed or resumable (FR-024; ADR 0006, Proposed).
- **ST-039:** Playwright journey v1: sign in → set up → upload fixture → Quick Tag 6 rallies → score sheet equals the golden sheet (QD §7, first half). Locust baseline at 50 RPS for match, score-sheet and correction endpoints (NFR-010, NFR-013), and tag-to-current timing (NFR-017). Baselines are recorded; they become gates at the R1 review (Sprint 5).
- **ST-040:** label schema for Full Tag (hit, bounce, hitter, rally boundaries, outcome, facets) and the gold-set manifest v1 per QD §8. A written capture protocol for team-recorded footage with written consent from everyone filmed (OQ-06 recommendation), split by venue (FR-151). No real-match footage is collected before the PO answers OQ-06.
- **ST-041:** QA writes the SOS rows, SOD-13..SOD-15 and C-01..C-04 from QD §2.2 before ST-032, ST-034 and ST-035 start. With Sprint 1's SOD/F/M rows this reaches the ≥ 46 rows of NFR-001.

### 3.2 Order of work per lane (retro 1 A2)

1. **BE:** C-01 → C-02 (both red-first, "Fixed" in `review-rounds.md` before anything else) → ST-013b → ST-026 (after the D1 design review) → ST-027 → ST-030 → ST-031 → ST-032 → ST-037 → stretch.
2. **FE:** C-03 (with C-35) → ST-027 UI (after DR-01 and the Sprint 2 flows) → ST-028a → ST-029 → ST-030 → ST-031 → ST-032 → ST-037 → stretch.
3. **QA:** QA-FUZZ (red before C-01) → C-04 → ST-041 → QA-ACC → C-22, C-31, C-32, C-34 → ST-039 → scorecard dry-runs; C-06 with the human tester by 2026-11-13.
4. **SRE:** C-05, C-15, C-23 (self-cleaning evidence) → W-01 → C-11, C-12, C-13, C-18, C-29 → SRE-MEDIA → ST-039 (Locust) → SRE-SMOKE.
5. **ML:** ST-040; ST-025 when P3 is answered.

## 4. Task breakdown per role agent

| Agent | Tasks | Due | Done-check |
|---|---|---|---|
| engineering-manager | D1: send the PO list P1-P9 (blockers.md); brief each lane with its slices (each ≤ 400 changed lines, waivers before the commit); carry the 17 open Sprint 1 families into `review-rounds.md` (done at planning). Daily: status step after every fix round (`status.json`, `progress.md`, `open_defects.py` count, sprint-report §1 when it changes). C-24 (scorecard §4.0 port remap, done at planning). D10: retro | D1, daily, D10 | `status.json` complete; G02-11 count matches the reviewers' rows every round |
| product-manager | D1: confirm the §14 priorities and the re-plan with the PO (P4); confirm the R1 exit criteria and usability-test plan (OQ-20); chase OQ-01 (latest useful date: Sprint 3 planning) and OQ-13 (Sprint 2 review); C-38 with principal-designer | D1, D3 | Answers recorded in `decision-log.md` or as ADR notes |
| business-analyst | §14 story cards and DoR check (done at planning, 2026-10-05); confirm the FR-050 R1 video behaviour with the PO (review-log RL-02); write Sprint 3 stories (stats, evidence, deletion, labelling tool, drill schema); traceability rows for the new feature files | D2, D8 | Sprint 3 stories meet DoR; traceability matrix lists the Sprint 2 feature files |
| principal-engineer | **D1: chair the design review of `match-aggregate.md`** (reviewers: senior-backend-engineer, senior-qa-engineer, pickleball-domain-coach, security-privacy-engineer) and record the outcome in the doc; **D2: `docs/architecture/api-sprint-02.md`** (routes, If-Match versions, error codes, sheet and history shapes) and the same-commit update of `scripts/measure/tagcontract.py` if it differs; C-10, C-33; review ST-026/ST-032 for aggregate invariants; D9: Analytics design note for Sprint 3 | D1, D2, D9 | Design doc "Accepted"; contract merged; G02-01..G02-04 dry-run rows written with the method authors |
| principal-designer | **D1: DR-01** (the Sprint 1 P7 review, hard date 2026-11-02); **D2: `docs/design/flows-sprint-02.md`** with every state of Quick Tag (T-), key map (K-), score sheet (S-), correction history (H-) and rally video (V-), the HAX and WCAG checklists, screen ids for the axe attachments (G02-10); C-37, C-38; review the Sprint 2 UI; D9: Sprint 3 stats flows; NFR-036 usability protocol (Sprint 5) | D1, D2, D5, D9 | Flows reviewed and approved before any Sprint 2 UI story starts |
| security-privacy-engineer | D2: threat notes for the audit trail (ST-031), media URLs (ST-037, SRE-MEDIA) and the JSON fuzz rule (QA-FUZZ); input on ADR 0031 for the PO (P2); D-8 wording for PD-R2R-03; review C-01, C-02, ST-013b; deletion threat notes for Sprint 3 | D2, D6 | Notes attached to the story cards; controls named as acceptance criteria |
| pickleball-domain-coach | D2: answer match-aggregate §8 Q1 (C-02/C-03 resolution choices) and Q2 (responsible-player side for forced errors); review every rule-related scenario and PR; verify the call format and rows when OQ-01 lands; AN-01..AN-07 to `coach-reviewed` for Sprint 3 (QD-AN-03) | D2, D8 | Answers recorded in the design doc; each AN entry has a definition and min sample |
| senior-backend-engineer | §3.2 BE order: C-01, C-02, ST-013b, then ST-026, ST-027 (API), ST-030 (API), ST-031, ST-032, ST-037 (API); stretch ST-035, ST-034, ST-038 and the BE minors | D1-D9 | Scenarios and IT-02 ids green; C-01, C-02, SEC-R3-S1-01 "Fixed" |
| senior-frontend-engineer | §3.2 FE order: C-03 (with C-35), then ST-027 (UI), ST-028a, ST-029, ST-030, ST-031 (UI), ST-032 (UI), ST-037 (UI); WebKit product defects routed by W-01; stretch ST-028b, ST-034 (UI), FE minors, ST-033, ST-036 | D1-D9 | Playwright, axe, keyboard and timing journeys green |
| senior-qa-engineer | §3.2 QA order: QA-FUZZ, C-04, ST-041 (D1-D2), QA-ACC, C-22, C-31, C-32, C-34, ST-039, scorecard dry-runs (G02-03, 05..10, 12); C-06 with a human tester; sprint test report | D2, D9, D10 | Report separates `@needs-verification`; every QA-owned method has a dry-run row |
| sre-devops-engineer | §3.2 SRE order: C-05, C-15, C-23, W-01, C-11, C-12, C-13, C-18, C-29, SRE-MEDIA, ST-039 (Locust in CI), SRE-SMOKE; G02-04 dry-run | D1-D8 | CI status recorded; smoke.md entry at the integrated head; Locust job runs |
| senior-ml-cv-engineer | ST-040 (capture protocol covers US and AU consent, ADR 0023 note); plan SPIKE-02/03 inputs for Sprints 3-5; ST-025 only when P3 is answered | D8 | Schema and protocol merged |

## 5. TDD plan (negative case first) [EP/ENG-18]

| Domain object / unit | Context | First tests, in order |
|---|---|---|
| `Rally` | matches | 1. end before start → error; 2. overlapping an earlier rally → error; 3. times are integer ms from video start (QD-TR-02) |
| `RallyOutcome` | matches | 1. unknown ending → error; 2. a responsible player for an error or fault must be on the side that lost the rally (judgment; coach to confirm); 3. a responsible player for a winner must be on the winning side; 4. responsible player optional |
| `Match.tag_rally` | matches | 1. tag on a match that is over → `MatchOver`; 2. tag on a match not yet uploaded → refused (NFR-060); 3. a tag appends a rally and the projection shows the new score |
| `ScoreSheet` projection | matches | 1. empty match → empty sheet; 2. projection equals `fold` over outcomes (P6); 3. replay rally rows show no score change (P8); 4. golden replay byte-identical (NFR-075) |
| `Correction` | matches | 1. correction of a non-existent rally → error; 2. correction records old and new values; 3. corrections are never edited, only appended; 4. a correction sets `corrected_by_user` |
| `Undo` | matches | 1. undo with nothing to undo → error; 2. undo of a correction restores a byte-identical sheet (C-04); 3. undo is itself audited |
| `replay_from(k)` | matches | 1. k out of range → error; 2. replay equals a fresh fold (C-01); 3. game ending earlier marks later rallies `conflict`, keeps them (C-02, provisional); 4. un-ending a game marks the next game's first rallies `conflict` (C-03, provisional) |
| `DeclaredStart` (stretch ST-034) | matches / sports | 1. server number 3 → `IllegalStart` (SOD-15); 2. score already game over → `IllegalStart` (SOD-14); 3. "0-0-1" accepted (SOD-13) |
| `SinglesRules` (stretch ST-035) | sports/pickleball | 1. rally after game over → `GameOver`; 2. server loses → side-out (no server 2); 3. court by parity of the server's score |
| `ScoreCall` formatter | sports/pickleball | 1. doubles call has three numbers, serving side first; 2. singles call has two numbers |
| `UploadExpiryPolicy` (stretch ST-038) | video_ingest | 1. 23 h 59 min old → not expired; 2. 24 h old → expired; 3. completed uploads never expire by this rule |
| `MediaUrlPolicy` | video_ingest | 1. TTL above 15 min refused; 2. URL never contains the session token |
| `normalise_email`, match title (C-01) | players, matches | 1. NUL and every Cc/Cs character refused with `email_invalid` / `title_invalid`; 2. a Hypothesis test over arbitrary text never raises (testing-strategy rule 9, L11) |
| Upload quota (C-02) | video_ingest | 1. the per-owner lock is taken before `_check_quota`; 2. IT-02-11: 8 parallel creations → exactly 3 × 201 |
| `Account` identity (ST-013b) | players | ADR 0032 red tests 1-5 first: 1. `AUTH_EMAIL_KEY` rotation keeps the account; 2. a forced `email_key` collision gives two accounts; 3-5 as in ADR 0032 |

Front-end (Vitest): tagging reducer (1. "end" before "start" ignored; 2. optimistic score rolls back on a server error), key-map store (1. remap to a used key refused; 2. turning shortcuts off disables single keys only).

## 6. Integration tests

| ID | Boundary | Test | Story |
|---|---|---|---|
| IT-02-01 | API ↔ DB | Tag 30 rallies; stored outcomes replay to the same sheet; `rules_version` stored | ST-026 |
| IT-02-02 | API ↔ DB | A failure injected in the middle of a correction replay rolls back everything; the sheet is unchanged | ST-032 |
| IT-02-03 | DB | UPDATE or DELETE on the corrections table is refused | ST-031 |
| IT-02-04 | API ↔ DB | Concurrent tags on the same match: one wins, the other gets a conflict and retries (optimistic locking, judgment) | ST-027 |
| IT-02-05 | BOLA matrix | Rally, correction, undo, score-sheet and media-URL routes added; Carlos gets 404 on each | ST-026..ST-037 |
| IT-02-06 | API ↔ store | Presigned URL expires after its TTL; range requests return 206 | ST-037 |
| IT-02-07 | Scheduler ↔ store ↔ DB | Expiry job removes the object and hides the session after 24 h (clock injected). **Only if ST-038 (stretch) is pulled in** | ST-038 |
| IT-02-08 | API | Server-confirmed correction on a 3-game fixture within 1.5 s p95 over 50 runs | ST-032 |
| IT-02-09 | Logs | Correction and undo log lines carry `match_id` and pseudonymous user ID only | ST-031 |
| IT-02-10 | API boundary | Every JSON string field of every route (auth, matches, rallies, corrections) with Hypothesis-generated control and surrogate characters, NUL included: 4xx, never 5xx, and no row written (testing-strategy rule L11) | QA-FUZZ, C-01 |
| IT-02-11 | API ↔ DB | 8 parallel upload creations by one owner → exactly 3 × 201, the rest 429/409; the open-upload count never exceeds 3 | QA-FUZZ, C-02 |
| IT-02-12 | API ↔ DB | ADR 0032 red tests 1-5: identity is the stored normalised address; key rotation keeps the account; a forced `email_key` collision gives two accounts; the address on `sign_in_links` is nulled after use or refusal | ST-013b |

Test files are named `test_it_02_<nn>_<slug>.py` so the goal scorecard's `junit_rate.py --require test_it_02_<nn>_` finds each id (G02-03).

**E2E (Playwright, `web/e2e/sprint-02/`):** E2E-02-01 journey v1 (ST-039). E2E-02-02 keyboard-only tagging of the 6-rally fixture produces the same sheet as tapping. E2E-02-03 screen-reader announcement text appears in the live region after each tag, and focus stays on the controls. E2E-02-04 seek from rally row to playing video ≤ 1.5 s on the throttled profile. E2E-02-05 any call can be fixed in ≤ 2 taps or keys from where it is seen (NFR-036d). E2E-02-06 undo restores the sheet and the correction history lists the change and the undo. axe on every page (attachments `axe-<screen id>`), the 24×24 and 48×48 target checks, and the viewport matrix 320/360/768/1280 on the score sheet. Test titles carry their id (`E2E-02-0n`) so `junit_rate.py --require` finds them.

**Timing spec (ST-039):** `web/e2e/sprint-02/timing.spec.ts` attaches one `timing-<metric>` JSON body `{"ms": n}` per sample for `tag-optimistic`, `tap-feedback`, `seek-first-frame` (9/1.5 Mbit/s, 4× CPU) and `score-sheet-interactive`; `scripts/measure/pw_timings.py` turns them into p95 values (G02-06).

**Fixture:** the 6-rally fixture is a team-recorded, consented clip (GD-07 #2) if OQ-06 is answered. Otherwise the synthetic clip from ST-011 is used with scripted rally boundaries; tagging does not depend on what the video shows (judgment).

## 7. Gherkin scenarios

### 7.1 Quick Tag and keyboard

```gherkin
# tests/features/quick_tag.feature
@M0 @story-ST-027 @nfr-012
Feature: Quick Tag
  A player records each rally's outcome by hand; the rules engine scores it.

  Background:
    Given Ivy is tagging her doubles match "Saturday doubles"

  Rule: Each tagged rally is scored immediately

    Scenario: Tag a rally
      Given rally 7 has been marked from start to end
      When she records it as won by the other side with "unforced error" by herself
      Then rally 7 shows the new score
      And the error is attributed to her
      And the video continues from the end of rally 7, ready to mark rally 8

    Scenario: Responsible player skipped
      Given Ivy has tagged rally 8 without choosing a responsible player
      When she opens the score sheet
      Then rally 8 shows its winner and ending
      And rally 8 shows "player not tagged"

    Scenario Outline: Every ending can be recorded
      Given rally 9 has been marked from start to end
      When she records it as won by her side with ending "<ending>"
      Then rally 9 shows ending "<ending>" on the score sheet
      Examples:
        | ending         |
        | winner         |
        | unforced error |
        | forced error   |
        | fault          |

    Scenario: A replay does not change the score
      Given the score before rally 10 is "5-5-1"
      When she records rally 10 as a replay
      Then the score after rally 10 is still "5-5-1"

  Rule: A player on the wrong side cannot be blamed

    Scenario: Error attributed to the winning side
      Given rally 11 has been marked from start to end
      When she records it as won by her side with "unforced error" by her own partner
      Then she is told the player who made the error must be on the side that lost the rally
```

```gherkin
# tests/features/keyboard_tagging.feature
@M0 @story-ST-028 @nfr-034
Feature: Keyboard tagging
  Rule: Keyboard and touch give the same result

    Scenario: Keyboard only
      Given Ivy uses a keyboard and no pointer
      When she tags rallies 1 to 6 of the fixture match using keys only
      Then the score sheet is identical to tagging the same rallies with taps

  Rule: Shortcuts are discoverable and can be changed

    Scenario: Show the key map
      Given Ivy is on the tagging screen
      When she presses "?"
      Then she sees every tagging shortcut and what it does

    Scenario: Turn single-key shortcuts off
      Given Ivy has turned single-key shortcuts off
      When she presses "1" while the video has focus
      Then no winner is recorded
```

### 7.2 Score call (provisional format)

```gherkin
# tests/features/score_call.feature
@M0 @story-ST-029 @needs-verification
Feature: Score call and announcement
  The three-number call format is unverified [DOM G1 R6].

  Rule: Every tag is announced without moving focus

    Scenario: Screen-reader user tags a rally
      Given Ivy uses a screen reader while tagging
      When she tags rally 7 as won by the other side
      Then she hears the rally number, the winner and the new score
      And her focus stays on the tagging controls
```

### 7.3 Score sheet and unofficial label

```gherkin
# tests/features/score_sheet.feature
@M0 @story-ST-030 @nfr-033
Feature: Score sheet
  Rule: The score sheet is a complete text record of the match

    Scenario: Read the match without the video
      Given Ivy has tagged a 3-game match
      When she opens the score sheet
      Then every rally shows its number, server, score before and after, winner and ending
      And corrected rallies are marked "corrected by you" in text

    Scenario: Narrow phone screen
      Given Ivy opens her score sheet on a screen 360 pixels wide
      Then every rally's details can be read without scrolling sideways

  Rule: Unverified rules are never presented as official

    Scenario: Rules not yet verified
      Given the active rules preset contains an unverified rule
      When Ivy opens any score sheet
      Then she sees "unofficial scoring (rules not yet verified)"
```

### 7.4 Undo and corrections

```gherkin
# tests/features/undo_and_audit.feature
@M0 @story-ST-031
Feature: Undo and correction history
  Rule: Every change can be undone and is remembered

    Scenario: Undo a correction
      Given Ivy changed rally 5's winner
      When she undoes the change
      Then the score sheet is identical to the one before her change
      And her correction history lists both the change and the undo

    Scenario: Correction history shows what changed
      Given Ivy changed rally 5's ending from "winner" to "forced error"
      When she opens the correction history
      Then it shows rally 5, the field "ending", the old value "winner" and the new value "forced error"
```

```gherkin
# tests/features/corrections_replay.feature
@M0 @story-ST-032 @nfr-013
Feature: Corrections re-score later rallies
  Rule: A correction re-scores every later rally in one step

    Scenario: C-01 correction in the middle of a game
      Given a tagged game with 30 rallies
      When Ivy changes the winner of rally 5
      Then rallies 5 to 30 show scores recomputed from the corrected outcomes
      And the score sheet matches one built from scratch with the corrected outcomes

    Scenario: C-04 undo restores the exact sheet
      Given Ivy changed the winner of rally 5 of 30
      When she undoes that change
      Then the score sheet is identical to the one before the change

  Rule: Rallies are never deleted when a correction changes where a game ends

    @needs-verification
    Scenario: C-02 correction ends the game earlier
      Given a tagged game that side A won 12-10 after 24 rallies
      When Ivy changes rally 20 to "won by side A"
      Then the game shows as won by side A at rally 20
      And rallies 21 to 24 are listed as needing her decision, not deleted

    @needs-verification
    Scenario: C-03 correction un-ends a game
      Given game 1 was won by side A at rally 22 and game 2 has 5 tagged rallies
      When Ivy changes rally 22 to "won by side B"
      Then game 1 is no longer over
      And the first rallies of game 2 are listed as needing her decision, not deleted
```

### 7.5 Mid-game start and singles (provisional)

```gherkin
# tests/features/mid_game_start.feature
@M0 @story-ST-034 @needs-verification
Feature: Start the score sheet mid-game
  Rows SOD-13..SOD-15 from QD §2.2 [DOM G1, unverified].

  Scenario: Video begins part-way through a game
    Given Ivy declares the start as "4-6-2" with her side receiving
    When she tags the first rally as won by her side
    Then the score sheet shows "6-4-1" with her side serving

  Scenario: SOD-13 a legal mid-game start
    Given Ivy declares the start as "0-0-1"
    Then the declared start is accepted

  Scenario Outline: Impossible start refused
    Given Ivy declares a start score of "<start>"
    Then she is told why it is impossible and asked to correct it
    Examples:
      | id     | start  |
      | SOD-14 | 12-9-1 |
      | SOD-15 | 4-6-3  |
```

```gherkin
# tests/features/side_out_singles_provisional.feature
@M0 @story-ST-035 @needs-verification
Feature: Side-out singles scoring under the provisional preset
  Rows come from QD §2.2 SOS [DOM G1 R6, unverified]. Two-number call, server's score first.

  Background:
    Given the rules preset "PROVISIONAL-UNVERIFIED" with target 11 and margin 2

  Rule: Only the server scores; a lost rally passes the serve

    Scenario Outline: Score after one rally
      Given a singles game called "<before>" with player <srv> serving
      When the <winner> player wins the rally
      Then the score is called "<after>" with player <next> serving
      And the game is <state>
      Examples:
        | id     | before | srv | winner    | after | next | state          |
        | SOS-01 | 0-0    | A   | serving   | 1-0   | A    | not over       |
        | SOS-02 | 0-0    | A   | receiving | 0-0   | B    | not over       |
        | SOS-03 | 10-10  | A   | serving   | 11-10 | A    | not over       |
        | SOS-04 | 11-10  | A   | serving   | 12-10 | A    | won by A 12-10 |

    Scenario: SOS-05 rally after game over
      Given a singles game that player A has won 11-8
      When any rally is applied
      Then the rally is refused with a "game already over" message

  Rule: The server's court follows the parity of the server's score

    Scenario Outline: Serving court
      Given a singles game where the server's score is <score>
      When the server serves
      Then the serve is expected from the <court> court
      Examples:
        | score | court |
        | 0     | right |
        | 1     | left  |
        | 2     | right |
        | 3     | left  |
        | 4     | right |
        | 5     | left  |
        | 6     | right |
        | 7     | left  |
        | 8     | right |
        | 9     | left  |
        | 10    | right |
        | 11    | left  |
        | 12    | right |
```

### 7.6 Evidence deep link and upload expiry

```gherkin
# tests/features/evidence_deep_link.feature
@M0 @story-ST-037 @nfr-014 @nfr-055
Feature: Jump to the video moment
  Rule: Every rally row opens the video at that rally

    Scenario: Open a rally from the score sheet
      Given Ivy's score sheet lists rally 12 starting at 14:32
      When she opens rally 12's video link
      Then the video plays from 14:32

    Scenario: An old video link stops working
      Given Ivy copied a video link from her score sheet 20 minutes ago
      When the link is opened
      Then the video does not play
      And reopening rally 12 from the score sheet still works
```

```gherkin
# tests/features/abandoned_upload_expiry.feature
@M0 @story-ST-038 @nfr-066
Feature: Abandoned upload expiry
  Scenario: Upload never finished
    Given Ivy started an upload 25 hours ago and never finished it
    When she opens her matches list
    Then the partial upload is not listed
    And it cannot be resumed

  Scenario: Upload finished in time
    Given Ivy started an upload 23 hours ago and finished it 1 hour later
    When she opens her matches list
    Then the match is listed with its video
```

### 7.7 Stretch scenarios

```gherkin
# tests/features/correction_consequences.feature
@M0 @story-ST-033
Feature: Correction consequences
  Scenario: Correction affects later rallies
    Given Ivy is changing the winner of rally 8 of 20
    When she reviews the change before saving
    Then she is told the score of the next 12 rallies will change
```

```gherkin
# tests/features/gaps_and_resync.feature
@M0 @story-ST-036
Feature: Gaps in the video
  Scenario: Camera stopped for two rallies
    Given Ivy marks a gap after rally 9 and declares the resync score "7-5-1"
    When she views the score sheet
    Then a gap row appears after rally 9 and rally 10 starts at "7-5-1"
```

## 8. Quality gates

All Sprint 0 and Sprint 1 per-PR gates, plus:

| Gate | Threshold | Source |
|---|---|---|
| Mutation score on `sports/pickleball/rules` | ≥ 85% (first sprint as a gate) | NFR-072; QD-QG-S2 (judgment) |
| Golden tables | ≥ 46 provisional rows present; every row of a committed story green; rows `red_until` a stretch story (SOS: ST-035; SOD-13..15: ST-034) listed separately; all reported as `@needs-verification` | NFR-001; ADR 0009 |
| JSON boundary fuzz and limit concurrency | IT-02-10 and IT-02-11 green; 0 5xx from any generated body | retro 1 L11; NFR-023, NFR-058 |
| Open blocker/major findings | 0 in `docs/sprints/02/review-rounds.md` (carried Sprint 1 families included) | DoD; ADR 0030, ADR 0033 |
| Golden replay | byte-identical sheet for every stored fixture match | NFR-075; QD-TR-04 |
| Optimistic tag feedback (E2E timing) | p95 ≤ 200 ms; any tap feedback ≤ 100 ms | NFR-012 (judgment targets) |
| Correction confirmed by server | p95 ≤ 1.5 s on a 3-game match | NFR-013 |
| Seek to playing video | p95 ≤ 1.5 s, throttled profile | NFR-014 |
| No dragging; keyboard-only journeys | 100% of tagging and score-sheet flows | NFR-030, NFR-034 [DPA/DESIGN-05] |
| E2E journey v1 | green on `main` for ≥ 3 consecutive nightly runs before the review (judgment; 5 from the R1 review) | QD-QG-S4 |

Baselines recorded but not yet gating: NFR-010 (API latency at 50 RPS), NFR-017 (tag to current results).

## 9. Definition of Done

Story and sprint levels as in `docs/process/definition-of-done.md`. Sprint 2 adds:

- [ ] Every score sheet in the demo shows the "unofficial scoring" label.
- [ ] Rule-dependent scenarios are reported separately and counted toward no Must FR (QD-QG-P5).
- [ ] The pickleball-domain-coach has reviewed every rule-related scenario and PR (working-agreement §6).
- [ ] The traceability matrix lists the feature files for FR-024, FR-027, FR-042, FR-046, FR-048..FR-053, FR-055.
- [ ] Sprint 3 stories meet the DoR, including coach-reviewed metric entries AN-01..AN-07.
- [ ] Retro 1 action items reviewed first.
- [ ] **Every row of `docs/sprints/02/goal-scorecard.md` is "yes"**, filled by an independent verifier from one isolated, self-cleaning run at one recorded head (PO standing rule; ADR 0033). The sprint report leads with the scorecard.
- [ ] Every scorecard method has a dry-run row before the verifier runs it (ADR 0033 rule 2).
- [ ] C-01..C-06 and ST-013b are "Fixed" in `review-rounds.md` with red→green evidence.

## 10. Risks for this sprint

| Risk | Signal | Response |
|---|---|---|
| OQ-01 still open | No rule numbers by D5 | Ship unofficial (FR-055); remind PO that Sprint 3 planning is the last useful date for official scoring in R1 |
| Correction replay too slow on long matches | IT-02-08 p95 > 1.5 s | Replay only from the changed game onward; snapshot per game (judgment); PE design review |
| Quick Tag effort too high (NFR-036 ≤ 5 s per rally) | Internal timing in E2E-02-02 | Principal-designer adjusts the control bar before the Sprint 5 usability test |
| Responsible-player side rule wrong for some endings | Coach review | Coach decides; BA updates FR-050 note; QA changes the test with an ADR note |
| Design inputs late (aggregate review, API contract, Sprint 2 flows) | Not approved by D2 | The carry-over and ST-041 fill the lanes meanwhile (§3.2); if not approved by D4, the EM re-plans with the PO (judgment) |
| The goal cannot close because carried findings wait on the PO | G02-11 > 0 only from P-items at D8 | The P-list is sent on D1 with dates (retro 1 A5); the EM re-asks at D5 with the count; the verdict stays "not met" rather than relabelling a finding (ADR 0030) |
| Evidence disk near the floor (11 GB free at planning) | `disk-precheck.sh` rc=3 or a live script rc=2 | SRE prunes own images (C-15); PO approves removing old rounds' images (P5) |

## 11. Dependencies

- Sprint 1: rules engine core (ST-020, ST-021), resumable upload (ST-017), setup (ST-016).
- Design: `Match` aggregate design doc; Quick Tag and score-sheet flows.
- Human: OQ-01 (official scoring), OQ-06 (consented fixture footage), OQ-17 (reference profile for NFR-014).

## 12. Demo script (sprint review, 2026-11-13)

1. Open "Saturday doubles" (uploaded in setup; the 6-rally journey of `taglib.JOURNEY_TAGS`). Tag rallies 1-3 by touch, showing the score after each tag and the live-region text.
2. Tag rallies 4-6 using keys only; press `?` to show the key map.
3. Open the score sheet: every rally with server, score before/after, winner, ending; point out "unofficial scoring (rules not yet verified)".
4. Narrow the window to 360 px; show the stacked rows.
5. Change rally 2's winner to Ivy's side; show rallies 2-6 re-scored and "corrected by you"; open the correction history; undo and show the identical sheet.
6. Open the prepared 14-rally game (the conflict fixture of `scripts/measure/taglib.py`, won 11-0 at rally 14); change rally 11 to "won by side A"; show the game won at rally 11 and rallies 12-14 as "needs your decision", not deleted (`@needs-verification`).
7. Click rally 3's link; the video plays from its start time. Show a copied link failing after its TTL (or a tampered link refused).
8. Show the goal scorecard (`docs/sprints/02/goal-scorecard.md`) filled by the verifier, then the test report: Ready scenarios, `@needs-verification` count (≥ 46 rows), mutation score (≥ 85%), golden replay result, Locust baselines, open defects (0).
9. Stretch, only if done: start a match mid-game at "4-6-2" receiving, tag one rally won, show "6-4-1"; a singles game with a two-number call.
10. Ask the PO: OQ-01 status; accept the FR-050 R1 video behaviour (review-log RL-02); OQ-13 (spend ceiling for SPIKE-04 in Sprint 3); any P-item still open.

## 13. Retrospective

- **Date:** 2026-11-13. **File:** `docs/retros/2026-11-13-sprint-02.md` from [`docs/retros/TEMPLATE.md`](../retros/TEMPLATE.md).
- **Format:** Mad/Sad/Glad. **Focus:** domain correctness and the coach verification flow; whether the ADR 0009 split held up.
- Review retro 1 action items first [EP/ENG-15].

## 14. Story specifications and Definition of Ready (business-analyst with engineering-manager, 2026-10-05)

This section adds what `docs/process/definition-of-ready.md` asks for beyond §3, §3.1 and §7, for every **committed** row. Where a card and §3.1 disagree, §3.1 wins and the BA raises the difference with the EM.

- **Feature files:** `tests/features/` (repository root); step modules in `backend/tests/features/`; browser journeys in `web/e2e/sprint-02/`.
- **Priority:** from the FR's MoSCoW priority (all Must, except FR-042 Should, which is stretch). The product-manager confirms at planning (§14.2 item R1).
- **Milestone:** M0 for every story.
- **Design:** `docs/architecture/match-aggregate.md` (Proposed; review D1), `docs/architecture/api-sprint-02.md` (D2), `docs/design/flows-sprint-02.md` (D2), `docs/design/tokens.md`, `docs/design/component-accessibility-checklist.md`.
- **Slices (ADR 0030 rule 4):** every M or L story names its slices below; each is planned at ≤ 400 changed lines and green on its own. A waiver row is written before any commit over 400 lines.

### 14.1 Story cards

#### C-01 Control characters refused at the API boundary (SEC-R6-S1-01, blocker)
- **Value:** As a player, I want a mistyped or pasted address or title to get a clear refusal, so that the service never fails on my input.
- **FR / NFR:** FR-001, FR-021; NFR-058 (0 stack traces), NFR-041 (no 5xx anyone can trigger).
- **Context:** Identity & Players (`players`: `normalise_email`), Match & Scoring (`matches`: title check).
- **Files / interfaces:** `backend/src/racket/players/`, `backend/src/racket/matches/`; `POST /auth/links`, `POST /matches`. Tests: unit, IT-02-10.
- **Out of scope:** Unicode normalisation of nicknames beyond control and surrogate characters (judgment).
- **E2E verification:** G02-03 IT-02-10; a NUL in the address returns 422 `email_invalid` and no row is written.
- **Gherkin:** §14.3.1.

#### C-02 Upload quota holds under parallel creations (PE-R3R-01, major)
- **Value:** As the operator, I want the per-owner open-upload quota to hold under parallel requests, so that one account cannot hold more storage than allowed.
- **FR / NFR:** FR-022; NFR-023 (0 accepted requests beyond a limit).
- **Context:** Capture & Media (`video_ingest`), aggregate `UploadSession`.
- **Files / interfaces:** `backend/src/racket/video_ingest/service.py` (`_check_quota` after the per-owner lock); `POST /matches/{id}/uploads`. Test: IT-02-11.
- **Out of scope:** storage-byte quotas (FR-160, later).
- **E2E verification:** IT-02-11, 8 parallel creations → exactly 3 × 201.
- **Gherkin:** §14.3.2.

#### C-03 Upload server error offers recovery (PD-R3V-01, major; with C-35)
- **Value:** As a player whose upload hit a server error, I want "Try again" and a support reference, so that I can finish without starting over.
- **FR / NFR:** FR-022; NFR-037 (error pattern), NFR-058 (support ref only).
- **Context:** web client, upload panel U-01 (flows-sprint-01 §6).
- **Files / interfaces:** `web/src/components/MatchUpload.tsx`, `web/src/lib/upload/messages.ts`; Vitest and a Playwright case.
- **Out of scope:** retry policy changes in the tus client.
- **E2E verification:** a Playwright case with the PATCH answering 500: "Try again" keeps the transfer, "No video yet" is not shown, the `support_ref` is shown.
- **Gherkin:** §14.3.3.

#### ST-013b Account identity is the stored address (SEC-R3-S1-01 / SEC-R4-S1-01, major)
- **Value:** As a player, I want to keep my account when the service rotates a key, so that my matches never disappear.
- **FR / NFR:** FR-001; NFR-057, NFR-069; ADR 0025, 0027, 0032.
- **Context:** Identity & Players, aggregate `Account`.
- **Files / interfaces:** new migration (`accounts.email` unique, `email_key` not unique), `backend/src/racket/players/`; IT-02-12 (ADR 0032 red tests 1-5).
- **Out of scope:** passkeys (ADR 0031 decision, P2); email change flow.
- **E2E verification:** IT-02-12; G02-01 sign-in still passes.
- **Gherkin:** §14.3.4.

#### ST-026 `Match` aggregate persistence; score as a projection
- **Value:** As a player, I want my tags stored and my score computed from them, so that the score is always consistent with what I tagged.
- **FR / NFR:** FR-049; NFR-075 (rules_version on every stored output; golden replay byte-identical).
- **Context:** Match & Scoring (`matches`), aggregate `Match` with `Game`, `Rally`, `Correction` (match-aggregate §2); imports only the rules Published Language.
- **Files / interfaces:** `backend/src/racket/matches/` (aggregate, projection, repository), migration (`match_games`, `match_rallies`, `match_corrections`; no score column). IT-02-01, IT-02-02 (rollback).
- **Slices:** (1) migration and repository round trip; (2) `project()` with unit tests 1-4 and the property test against `fold`; (3) golden replay test (`golden_replay` marker).
- **Out of scope:** events for Analytics (Sprint 3), per-game cache (only if IT-02-08 fails).
- **E2E verification:** G02-01 step 4; G02-07 golden replay.
- **Gherkin:** §7.3 "Read the match without the video", §7.4 C-01.

#### ST-027 Quick Tag a rally
- **Value:** As a player watching my match, I want to record each rally's outcome in a few taps, so that I get a score sheet without writing anything down.
- **FR / NFR:** FR-050; NFR-012 (a) ≤ 200 ms p95, (b) ≤ 100 ms p95; NFR-028 (48×48 tagging controls); NFR-030 (no dragging); NFR-031 (focus not obscured).
- **Context:** `matches` (command `tag_rally`, If-Match version) and the web client (screen family T).
- **Files / interfaces:** `POST /matches/{id}/games`, `POST /matches/{id}/rallies` (api-sprint-02); `web/src/app/matches/[matchId]/tag/`, `web/src/components/tagging/`, `web/src/lib/tagging/` (reducer with optimistic score and rollback).
- **Slices:** BE (1) command and invariants I1, I5, I6, I7; (2) API route, 409 `stale_match`, IT-02-04. FE (1) tagging reducer (Vitest first); (2) control bar and video wiring; (3) optimistic display and rollback; (4) axe, targets, focus and Playwright.
- **Out of scope:** jumping to the next rally start (FR-087, R2); automatic rally boundaries.
- **E2E verification:** E2E-02-01; G02-01 steps 2-3, 5-6; G02-06 (a)(b).
- **Gherkin:** §7.1; §14.3.5 (tag before the video, stale version).

#### ST-028a Keyboard tagging
- **Value:** As a keyboard user, I want to tag with keys and see the key map, so that I can tag as fast as with touch.
- **FR / NFR:** FR-051; NFR-034 (keyboard-only flows 100%).
- **Context:** web client (screen family K).
- **Files / interfaces:** `web/src/lib/tagging/keymap.ts` (store, Vitest first: turning shortcuts off disables single keys only), `web/src/components/tagging/KeyMapDialog.tsx`.
- **Out of scope:** remapping (ST-028b, stretch).
- **E2E verification:** E2E-02-02.
- **Gherkin:** §7.1 "Keyboard only", "Show the key map", "Turn single-key shortcuts off".

#### ST-029 Score call and polite announcement
- **Value:** As a screen-reader user, I want to hear the rally and the new score after each tag, so that I know the tag was recorded without looking.
- **FR / NFR:** FR-048 (call format provisional, `@needs-verification`); NFR-034 (announcements).
- **Context:** web client; the call text comes from the server sheet.
- **Files / interfaces:** `web/src/components/tagging/ScoreAnnouncer.tsx` (one polite live region).
- **Out of scope:** spoken audio output.
- **E2E verification:** E2E-02-03.
- **Gherkin:** §7.2.

#### ST-030 Score sheet with the "unofficial scoring" label
- **Value:** As a player, I want a complete text record of my match, so that I can read it without the video.
- **FR / NFR:** FR-049, FR-055; NFR-011 (≤ 2.0 s warm), NFR-029, NFR-033, NFR-034 (reflow 320 px; markers not by colour alone).
- **Context:** `matches` (GET score sheet) and the web client (screen family S).
- **Files / interfaces:** `GET /matches/{id}/score-sheet`; `web/src/app/matches/[matchId]/sheet/`, `web/src/components/score-sheet/`.
- **Slices (FE M):** (1) semantic table and label; (2) stacked rows at 360 px and markers; (3) axe and viewport matrix.
- **Out of scope:** export or print (later).
- **E2E verification:** E2E-02-01 sheet step; G02-01 step 4; G02-06 (d); G02-10 (d).
- **Gherkin:** §7.3.

#### ST-031 Undo and correction audit
- **Value:** As a player, I want to undo any change and see what I changed, so that a mis-tap never costs me the match.
- **FR / NFR:** FR-052; NFR-047 (fail closed), NFR-069 (pseudonymous logs).
- **Context:** `matches` (commands `correct_rally`, `withdraw_rally`, `undo`; table `match_corrections` append-only).
- **Files / interfaces:** `PATCH /matches/{id}/rallies/{rally_id}`, `POST /matches/{id}/undo`, `GET /matches/{id}/corrections`; `web/src/components/score-sheet/CorrectionHistory.tsx` (screen family H). IT-02-03, IT-02-09.
- **Slices (BE M):** (1) correction and withdrawal commands with the audit row; (2) undo stack; (3) DB trigger and REVOKE (IT-02-03).
- **Out of scope:** redo (match-aggregate §8 Q4).
- **E2E verification:** E2E-02-06; G02-01 steps 7-8.
- **Gherkin:** §7.4 "Undo and correction history".

#### ST-032 Corrections replay the score; conflicting rallies kept (a)
- **Value:** As a player, I want a correction to re-score every later rally at once, and never lose a rally, so that the sheet stays right after I fix a call.
- **FR / NFR:** FR-053 (a): C-01, C-04 Ready; C-02, C-03 `@needs-verification`; NFR-013 (≤ 1.5 s p95, 3-game match).
- **Context:** `matches` (projection marks `needs_decision`; command `resolve`).
- **Files / interfaces:** projection, `resolve` command; UI marker "needs your decision" in the score sheet. IT-02-02, IT-02-08.
- **Slices (BE M):** (1) projection marks for C-02/C-03; (2) `resolve` command; (3) IT-02-08 timing.
- **Out of scope:** correction consequences preview (ST-033, stretch).
- **E2E verification:** G02-01 steps 7, 9; G02-02 (a).
- **Gherkin:** §7.4 "Corrections re-score later rallies".

#### ST-037 Jump to the video moment with short-lived media URLs
- **Value:** As a player reading the score sheet, I want each rally to open the video at that moment, so that I can check what happened.
- **FR / NFR:** FR-027; NFR-014 (≤ 1.5 s p95, reference profile), NFR-055 (TTL ≤ 15 min, 0 session tokens in URLs), NFR-069 (no signed URLs in logs).
- **Context:** `video_ingest` (`MediaUrlPolicy`) via the `matches` public API; web client (screen family V).
- **Files / interfaces:** `GET /matches/{id}/rallies/{rally_id}/media`; `web/src/components/score-sheet/RallyVideoLink.tsx`; SRE-MEDIA config. IT-02-05, IT-02-06.
- **Out of scope:** clip extraction; thumbnails.
- **E2E verification:** E2E-02-04; G02-01 step 10; G02-06 (c).
- **Gherkin:** §7.6 "Jump to the video moment"; §14.3.6.

#### ST-039 E2E journey v1 and performance baseline
- **Value:** As the team, we want the tagging journey and its timings measured live every sprint, so that a regression shows before the R1 review.
- **FR / NFR:** NFR-010, NFR-012, NFR-013, NFR-014, NFR-017 (baselines; gates from the R1 review except where §8 gates them now).
- **Files / interfaces:** `web/e2e/sprint-02/journey.spec.ts` (E2E-02-01), `web/e2e/sprint-02/timing.spec.ts`; Locust file under `backend/tests/perf/`; CI job (SRE).
- **Slices (QA M):** (1) journey spec; (2) timing spec with attachments; (3) Locust scenario and CI job (SRE S).
- **Out of scope:** WebKit timings (CI only).
- **E2E verification:** G02-05, G02-06, G02-04.

#### ST-040 Gold-set label schema, manifest v1 and capture protocol
- **Value:** As the ML engineer, I want a label schema and a consented capture protocol, so that the gold set can start the day footage is allowed.
- **FR / NFR:** FR-151; OQ-06; ADR 0023 note (consent forms valid for US and AU participants; legal review before real users, NFR-070).
- **Files / interfaces:** `docs/data/`, `backend/src/racket/dataset/` (manifest v1 schema and checks).
- **Out of scope:** collecting real-match footage (blocked until the legal review).
- **E2E verification:** `racket-manifest-check` on manifest v1 in CI.

#### ST-041 Golden tables written first
- **Value:** As the team, we want the provisional rows as executable tables before the code, so that the engine is tested against the documented rows.
- **FR / NFR:** NFR-001 (≥ 46 rows: 16 SOD, 6 F, 12 SOS, 8 M, 4 C).
- **Files / interfaces:** `tests/features/corrections_replay.feature`, `mid_game_start.feature`, `side_out_singles_provisional.feature`; step modules. Rows of stretch stories carry `red_until(story=...)`.
- **E2E verification:** G02-07.

#### QA-ACC, QA-FUZZ, W-01, SRE-MEDIA, SRE-SMOKE, DR-01
- Defined in §3 (planning additions and design carry-over). Each names its files, its test or evidence and its reviewer there. QA-FUZZ adds rule L11 to `docs/process/testing-strategy.md` §1.

### 14.2 Definition of Ready check (2026-10-05)

Key: ✓ met (evidence in this file or a linked one); **R** pending, with owner and day below; — not applicable.

| DoR item | C-01 | C-02 | C-03 | 013b | 026 | 027 | 028a | 029 | 030 | 031 | 032 | 037 | 039 | 040 | 041 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ID, value statement | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PM-assigned priority | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 |
| FR/NFR and milestone linked | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Out of scope listed | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Declarative Gherkin incl. negative cases | ✓ §14.3 | ✓ §14.3 | ✓ §14.3 | ✓ §14.3 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — (journey) | — | ✓ |
| NFRs measurable | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| QA agrees testable, levels named | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 |
| Domain truth verified, or (a) with no rule claim | — | — | — | — | ✓ (projection over any preset) | ✓ (a); R5 for responsible-player side | — | ✓ `@needs-verification` | ✓ unofficial label | — | ✓ (a) C-01/C-04; C-02/C-03 `@needs-verification`, R5 | — | — | — | ✓ `@needs-verification` |
| Glossary terms used / added | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Context and aggregates named | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Design doc / ADR approved | — | — | ✓ flows §6 | ✓ ADR 0032 | R3 | R3, R4 | — | — | R4 | R3, R4 | R3 | R4 | — | — | — |
| UI flow and all states; WCAG, HAX | — | — | ✓ U-01 | — | — | R6 | R6 | R6 | R6 | R6 | R6 | R6 | — | — | — |
| Design review held | — | — | R7 (DR-01) | — | R3 | R7 | R7 | R7 | R7 | R7 | R7 | R7 | — | — | — |
| Threat-model notes attached | R8 | R8 | — | ✓ ADR 0032 | — | — | — | — | — | R8 | — | R8 | — | R8 (consent) | — |
| Sized; PRs ~100 lines; slices named | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Dependencies available | ✓ | ✓ | ✓ | ✓ | ✓ (ST-020, 021) | ST-026 | ST-027 | ST-027 | ST-026 | ST-026 | ST-031, ST-041 | ST-027, SRE-MEDIA | ST-030 | ✓ | ✓ |
| Files, interfaces, E2E step named | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

| # | Pending item | Owner | Due |
|---|---|---|---|
| R1 | Confirm the priorities (all Must; the stretch order in §3) and the re-plan with the PO (P4) | product-manager | D1 |
| R2 | Agree that every criterion in §7 and §14.3 is testable and name the level | senior-qa-engineer | D1 (before QA-ACC) |
| R3 | Design review of `match-aggregate.md` held and the doc "Accepted" | principal-engineer and reviewers | D1 |
| R4 | `api-sprint-02.md` written and reviewed; `tagcontract.py` aligned | principal-engineer | D2 |
| R5 | match-aggregate §8 Q1 and Q2 answered | pickleball-domain-coach | D2 |
| R6 | `flows-sprint-02.md` with all states, HAX and WCAG checklists | principal-designer | D2 |
| R7 | DR-01 held (Sprint 1 P7), then the Sprint 2 flows reviewed | principal-designer with coach, FE, BA, security, PM | D1, D3 |
| R8 | Threat notes: C-01/C-02 fuzz and quota, ST-031 audit trail, ST-037 media URLs, ST-040 consent (US and AU) | security-privacy-engineer | D2 |

**Verdict (business-analyst and engineering-manager, 2026-10-05):** every BA-owned DoR item is met for the committed rows. C-01, C-02, ST-013b and ST-041 are **Ready now** once R1 and R2 are ticked on D1; they are the first work of their lanes. ST-026..ST-037 are **Ready on condition** of R3-R8 by D2-D3; no code for them is committed before their conditions are ticked in this table (a dated note per tick). Rule-dependent rows stay `@needs-verification` and count toward no Must FR (QD-QG-P5).

### 14.3 Additional Gherkin (carry-over rows and negative cases)

```gherkin
# tests/features/input_robustness.feature
@M0 @story-C-01 @nfr-058
Feature: Input that is not text is refused cleanly
  Rule: Control characters never break the service

    Scenario Outline: 14.3.1 Control character in a field
      Given Ivy is on the "<form>" form
      When she submits a <field> containing a "<character>" character
      Then she is told the <field> is not valid
      And nothing is saved
      Examples:
        | form      | field         | character      |
        | sign-in   | email address | NUL            |
        | sign-in   | email address | line separator |
        | new match | title         | NUL            |
        | new match | title         | lone surrogate |
```

```gherkin
# tests/features/upload_quota.feature
@M0 @story-C-02 @nfr-023
Feature: Upload quota under parallel requests
    Scenario: 14.3.2 Eight uploads started at the same moment
      Given Ivy may have 3 unfinished uploads at once
      When 8 uploads are started for her at the same moment
      Then exactly 3 are accepted
      And the other 5 are refused with a reason
```

```gherkin
# tests/features/upload_recovery.feature
@M0 @story-C-03
Feature: Recover from an upload server error
    Scenario: 14.3.3 The server fails during the upload
      Given Ivy's upload is at 40%
      When the server answers with an error
      Then she sees "Try again" and a support reference
      And she does not see "No video yet"
      And trying again continues from 40%
```

```gherkin
# tests/features/account_identity.feature
@M0 @story-ST-013b @nfr-057
Feature: The account follows the address
    Scenario: 14.3.4 The service rotates its key
      Given Ivy has an account with 2 matches
      When the service rotates its sign-in key
      And Ivy signs in with the same address
      Then she sees her 2 matches

    Scenario: Two addresses that share a key
      Given two different addresses produce the same key
      When both sign in
      Then each gets an account of its own
```

```gherkin
# tests/features/quick_tag.feature (additions)
@M0 @story-ST-027 @nfr-060
  Rule: Tagging needs a received video and the latest version

    Scenario: 14.3.5 Tag before the video is received
      Given Ivy's match has no video yet
      When she tries to tag a rally
      Then she is told to wait until the video is received
      And no rally is saved

    Scenario: Two devices tag at once
      Given Ivy tags the same match on her phone and her laptop
      When both record rally 8 at the same moment
      Then one tag is saved
      And the other device is told the match changed and shows the latest score
```

```gherkin
# tests/features/evidence_deep_link.feature (addition)
@M0 @story-ST-037 @nfr-055
    Scenario: 14.3.6 A changed video link is refused
      Given Ivy has a video link for rally 3
      When the link is changed by hand
      Then the video does not play
```

## 15. Build lanes (engineering-manager, 2026-10-05; ADR 0010: ≤ 5 lanes, ≤ 2 streams per role, disjoint directories)

| Lane | Role | Stories (in order) | Directories (write) |
|---|---|---|---|
| L1 backend | senior-backend-engineer | C-01, C-02, ST-013b, ST-026, ST-027 (API), ST-030 (API), ST-031, ST-032, ST-037 (API); stretch ST-035, ST-034, ST-038, BE minors | `backend/src/racket/` (except `dataset/`), `backend/src/racket/migrations/`, `backend/tests/unit/{matches,players,video_ingest,sports}/` (unit tests of its own code) |
| L2 frontend | senior-frontend-engineer | C-03 (with C-35), ST-027 (UI), ST-028a, ST-029, ST-030 (UI), ST-031 (UI), ST-032 (UI), ST-037 (UI), WebKit product fixes from W-01; stretch ST-028b, ST-034 (UI), FE minors | `web/src/`, `web/tests/` (Vitest of its own code) |
| L3 quality | senior-qa-engineer | QA-FUZZ, C-04, ST-041, QA-ACC, C-22, C-31, C-32, C-34, ST-039 (journey and timing specs), scorecard dry-runs, C-06 | `tests/features/`, `backend/tests/{features,integration,regression,oracle,perf,support}/`, `web/e2e/`, `docs/process/testing-strategy.md`, `docs/sprints/02/test-change-requests.md` |
| L4 platform | sre-devops-engineer | C-05, C-15, C-23, W-01, C-11, C-12, C-13, C-18, C-29, SRE-MEDIA, ST-039 (Locust in CI), SRE-SMOKE | `infra/`, `.github/`, `scripts/ci/`, `scripts/dev-*.sh`, `scripts/disk-precheck.sh`, `docs/ops/`, `docs/sprints/02/{smoke,ci-status}.md` |
| L5 data | senior-ml-cv-engineer | ST-040; ST-025 when P3 is answered | `backend/src/racket/dataset/`, `backend/tests/unit/dataset/`, `docs/data/`, `fixtures/` |

- **Disjointness:** L1 writes production code under `backend/src/racket/` and only the unit-test folders of its own contexts; L3 owns every acceptance, integration, regression and E2E test. L5 owns `dataset/` only. A lane that needs a file in another lane's directory asks that lane (or the EM routes it).
- **Docs roles** (no lane, no code): principal-engineer (`docs/architecture/`, `scripts/measure/tagcontract.py` with the contract), principal-designer (`docs/design/`), business-analyst (`docs/requirements/`), security-privacy-engineer (`docs/security/`), pickleball-domain-coach (`docs/domain/`), product-manager and engineering-manager (`docs/sprints/`, `docs/decisions/`, `docs/retros/`).
- **Streams per role:** BE 2 (`matches`; then `players`/`video_ingest`/`sports`), FE 2 (tagging; score sheet and video), QA 2 (backend tests; browser tests), SRE 2 (CI; Compose and TLS), ML 1.
