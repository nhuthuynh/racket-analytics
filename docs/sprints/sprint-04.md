# Sprint 4: Runnable R1 prototype (rules-only plan and drill library), then R1 privacy and quotas behind flags

- **Dates:** Mon 2026-11-30 → Fri 2026-12-11
- **Planning:** 2026-10-17 (compressed session, like Sprints 1-3; the planned dates are kept for the review and the retro) · **Sprint review:** 2026-12-11 · **Retrospective:** 2026-12-11
- **Retro file:** `docs/retros/2026-12-11-sprint-04.md` from [`docs/retros/TEMPLATE.md`](../retros/TEMPLATE.md). Format: **4Ls (Liked, Learned, Lacked, Longed for)**. Focus area: **did slicing at planning (B4) and the merge discipline (ADR 0050) hold, and is the prototype usable by the PO?**
- **Status:** Planned at Sprint 4 planning on **2026-10-17** by the engineering-manager with the product-manager, principal-engineer, business-analyst and senior-qa-engineer (ticket PLAN-04, branch `s04/plan` from `origin/main` at `c170ef0`). The roadmap outline (roadmap §6 "S4") is replaced by this file and ADR 0051.
- **Delivery:** every ticket is its own branch `s04/<ticket-id-lowercase>` and its own PR into `main` (PO rule 2026-10-07, ADR 0039). No sprint branch. Merges only through `merge_ready.py`, one PR at a time, by the gated merge step (ADR 0050). Ticket branches are named in §15 and created from planning (ADR 0047 rule 4).
- **Goal scorecard (PO standing rule):** [`docs/sprints/04/goal-scorecard.md`](04/goal-scorecard.md), 12 metrics G04-01..G04-12, each measured live on the local stack; human-only items in its "not met: waiting on P-n" table (PO P12).
- **Shared sprint files:** `docs/sprints/04/review-rounds.md` (findings), `test-change-requests.md` (TCR rows), `blockers.md` (PO list), and `decision-log.md`, `status.json`, `progress.md` (created by RETRO-04). **Ticket PRs never edit** `decision-log.md`, `blockers.md`, `status.json` or `progress.md`; each ticket writes its small decisions in `docs/sprints/04/decisions/<TICKET-ID>.md` (one file per ticket, created by that ticket's PR). Only RETRO-04 consolidates.
- **Related ADRs:** 0003 (rallies-lost unit), 0005 (Wilson, minimum n; PM-4), 0006 (deletion and retention windows), 0009 (rules readiness), 0010 (capacity), 0014 (fail closed), 0022/0030 (PR size), 0029 (https dev stack), 0033, 0037, 0039, 0044 (`coach-reviewed` vs `verified`), 0046 (red-first E2E), 0047 (gate phase), 0050 (merge discipline), **0051 (this sprint's order, flags, interim values, out-of-scope spikes, roadmap renumbering)**. Citation prefixes: working-agreement §0.

## 0. Planning record (2026-10-17)

### 0.1 Preconditions

| Precondition | Status at planning | Consequence |
|---|---|---|
| **CI on `main` green (CI FIRST, PO 2026-10-08)** | **Met.** `actions_list list_workflow_runs branch=main`: run 39015002522 (`schedule`, `c170ef0`) → success; last push run 38894723692 (`d8b0a34`, PR #86) → success. Open PRs: none (`list_pull_requests state=open` → `[]`) | No CI-fix ticket is needed first. If `main` turns red at any point, the next ticket is a `ci_fix` ticket that pre-empts every feature ticket (§3.6) |
| Sprint 3 goal ledger | **2 open:** `python3 scripts/measure/open_defects.py docs/sprints/03/review-rounds.md` → rc 1, `open 2`: PD-R1S3-01 with QA-R3S3-06 (blocker group; the chair's DR-03 "Held" record and `flows-sprint-03.md` line 3) and EM-PR27-01 (major; a senior verdict on PR #27's merged head `52582fd`). The PO brief names "PE-PR24-01"; that row is already **Fixed** (FIX-03-2b; scorecard §12.3), and EM-PR27-01 is the second open row | Ticket **C4-G12** closes both and confirms PE-PR24-01 stays Fixed |
| Coaching design and Sprint 4 API contract (plan, weakness, done/swap, privacy, quotas) | **Not met:** only the context canvas `docs/architecture/contexts/coaching.md` | Gate ticket **PE-4** first (ADR 0047 rule 2) |
| Flows for the plan screens (P-) and privacy screens (A- age, R- retention/consent, Q- quota) with every state, HAX and WCAG checklists; DR-04 decider cells | **Not met:** last flows file is `flows-sprint-03.md` | Gate ticket **PD-4**. No Sprint 4 UI ticket starts before PD-4 is merged |
| Threat notes for plans (BOLA, offline replay) and FR-003/008/009/160, NFR-022/023 | **Not met** | Gate ticket **SEC-4** |
| Weakness catalogue (Quick Tag ending → weakness → target metric, serve/receive split), the R1 targetable metrics, warm-up rule, drill review checklist | **Not met:** the metric dictionary has AN-01..AN-07 (`coach-reviewed`); no weakness catalogue | Gate ticket **COACH-4** |
| ADR 0005 (Wilson 95%, n < 20 or width > 30 points) | **Proposed** (PM-1 carried from Sprint 3) | Gate ticket **PM-4**; FR-123 reads the low-sample rule from the metric dictionary (ADR 0041) either way |
| Drill library | Schema v1, lint and lock exist (ST-053); `content/drills` holds 3 `pb.fixture.*` drills | ST-058a..c author ≥ 20 drills; ST-059 adds the coverage check |
| OQ-05, OQ-06, OQ-07, OQ-08, OQ-13 | **Accepted by the PO on 2026-10-05** (ADR 0023 decision table; `open-questions.md` summary table: "Accepted"). Still open are only: the NFR-070 legal review (US + AU) of the OQ-05/06/07 wording and windows; the OQ-13 budget amount (P8); the coach's verification of the side-out rule behind OQ-08 (after OQ-01, P7) | Sprint 4 builds the accepted values (ADR 0051 rule 4) behind default-off flags, because no real user may see them before the legal review (P16). The PO is not asked again |
| Disk | **9.5 GB free** on `/` (`df -h /`), below the 10 GB floor | Blocker row 2 (P5 prune). Every live step runs `bash scripts/disk-precheck.sh` first |

### 0.2 Product-owner decisions applied

- **CI FIRST (2026-10-08)**, now recorded in `po-input-2026-10-05.md` (addendum 2026-10-17, as relayed). CI green on `main` and on every PR before any merge; a red `main` is fixed first; the runner enforces the merge gate on the exact head SHA.
- **Sprint 4 brief and session goal (2026-10-17, as relayed):** "resume Sprint 4 and try to complete the MVP so it can run as a prototype". Order: (0) CI first; (1) carry-overs; (2) prototype spine; (3) privacy and quotas behind flags. SPIKE-02/03/05 out of scope. Human-only items never ticketed. Slice ≤ 400 changed lines at planning. ADR 0047 gate day and ADR 0050 merge discipline apply.
- **Separation of duties (orchestrator, 2026-10-09):** only the gated merge step merges; only the EM/QA PR-policy step adds or removes `size-waiver` and `qa-approved-test-change`. No ticket brief includes either.
- **One PR per ticket, TDD + DDD, three test levels, two verdicts (PO 2026-10-07; P13).** Unchanged.
- **Goals measured live; human-only items as "not met: waiting on P-n" (P12).** §9.1 and scorecard §5.
- **Rulebook later (OQ-01, P7).** Scoring stays `PROVISIONAL-UNVERIFIED`; stats and the plan page carry the "unofficial scoring" notice once before the first card (as stats, DR-03 R3-3).
- **OQ-05..OQ-08 accepted (2026-10-05, ADR 0023); built as accepted, not asked again.** OQ-05: account holders 18+ (FR-003), the capture guide asks not to upload matches with minors. OQ-06: training use is a separate opt-in, off by default and revocable (FR-009); a revoked match leaves all future gold-set versions, frozen historical versions are not edited and retire at their next scheduled refresh. OQ-07: ADR 0006 windows as interim defaults; review video by the user's setting, default 90 days. OQ-08: weaknesses ranked by rallies lost per game, split serve/receive (ADR 0003). Open parts only: the legal review (P16), the budget amount (P8), the side-out rule verification (P7).
- **Jurisdictions US + AU (OQ-05 part).** The interim FR-003 wording names neither law as satisfied; NFR-070 legal review stays a human gate before any real-user beta.
- **HTTPS dev stack, no insecure-cookie flag (ADR 0029).** Every live method runs over https through `web-tls`.
- **Go port in S6.** Every new behaviour is pinned by a language-independent test (Gherkin, HTTP-level IT, Playwright, live scorecard) for the port to reuse.
- **Repository is public (P10 open).** No footage of people, no labels of real people, no secrets in git.

### 0.3 Retro 3 actions applied (`docs/retros/2026-11-27-sprint-03.md` §7)

| Action | How this plan applies it |
|---|---|
| B1 merge only through `merge_ready.py`; post-merge audit; PR #27 senior verdict | Merge step per ADR 0050 (orchestrator). The EM status step runs `merged_verdict.py --pr N --role principal-engineer --role <senior role>` on every merged Sprint 4 PR (G04-12 b). PR #27's senior-backend verdict is part of **C4-G12** |
| B2 DR-03 held; PD-R1S3-01 Fixed; demo step 10 re-run | **C4-G12** |
| B3 verification PRs merged before the next round; `reconcile_due.py` VM-R3-02; parseable verifier ids | **C4-RECON** (tool fix, red first); **VERIFY-04** delivers one merged PR per round with ids in the ledger format (ADR 0050 rules 4-5) |
| B4 slice ≤ 400 changed lines at planning, from unbuilt work | Every ticket in §3 is sized ≤ 400 counted changed lines (tests included). Success measure: ≤ 20% of Sprint 4 PRs carry `size-waiver`; median PR ≤ 300 lines (reported by RETRO-04) |
| B5 the R3-IN-1 `Red:` check | **C4-RED** (red-first tested, in `ci-gate`); lands in the first wave so later tickets are checked by it |

### 0.4 Goal items that depend on a human input (ADR 0037 rule 3; PO P12 option b)

These are not goal metrics. Each is a sprint-DoD row "not met: waiting on P-n" (§9.1) until the human supplies it.

| Item | Waits on | Need-by | What the team ships meanwhile |
|---|---|---|---|
| Human coach review of the starter drills (`verified`) | **P15** | 2026-12-11 | Drills at `coach-reviewed` by the coach agent (ADR 0044 analogue), `@needs-verification`, plan-page notice (interim wording) |
| Legal review (NFR-070; US + AU) of the age wording and footage notice (OQ-05), the consent text (OQ-06) and the retention windows (OQ-07). The values themselves are PO-accepted (ADR 0023); only their legal adequacy is open | **P16** | before any real-user beta (none in Sprint 4) | Accepted values behind default-off flags; user-facing texts marked "interim, pending legal review (NFR-070)" |
| Coach verification of the side-out rule behind the serve/receive split (OQ-08's open part; after OQ-01) | **P7** | 2026-11-16 (OQ-01) | Split shipped `@needs-verification`; plan page carries the "unofficial scoring" notice |
| Storage quota size; monthly budgets for billing alerts; GPU budget | **P8** (OQ-13) | 2026-12-11 | 20 GB (judgment) as a setting; budgets as settings; SPIKE-03 not ticketed |
| Screen-reader pass of Sprint 1-4 screens (NFR-027 b) | **P6** | overdue | Automated axe and keyboard checks (G04-08) |
| Repository visibility | **P10** | sooner is safer | Nothing private in git |
| Footage bucket provider | **P11** | before any footage of people | SPIKE-02/05 not ticketed |

### 0.5 What changed from the outline (roadmap §6 "S4")

- **Order:** prototype spine first; privacy and quotas after it, behind flags (ADR 0051 rule 1).
- **Removed:** SPIKE-05, SPIKE-03 (start), SPIKE-02 (start): blocked on P11/OQ-06 and P8/OQ-13 (ADR 0051 rule 6).
- **Added:** the Sprint 3 carry-over (C4-*), `make demo` with a plan and the README prototype walkthrough (ST-064, ST-066), the live goal harness (QA-HARNESS-4a/b), a config scaffold for the flags (ST-067).
- **Changed:** "≥ 20 coach-reviewed drills" means `coach-reviewed` by the coach agent; `verified` needs P15.

## 1. Sprint goal

1. **A player can run the whole R1 journey on a local stack as a prototype:** `make up` then `make demo` gives a demo user with a tagged match, its score sheet, its stats and a generated 2-week plan; a fresh user can do the same by hand (upload → Quick Tag → score sheet → stats → plan).
2. **The plan is rules-only, deterministic and honest:** weaknesses ranked by rallies lost per game, split serve/receive (ADR 0003, PO-accepted; the side-out part `@needs-verification` until P7); the 2-week plan fits the player's time per session and per week, players and equipment, starts every session with a warm-up, gives no drill more than 40% of a session, uses only reviewed library drills; every drill cites metric, value, n and the evidence rallies; a low-sample plan says so with its n; the code-grader eval passes at pass^3 = 100%.
3. **A starter library of ≥ 20 drills** passes the lint and the coverage matrix in CI (content `needs-verification` until P15).
4. **A player can follow the plan:** mark a session done offline (synced later, idempotent) and swap a drill with "Not for me" for another that targets the same metric and still fits.
5. **R1 privacy and quotas exist behind default-off flags with interim wording:** age confirmation and footage notice, video retention choice, training-data consent, match-creation rate limit and storage quota; billing alert rules at 50/80/100%.
6. **The Sprint 3 carry-over is closed first** (G03-12 rows, `extra_ca`, T-AC-5, Locust on stats/evidence, the `Red:` check, `reconcile_due` fix); CI is green on `main` at the close; no blocker or major is open.

## 2. Capacity (ADR 0010)

- **Lanes:** BE (senior-backend-engineer, 2 streams), FE (senior-frontend-engineer), QA (senior-qa-engineer), SRE (sre-devops-engineer), ML (senior-ml-cv-engineer). Docs and gate roles: principal-engineer, principal-designer, security-privacy-engineer, pickleball-domain-coach, product-manager, business-analyst, engineering-manager (dated tickets, no units, except the coach's drill content which is sized for review effort).
- **Load factor:** 0.8 (retro 3 §8: implemented ratio 0.919, DoD-done 0.849; keep 0.8). Capacity per stream 16 × 0.8 = 12.8 units.
- **Sizes:** XS 0.5 · S 1 (≈ 200 counted changed lines incl. tests) · M 2 (≈ 300-400 lines). Nothing larger than M: every ticket ≤ 400 lines (B4).

| Lane | Tickets (units) | Planned | Capacity |
|---|---|---|---|
| BE | ST-055 (2), ST-056 (2), ST-057 (1), ST-061a (2), ST-061b (2), ST-062 (2), ST-067 (1), ST-068a (1), ST-069 (2), ST-072a (2) | 17 | 25.6 (2 streams) |
| FE | ST-063a (2), ST-063b (2), ST-063c (2), ST-068b (1), ST-071 (2), ST-072b (1) | 10 | 12.8 |
| QA | C4-TAC5 (0.5), C4-RECON (1), ST-059 (1), ST-065 (2), QA-HARNESS-4a (2), QA-HARNESS-4b (1), VERIFY-04 (1) | 8.5 | 12.8 |
| SRE | C4-CA (1), C4-LOCUST (1), C4-RED (1), ST-064 (1), ST-066 (0.5), ST-073 (1) | 5.5 | 12.8 |
| ML | ST-060 (2), ST-070 (2) | 4 | 12.8 |
| Coach content | ST-058a (1), ST-058b (1), ST-058c (1) | 3 | dated |
| **Total** | 41 tickets: 34 sized, plus 7 without units (5 gate tickets, C4-G12, RETRO-04); PLAN-04 is this PR | **48 units** | 77 |

The ~29 units of headroom are the review loop (1-3 rounds per PR in Sprint 3), the CI-first reserve (Sprint 3: 18 of 71 PRs were CI work) and the C4-MIN minors (§3.1). No stretch stories are committed; ST-033..ST-036 stay in the backlog.

## 3. Committed backlog

Ticket ids: `C4-*` carry-over, `PE-4`/`PD-4`/`SEC-4`/`COACH-4`/`PM-4` gate tickets (ADR 0047 rule 2), `ST-055..ST-073` stories, `QA-HARNESS-4a/b` measurement, `VERIFY-04`, `RETRO-04`. Every ticket: its own PR; principal-engineer + the named senior reviewer; tests first and seen failing (negative case first); `docs/sprints/04/decisions/<ID>.md`.

### 3.1 Carry-over from Sprint 3 (first wave, parallel with the gates)

| ID | Title | Owner | Senior reviewer | Size | FR/NFR / source |
|---|---|---|---|---|---|
| C4-G12 | Close the G03-12 ledger rows: DR-03 "Held" record and `flows-sprint-03.md` line 3 (PD-R1S3-01, QA-R3S3-06); senior-backend verdict on PR #27 head `52582fd` (EM-PR27-01); Fixed rows; `demo_test_report.py` rc 0 | principal-designer | senior-frontend-engineer | docs | retro 3 B1, B2; sprint-report §9 |
| C4-CA | Optional `extra_ca` build secret in `infra/compose.yaml` so `make up` builds behind a TLS-intercepting proxy; default off; README | sre-devops-engineer | senior-backend-engineer | S | VR3-S3-01 |
| C4-TAC5 | T-AC-5: a re-created account has no labeller role (SEC-S3-TM-07) | senior-qa-engineer | senior-backend-engineer | XS | ADR 0045; retro 3 A4 |
| C4-LOCUST | ST-054 SRE half: Locust on GET stats and evidence in CI (`perf-baseline`), gate on NFR-010 dashboard read p95; VR3-S3-02 G03-05 dry-run row | sre-devops-engineer | senior-qa-engineer | S | ST-054; NFR-010, NFR-041 |
| C4-RED | R3-IN-1 `Red:` check in `ci-gate`: a story commit adding `backend/src` or `web/src` code without a `Red:` body line or an earlier test-only commit in the PR fails | sre-devops-engineer | senior-qa-engineer | S | retro 3 B5 (A5) |
| C4-RECON | `reconcile_due.py` marks a merged ticket that changes an open row's evidence as due (VM-R3-02); verifier ids parse in `measurelib._FINDING_ID`; QA-RETRO03-03 docstring | senior-qa-engineer | sre-devops-engineer | S | retro 3 B3 |

**C4-MIN (not ticketed; review-loop reserve):** PE-PR26-01; PE-ST043-03/-04/-06/-07/-08; VM-R1-02, VM-R2-01; PE-R3S3-06/-07/-08; SEC-R3S3-04; SEC-S3-TM-03/-04/-09/-10; PD-R3S3-02; PD-FL3-02/-03; VR2-S3-03; VR3-S3-03; PE-S2-R3-08. Each owner closes a minor in a ticket that already touches the same file, with a Fixed row in the Sprint 3 ledger; RETRO-04 carries the rest. No minor counts toward G04-12.

### 3.2 Gate tickets (ADR 0047 rule 2: first, in parallel, before any build ticket that depends on them)

| ID | Title | Owner | Senior reviewer | Output |
|---|---|---|---|---|
| PE-4 | Coaching design and Sprint 4 API contract | principal-engineer | senior-backend-engineer | `docs/architecture/coaching-plan.md`, `docs/architecture/api-sprint-04.md`; context-map update |
| PD-4 | Flows for P- (plan), A- (age), R- (retention, consent), Q- (quota) with every state; DR-04 decider cells | principal-designer | senior-frontend-engineer | `docs/design/flows-sprint-04.md` |
| SEC-4 | Threat notes for plans and R1 privacy/quotas; BOLA matrix additions | security-privacy-engineer | senior-backend-engineer | `docs/security/threat-notes-sprint-04.md` |
| COACH-4 | Weakness catalogue, R1 targetable metrics, warm-up rule, drill review checklist and coverage scope | pickleball-domain-coach | senior-ml-cv-engineer | `docs/domain/weakness-catalogue.md`, `docs/domain/drill-review-checklist.md` |
| PM-4 | ADR 0005 accept or amend (PM-1); interim wording register for the four flags (texts pending legal review, P16) | product-manager | senior-qa-engineer | ADR 0005 status; `docs/requirements/interim-wording-sprint-04.md` |

### 3.3 Prototype spine (FR-120..FR-124, FR-141, NFR-005a, NFR-019; QD §7)

| ID | Title | Owner | Senior reviewer | Size | FR/NFR | Depends on |
|---|---|---|---|---|---|---|
| ST-055 | Weakness ranking by rallies lost per game, split serve/receive, side-out part `@needs-verification` | senior-backend-engineer | senior-ml-cv-engineer | M | FR-120; ADR 0003 | PE-4, COACH-4 |
| ST-056 | `TrainingPlan` aggregate and rules-only assembly (QD-PL-01..03) | senior-backend-engineer | senior-qa-engineer | M | FR-121 | PE-4, COACH-4 |
| ST-057 | Every assignment cites metric, value, n, evidence rallies; limited-data plan (QD-PL-04, PL-06) | senior-backend-engineer | senior-qa-engineer | S | FR-122, FR-123 | ST-055, ST-056, PM-4 |
| ST-058a | Starter drills 1-7 (warm-ups; serve: AN-01, AN-05) | pickleball-domain-coach | senior-qa-engineer | S | FR-141 | COACH-4 |
| ST-058b | Starter drills 8-14 (receive: AN-02; unforced errors: AN-04) | pickleball-domain-coach | senior-qa-engineer | S | FR-141 | ST-058a |
| ST-058c | Starter drills 15-21+ (ending mix: AN-07; fill every empty coverage cell) | pickleball-domain-coach | senior-qa-engineer | S | FR-141 | ST-058b |
| ST-059 | Coverage-matrix check in CI (QD-DR-05) | senior-qa-engineer | senior-backend-engineer | S | FR-141 | COACH-4, ST-058c |
| ST-060 | Code-grader eval on rules-only plans, ≥ 30 cases, pass^3 = 100%, in CI | senior-ml-cv-engineer | senior-backend-engineer | M | NFR-005 (a); QD-QG-S7 | ST-057, ST-058c |
| ST-061a | Plan persistence: migration 0018, repository, ownership | senior-backend-engineer | senior-qa-engineer | M | FR-121; NFR-051 | ST-056, PE-4, SEC-4 |
| ST-061b | Plan API: generate and read the current plan with preferences; NFR-019 | senior-backend-engineer | senior-qa-engineer | M | FR-120..123; NFR-019 | ST-061a, ST-055, ST-057, ST-067 |
| ST-062 | Mark session done (idempotent op id, offline replay) and "Not for me" swap API | senior-backend-engineer | senior-qa-engineer | M | FR-124 | ST-061b |
| ST-063a | Plan page P-01: weaknesses, sessions, drill "why" with metric, value, n and "Show me" evidence | senior-frontend-engineer | senior-backend-engineer | M | FR-122, FR-123 | ST-061b, PD-4, PM-4 |
| ST-063b | Plan preferences and generate P-02 | senior-frontend-engineer | senior-backend-engineer | M | FR-121 | ST-061b, PD-4 |
| ST-063c | Mark done offline (outbox, sync) and "Not for me" UI P-03 | senior-frontend-engineer | senior-backend-engineer | M | FR-124 | ST-062, ST-063a |
| ST-064 | `make demo` also generates the demo user's plan | sre-devops-engineer | senior-backend-engineer | S | QD §7 | ST-061b, ST-058c |
| ST-065 | Playwright E2E for the full journey, plan states, offline done, swap, keyboard and narrow widths | senior-qa-engineer | senior-frontend-engineer | M | QD §7; NFR-024/027/034 | ST-063b, ST-063c |
| ST-066 | README "Run it locally": prototype walkthrough and its checker | sre-devops-engineer | senior-qa-engineer | XS | QD §7 | ST-064, ST-063c |
| ST-067 | Config scaffold: weakness unit and the four feature flags (default off), PO-accepted values as settings | senior-backend-engineer | senior-qa-engineer | S | FR-003/008/009/120/160 | PE-4 |
| QA-HARNESS-4a | Live goal harness: `planlib.py` reference and `live_plan.py` (G04-01..03) | senior-qa-engineer | senior-backend-engineer | M | scorecard | PE-4, COACH-4 |
| QA-HARNESS-4b | Live goal harness: `live_privacy.py` (G04-09, G04-10) | senior-qa-engineer | senior-backend-engineer | S | scorecard | PE-4, SEC-4 |

### 3.4 R1 privacy and quotas behind flags (after the spine; ADR 0051 rule 4)

| ID | Title | Owner | Senior reviewer | Size | FR/NFR | Depends on |
|---|---|---|---|---|---|---|
| ST-068a | Age confirmation API behind `FEATURE_AGE_GATE` (migration 0019) | senior-backend-engineer | senior-qa-engineer | S | FR-003 | ST-067, SEC-4, ST-061b |
| ST-068b | Age question page A-01 and footage notice on upload | senior-frontend-engineer | senior-backend-engineer | S | FR-003 | ST-068a, PD-4, PM-4, ST-063c |
| ST-069 | Video retention setting and purge of review video on schedule behind `FEATURE_RETENTION_SETTING` (migration 0020) | senior-backend-engineer | senior-qa-engineer | M | FR-008; ADR 0006; NFR-066 | ST-068a, SEC-4 |
| ST-070 | Training-data consent behind `FEATURE_TRAINING_CONSENT`; label sets exclude non-consented matches (migration 0021) | senior-ml-cv-engineer | senior-backend-engineer | M | FR-009 | ST-069, SEC-4 |
| ST-071 | Privacy settings R-01: retention choice and deletion dates, training-data consent | senior-frontend-engineer | senior-backend-engineer | M | FR-008, FR-009 | ST-069, ST-070, PD-4, PM-4, ST-063c |
| ST-072a | Match-creation rate limit (10/h) and storage quota behind `FEATURE_QUOTAS`; quota regression suite | senior-backend-engineer | senior-qa-engineer | M | FR-160; NFR-023 | ST-067, SEC-4, ST-061b |
| ST-072b | Over-limit messages Q-01 (when the player can continue; quota used) | senior-frontend-engineer | senior-backend-engineer | S | FR-160 | ST-072a, PD-4, ST-063c |
| ST-073 | Billing alert rules at 50/80/100% for the LLM provider and the object store (config + rules only) | sre-devops-engineer | senior-backend-engineer | S | NFR-022 | SEC-4 |

### 3.5 Closing tickets

| ID | Title | Owner | Senior reviewer | Depends on |
|---|---|---|---|---|
| VERIFY-04 | Verification round(s) on `main`: scorecard filled live, one merged PR per round, ids in ledger format | senior-qa-engineer | sre-devops-engineer | every ticket in §3.1-§3.4 |
| RETRO-04 | Sprint report, retro, consolidation of `decision-log.md`, `blockers.md`, `status.json`, `progress.md`, roadmap §12 actuals | engineering-manager | senior-qa-engineer | VERIFY-04 |

### 3.6 Order of work and CI-first rule

1. **Wave 0 (any time, pre-empts everything):** if a `main` run is red or cancelled-by-timeout, the EM opens a `CI-<CAUSE>` ticket with `ci_fix=true`, owner sre-devops-engineer (or the owner of the failing suite), and no feature PR merges until it is merged (PO 2026-10-08). The same applies to a red PR pipeline caused by `main`.
2. **Wave 1 (parallel):** PE-4, PD-4, SEC-4, COACH-4, PM-4; C4-G12, C4-CA, C4-TAC5, C4-LOCUST, C4-RED, C4-RECON.
3. **Wave 2 (spine, as gates merge):** ST-067, ST-055, ST-056, ST-058a→b→c, QA-HARNESS-4a/b; then ST-057, ST-061a, ST-059; then ST-061b, ST-060; then ST-062, ST-063a, ST-063b, ST-064; then ST-063c; then ST-065, ST-066. **Prototype milestone:** ST-066 merged = goal bullet 1 demonstrable.
4. **Wave 3 (privacy and quotas):** ST-073 (any time after SEC-4); ST-068a → ST-069 → ST-070 (migration order 0019 → 0020 → 0021); ST-072a; then ST-068b, ST-071, ST-072b (FE, after ST-063c).
5. **Wave 4:** VERIFY-04 (rounds in series, ADR 0047 rule 1), RETRO-04.

### 3.7 Story specifications (acceptance criteria, tests, context, directories)

Each card names the Gherkin feature, the integration tests (IT) and the unit tests the PR must carry, all written first and seen failing (negative case first, ADR 0022; the `Red:` line or a test-only commit, C4-RED). Directories are the only ones the ticket may change, plus its own `docs/sprints/04/decisions/<ID>.md` and, when an accepted test changes, a row in `test-change-requests.md`.

#### PE-4 Coaching design and API contract (gate)
- **AC:** `coaching-plan.md` defines the `TrainingPlan` aggregate (owns `Session`, `DrillAssignment`; invariants QD-PL-01..04; version for optimistic concurrency), `Weakness` value objects, the ACL from Analytics (`analytics.public` read model: rally outcomes per side with serve/receive, metric values, n, evidence rally ids) so Coaching never imports analytics internals, events `TrainingPlanGenerated`, `SessionMarkedDone`, `DrillSwapped`, determinism rule (stable sort keys, no clock or random in the domain), what happens to a plan when a cited match or the account is deleted (deleted with the account; a plan citing a deleted match is marked stale and regenerated on next read, judgment to confirm), migration numbers 0018 (plans) → 0019 (age) → 0020 (retention) → 0021 (consent) and that ST-072a needs none. `api-sprint-04.md`: `POST /me/plan` (preferences body: minutes per session, sessions per week, players available, equipment needs, level), `GET /me/plan`, `POST /me/plan/sessions/{session_id}/done` (`Idempotency-Key` op id), `POST /me/plan/assignments/{assignment_id}/swap` (reason optional), age, retention, consent and quota routes and error codes (429 `rate_limited` with `retry_at`, quota code and body), all as owned resources (404 to others). Flag-on E2E strategy (default: flag-on Playwright project run nightly and by the verifier; per-PR coverage by IT and Vitest).
- **Checks (docs ticket):** `racket-adr`/markdown link check in CI; the contract's routes appear in the BOLA inventory plan (SEC-4); review by SBE and FE. **Context:** Coaching (C1), Analytics (ACL), Identity. **Dirs:** `docs/architecture/`.

#### PD-4 Flows (gate)
- **AC:** P-01 plan (weaknesses with the unit name, sessions, drill rows with "why: AN-xx value, n" and "Show me"; notice "unofficial scoring" once and "drills not yet checked by a human coach" (interim); limited-data banner with n), P-02 preferences, P-03 done/undo-offline/"Not for me" with reason, A-01 age question, footage notice on upload, R-01 retention and consent, Q-01 over-limit; empty, loading, error, offline, not-found states; HAX G1/G2/G11 and WCAG 2.2 AA checklists; 320/360 px layouts. DR-04 decider cells (FE, coach, PM, security, BA) recorded in the file with dates.
- **Checks:** link check; DR-04 cells present. **Dirs:** `docs/design/`.

#### SEC-4 Threat notes (gate)
- **AC:** STRIDE notes for plan routes (BOLA on plan/session/assignment ids; replayed done op ids; swap abuse), FR-003 (no account row for under-18; no stored birth date, only the confirmation timestamp), FR-008 (retention change cannot shorten another user's data; purge order objects-then-rows, ADR 0042), FR-009 (consent off by default, revocation takes effect at next label-set build, audit row), FR-160/NFR-023 (per-account and per-IP keys, fail closed, no quota bypass through tus resume), NFR-022 (no secrets in alert rules). BOLA matrix rows to add (`backend/tests/regression/bola.py`) listed per route. Interim legal wording flagged as not legal advice (US + AU).
- **Dirs:** `docs/security/`.

#### COACH-4 Weakness catalogue and drill protocol (gate)
- **AC:** `weakness-catalogue.md`: each Quick Tag ending type × responsible side → weakness (e.g. serve fault → "serve faults"; unforced error while serving/receiving → "unforced errors"; forced error → "errors under pressure"; opponent winner → "opponent winners against you"), its target metric (AN-01, AN-02, AN-04, AN-05 or AN-07), serve/receive attribution rules (`@needs-verification` side-out part), tie-break order for equal counts; R1 targetable metrics (proposed AN-01, AN-02, AN-04, AN-05, AN-07; AN-03 and AN-06 are summaries, not trained directly; judgment, coach decides); worked example for the FR-120 scenario and for GS-AN-1 hand counts per side. `drill-review-checklist.md`: what `coach-reviewed` means for a drill (schema + lint pass, source or "(judgment)" rationale, numeric success criterion, safety notes per QD-DR-04, level fit), warm-up rule (QD-PL-03: every session starts with a drill tagged skill `warm-up`, 5-10 minutes), coverage scope (targetable metrics × beginner/intermediate/advanced, ≥ 2 drills per cell, ≥ 1 with `players ≤ 2`, ≥ 1 without `ball_machine`).
- **Dirs:** `docs/domain/`.

#### PM-4 ADR 0005 and interim wording (gate)
- **AC:** ADR 0005 Accepted or amended with a dated row (thresholds stay config, ADR 0041); `interim-wording-sprint-04.md` lists every user-facing string for FR-003, FR-008, FR-009 and FR-160, each marked "interim, pending legal review (NFR-070, P16)" (the storage-quota text also "size pending P8"); the values in the texts are the PO-accepted ones (ADR 0023), with the plain-language reading level check (NFR-028).
- **Dirs:** `docs/decisions/0005-*`, `docs/requirements/`.

#### C4-G12 Close the G03-12 rows
- **AC:** principal-designer flips the `flows-sprint-03.md` §13 2026-10-10 row to "Held" with DoR R7 and fixes line 3; senior-backend-engineer posts a verdict review on PR #27 for head `52582fd` (outside this PR; if not APPROVE, a fix ticket is opened); the EM writes Fixed rows for PD-R1S3-01/QA-R3S3-06 and EM-PR27-01 in `docs/sprints/03/review-rounds.md` with evidence; `demo_test_report.py` re-run.
- **Checks:** `python3 scripts/measure/open_defects.py docs/sprints/03/review-rounds.md` → rc 0, `open 0`; `merged_verdict.py --pr 27 --role principal-engineer --role senior-backend-engineer` → rc 0; `demo_test_report.py` → rc 0; `reconcile_due.py --report-only` lists 0 due. **Dirs:** `docs/design/flows-sprint-03.md`, `docs/sprints/03/review-rounds.md`.

#### C4-CA `extra_ca` build secret (VR3-S3-01)
- **AC:** `infra/compose.yaml` passes an optional BuildKit secret `extra_ca` to every built service (api, worker, purge, web, others built from Dockerfiles); the Dockerfiles append it to the trust store only when present (`RUN --mount=type=secret,id=extra_ca,required=false`); default (no `EXTRA_CA_FILE`) builds are byte-for-byte the same steps; the CA never lands in an image layer; README "Run it locally" documents `EXTRA_CA_FILE=/path/ca.crt make up`.
- **Gherkin:** `tests/features/compose_extra_ca.feature` — "Build behind a TLS-intercepting proxy" and the negative "No extra CA configured → no secret mounted and no CA file in the image". **IT:** IT-04-14 `infra/tests/test_compose_extra_ca.py`: `docker compose config` with and without `EXTRA_CA_FILE`; a real build of one image with a throwaway CA then `docker history`/file check shows no CA in layers (marked integration). **Unit:** compose YAML parse tests for every build service. **Context:** platform/infra. **Dirs:** `infra/`, `README.md`, `tests/features/`.

#### C4-TAC5 T-AC-5
- **AC:** an integration test proves that an account deleted while holding the labeller role and re-created with the same address has no labeller role and gets 403 on label routes. Red-first evidence: a one-line mutant that copies the role to the new account makes it fail (as #63).
- **Gherkin:** scenario added to `tests/features/account_deletion.feature` (new scenario, no existing step changed). **IT:** `backend/tests/integration/test_it_03_08_delete_account.py` new test (QA lane; addition only, no TCR needed). **Unit:** role-grant unit test in `backend/tests/unit/players/`. **Context:** Identity, Dataset. **Dirs:** `backend/tests/`, `tests/features/`.

#### C4-LOCUST Locust on stats and evidence in CI
- **AC:** `backend/tests/perf/locustfile_sprint04.py` (or an extension) loads GET stats and GET evidence for a seeded tagged match at 50 RPS in the `perf-baseline` job; `perf_verdict.py` gates p95 ≤ 300 ms, p99 ≤ 800 ms, availability ≥ 99.5% for those routes (NFR-010 dashboard, NFR-041); G03-05 dry-run row written in `docs/sprints/03/goal-scorecard.md` §6 (VR3-S3-02).
- **Gherkin:** `tests/features/ci_perf_gates.feature` new scenario "Stats read latency gate" plus the negative (a synthetic stats CSV over the threshold fails). **IT:** `infra/tests/test_perf_verdict_stats.py` runs `perf_verdict.py` on fixture CSVs. **Unit:** verdict rule tests. **Dirs:** `.github/workflows/ci.yml` (perf-baseline job only), `backend/tests/perf/`, `scripts/ci/perf_verdict.py`, `infra/tests/`, `tests/features/`, `docs/sprints/03/goal-scorecard.md` (§6 row only).

#### C4-RED `Red:` check
- **AC:** `scripts/ci/check_red_first.py --base <sha> --head <sha>` fails when a commit in the PR adds or changes `backend/src/**` or `web/src/**` and neither has a `Red:` line in its body nor follows an earlier test-only commit in the same PR; docs-only and test-only PRs pass; merge commits ignored; runs in the `pr-policy` job and is required by `ci-gate`.
- **Gherkin:** `tests/features/red_first_check.feature` — negative first: "A code commit with no red step fails", then "test-only commit before code passes", "`Red:` line passes", "docs-only PR passes". **IT:** IT-04-15 `infra/tests/test_check_red_first.py` builds a throwaway git repo with planted commits and runs the script. **Unit:** commit classification tests. **Dirs:** `scripts/ci/`, `.github/workflows/ci.yml` (pr-policy step), `infra/tests/`, `tests/features/`.

#### C4-RECON `reconcile_due.py` and verifier ids
- **AC:** a merged ticket whose diff changes the evidence cell of an open row (not only names it) is "due" (VM-R3-02); `measurelib._FINDING_ID` parses the verifier format (`V04R1-01`) and the ledger format; QA-RETRO03-03 docstring fixed.
- **Gherkin:** `tests/features/reconcile_due.feature` new scenarios (negative first: "evidence changed, no reconciliation row → due"). **IT:** `infra/tests/test_reconcile_due.py` new cases on a temp git repo. **Unit:** id regex tests. **Dirs:** `scripts/measure/`, `infra/tests/`, `tests/features/`.

#### ST-055 Weakness ranking (FR-120)
- **AC:** pure domain `racket.coaching.weakness`: from per-side rally facts (ending type, responsible player, server side) over the player's tagged, non-deleted matches, compute rallies lost per game per weakness, split lost-on-serve and lost-on-receive; points conceded shown separately; ranking by total rallies lost per game, ties by the catalogue order (COACH-4); unit object carries the configured unit name (ADR 0003) and a side-out-unverified mark (field name per PE-4) while the side-out rule is unverified (P7); the FR-120 example ranks "unforced errors" above "serve faults"; zero games → empty ranking, not an error. Analytics data enters only through the `analytics.public` read model (ACL).
- **Gherkin:** `tests/features/weakness_ranking.feature` (`@needs-verification`): FR-120 scenario; negative first "No tagged match → no weakness and a reason"; "Each weakness shows rallies lost on serve and on receive"; "The serve/receive split is marked unverified". **IT:** IT-04-01 `backend/tests/integration/test_it_04_01_weakness_from_stats.py`: tagged worked example in Postgres → ranking through the ACL equals the coach's catalogue worked example. **Unit:** `backend/tests/unit/coaching/test_weakness.py` (tables from the catalogue; GS-AN-1 per side; property: sum of attributed rallies lost = rallies lost by that side, ≥ 1,000 examples). **Context:** Coaching (domain, no framework imports), Analytics public read model. **Dirs:** `backend/src/racket/coaching/weakness*`, `backend/src/racket/analytics/public.py` (read model addition only), `backend/tests/`, `tests/features/`.

#### ST-056 `TrainingPlan` aggregate and assembly (FR-121; QD-PL-01..03)
- **AC:** given top-3 weaknesses, preferences and the reviewed library, build a 2-week plan deterministically: sessions per week as stated; each session total ≤ minutes per session; weekly total ≤ stated weekly minutes; every session starts with a `warm-up` drill; no drill > 40% of its session; only `coach-reviewed`/`verified`, non-deprecated drills whose `players ≤ available` and `needs ⊆ equipment`; drills target the weakness metrics, spread by weakness rank; no feasible drill for a weakness → the plan names the weakness as "no drill fits your setup" instead of breaking a constraint. Aggregate guards its invariants on creation and on every change (swap, done).
- **Gherkin:** `tests/features/training_plan.feature`: negative first "Solo player without a ball machine never gets a ball-machine or 4-player drill"; FR-121 "Solo player with 30 minutes"; warm-up first; 40% cap; "same input → same plan". **IT:** IT-04-02a `backend/tests/integration/test_it_04_02_plan_assembly_library.py`: assembly over the real `content/drills` library loaded by the drills module. **Unit:** `backend/tests/unit/coaching/test_training_plan.py` (each invariant, negative cases first; property ≥ 1,000 random preference/library inputs → 0 violations). **Context:** Coaching domain. **Dirs:** `backend/src/racket/coaching/plan/` (domain only), `backend/tests/`, `tests/features/`.

#### ST-057 Citations and limited data (FR-122, FR-123; QD-PL-04, PL-06)
- **AC:** each `DrillAssignment` cites `(metric_id, value, n, rally_ids)` taken from the ACL for the player's side; the "why" text names the metric and value ("Serve fault %: 29% of 7 serves"); rally ids ≤ 10 with a "see all n" link target (same rule as evidence, FR-103); if the top weakness's metric is low-sample (metric dictionary rule, ADR 0041/0005) the plan carries `limited_data: {rallies: N}` and the text "based on limited data from N rallies"; an assignment without a citation cannot be created (aggregate invariant).
- **Gherkin:** `tests/features/drill_rationale.feature` (FR-122) and `tests/features/limited_data_plan.feature` (FR-123; negative first "missing citation is refused"). **IT:** IT-04-02b `backend/tests/integration/test_it_04_02_plan_citations.py`: citations equal GET stats and every rally id is in GET evidence for that metric. **Unit:** `backend/tests/unit/coaching/test_citations.py`. **Dirs:** `backend/src/racket/coaching/plan/`, `backend/tests/`, `tests/features/`.

#### ST-058a/b/c Starter drill library (FR-141 content)
- **AC:** 7 (a), 7 (b) and ≥ 7 (c) new drills under `content/drills/pb.<skill>.<name>/v1.json`, each schema v1 valid, `racket-drill-lint` 0 problems, `review_status: coach-reviewed` after the COACH-4 checklist (checklist row per drill in the ticket's decisions file), `source` or "(judgment)" rationale, numeric success criterion, safety notes where QD-DR-04 applies; at least 3 `warm-up` drills in (a); `library.lock` updated (serial a → b → c to avoid lock conflicts); after (c): ≥ 20 drills and every coverage cell of COACH-4 filled (checked by ST-059's CLI locally if merged, else by the matrix in the decisions file).
- **Checks (content ticket):** `cd backend && uv run racket-drill-lint ../content/drills` → `ok, 0 problem(s)`; drill-lint CI job green; a scenario row in `tests/features/drill_library.feature` is not needed (content only). The coach records each drill's checklist outcome. **Context:** Coaching drills module. **Dirs:** `content/drills/`.

#### ST-059 Coverage-matrix check in CI (FR-141; QD-DR-05)
- **AC:** `racket-drill-coverage ../content/drills` prints the matrix (targetable metric × level: count, `players ≤ 2` count, no-ball-machine count) and exits 1 naming each empty cell in scope; counts only `coach-reviewed`/`verified`, non-deprecated drills; total ≥ 20; runs in the `drill-lint` CI job.
- **Gherkin:** `tests/features/drill_coverage.feature` (`@needs-verification`): negative first, the FR-141 "Missing coverage cell" scenario on a fixture library; "full library passes and prints the matrix". **IT:** IT-04-13 `backend/tests/integration/test_it_04_13_drill_coverage_cli.py` runs the CLI on `content/drills` (pass) and on `backend/tests/fixtures/drills-coverage-gap/` (fail, names the cell). **Unit:** `backend/tests/unit/coaching/test_coverage.py`. **Dirs:** `backend/src/racket/coaching/drills/coverage.py`, `backend/pyproject.toml` (script entry), `.github/workflows/ci.yml` (drill-lint job), `backend/tests/`, `tests/features/`.

#### ST-060 Code-grader eval (NFR-005a)
- **AC:** ≥ 30 eval cases in `backend/tests/evals/plan_cases/` (synthetic tag scripts + preferences: solo/pairs/four, 20-90 min, with/without ball machine/wall, beginner..advanced, low and high sample); graders: every drill id@version exists and is reviewed, every assignment cites a metric that the stats show with its value and n, QD-PL-01..03 hold; each case run 3 times; pass^3 = 100% required (a case passes only if all 3 runs pass and are byte-identical); `racket-plan-eval --runs 3` prints per-case results and exits 1 on any failure; a CI job (or step in `python-unit`) runs it.
- **Gherkin:** `tests/features/plan_eval.feature`: negative first "a planted grader-violating plan fails the eval and is named"; "the suite passes at pass^3". **IT:** IT-04-16 `backend/tests/integration/test_it_04_16_plan_eval_cli.py` runs the CLI over the real library. **Unit:** grader tests `backend/tests/unit/coaching/test_graders.py`. **Context:** Coaching (evaluation, outside the domain layer). **Dirs:** `backend/src/racket/coaching/evals/`, `backend/tests/`, `backend/pyproject.toml`, `.github/workflows/ci.yml` (one step), `tests/features/`.

#### ST-061a Plan persistence
- **AC:** migration `0018_training_plans` (plans, sessions, assignments, done ops with unique `(account_id, op_id)`, plan version, preferences JSON, `stale` flag; owner column; grants like 0012/0013); repository maps the aggregate both ways; deleting the account removes plan rows (purge inventory extended, ADR 0042 order); every query filters by owner.
- **Gherkin:** `tests/features/training_plan.feature` scenario "A saved plan reads back identical". **IT:** IT-04-02c `backend/tests/integration/test_it_04_02_plan_repository.py` (round trip; another owner sees nothing; account purge leaves 0 plan rows). **Unit:** mapping tests. **Dirs:** `backend/src/racket/coaching/plan/repository.py`, `backend/src/racket/migrations/versions/0018_*`, `backend/src/racket/platform/purge.py` (inventory only), `backend/tests/`.

#### ST-061b Plan API (FR-120..123; NFR-019)
- **AC:** `POST /me/plan` validates preferences (422 with field errors), ranks weaknesses (ST-055), assembles (ST-056) with citations (ST-057), saves and returns 201 with the plan, weaknesses with the unit and the side-out-unverified mark, limited-data note and the "unofficial scoring" flag; `GET /me/plan` 200 or 404 `no_plan`; no tagged match → 409 `no_tagged_match` with the reason text; generation p95 ≤ 5 s (NFR-019) measured in IT; routes added to the BOLA matrix (other accounts get 404 for session/assignment ids); OpenAPI updated.
- **Gherkin:** `tests/features/rules_only_plan_api.feature` (negative first "no tagged match"). **IT:** IT-04-02 `backend/tests/integration/test_it_04_02_plan_api.py`; IT-04-03 BOLA rows in `backend/tests/regression/bola.py` (QA lane file: TCR row if an existing table entry changes; additions only expected). **Unit:** request/response schema tests. **Dirs:** `backend/src/racket/coaching/api.py`, `service.py`, `backend/src/racket/platform/app.py` (router include), `backend/tests/`, `tests/features/`.

#### ST-062 Done and swap (FR-124)
- **AC:** `POST .../sessions/{id}/done` with `Idempotency-Key` marks done once; a replay with the same key returns the same result and does not bump the version; a different key on a done session is a no-op 200; undo (`DELETE .../done`) allowed; `POST .../assignments/{id}/swap` replaces the drill with another reviewed drill targeting the same metric that keeps every QD-PL-01..03 invariant; no alternative → 409 `no_alternative` and the plan is unchanged; optional reason (≤ 200 chars) stored; swapped-out drill not offered again in that plan.
- **Gherkin:** `tests/features/plan_follow_through.feature`: negative first "no alternative drill → plan unchanged"; FR-124 "Swap a drill"; "Mark done twice offline → done once". **IT:** IT-04-04 `test_it_04_04_session_done_idempotent.py`; IT-04-05 `test_it_04_05_swap.py`. **Unit:** aggregate swap/done tests. **Dirs:** `backend/src/racket/coaching/`, `backend/tests/`, `tests/features/`.

#### ST-063a Plan page P-01
- **AC:** route `/plan` per PD-4: weaknesses (unit name; the "unofficial scoring" notice covers the unverified side-out split), sessions per week, each drill with name, minutes, players, equipment, "why" citing metric, value and n, and "Show me" opening the evidence panel for that metric (reuses `EvidencePanel`); notices: "unofficial scoring" once before the first card and the interim human-coach notice; limited-data banner; empty (no tagged match), loading, error, not-found states; nav link from the match stats page and the account menu; keyboard and 320/360 px.
- **Gherkin:** bindings for `drill_rationale.feature` UI scenario in `web/tests/` (Vitest + Testing Library). **IT:** contract test against the OpenAPI schema (`web/tests/contract/plan.test.ts`) with MSW. **Unit:** component tests (`web/tests/unit/plan-view.test.tsx`), negative first (citation missing → row shows an error, not a blank). **Dirs:** `web/src/app/plan/`, `web/src/components/plan/PlanView*`, `web/src/lib/api/plan*`, `web/tests/`.

#### ST-063b Plan preferences P-02
- **AC:** `/plan/new` form (minutes per session, sessions per week, players, equipment, level) with validation and error summary (existing `ErrorSummary`), submit calls `POST /me/plan`, shows the 409 no-tagged-match reason with a link to tag a match; regenerate keeps the last preferences.
- **Tests:** Vitest form tests (negative first: invalid minutes), contract test, Gherkin binding for FR-121 UI step. **Dirs:** `web/src/app/plan/new/`, `web/src/components/plan/PlanPreferences*`, `web/tests/`.

#### ST-063c Offline done and "Not for me" P-03
- **AC:** "Mark done" works offline: an IndexedDB outbox stores `{op_id, session_id}`, the UI shows "Saved on this device, will sync", sync on `online` and on page load, replays are idempotent (ST-062), conflicts shown; "Not for me" opens a dialog with optional reason, calls swap, focuses the new drill, shows 409 no-alternative text; the service worker caches the plan page shell and the last plan JSON for offline reading.
- **Tests:** Vitest outbox tests (negative first: sync failure keeps the op), fake-indexeddb; contract test for done/swap; Gherkin binding for "Mark done twice offline". **Dirs:** `web/src/components/plan/`, `web/src/lib/plan-outbox*`, `web/public/sw*` or the existing SW registration, `web/tests/`.

#### ST-064 `make demo` generates a plan
- **AC:** `seed_demo.py` after seeding the match calls `POST /me/plan` with fixed demo preferences (solo, 30 min, 3 sessions/week, no ball machine, intermediate) unless the demo user already has a plan; prints the plan URL `https://localhost:3000/plan`; re-running adds nothing; exit codes unchanged (0, 1, 3).
- **Gherkin:** `tests/features/demo_seed.feature` new scenarios (negative first: "plan step fails → rc 1 and names the step"; "re-run keeps the same plan id"). **IT:** IT-04-11 `infra/tests/test_seed_demo_plan.py` against a local API stub or the dev stack (marked integration). **Unit:** `scripts/demo` unit tests for the plan step. **Dirs:** `scripts/demo/`, `infra/tests/`, `tests/features/`, `Makefile` (help text only).

#### ST-065 E2E journey
- **AC:** `web/e2e/sprint-04/journey-v3.spec.ts` E2E-04-01: sign in → doubles match → upload fixture → Quick Tag the worked example → score sheet → stats → generate plan → a drill's "why" shows metric, value, n → "Show me" opens the rallies → mark a session done offline (Playwright `context.setOffline`) → back online, synced → "Not for me" swaps a drill; E2E-04-02 plan states (empty, limited data, loading, error, not found) with axe and 24×24 target checks; E2E-04-03 offline done survives reload; E2E-04-04 swap with no alternative; E2E-04-05 keyboard-only and 320/360 px. Flag-on specs E2E-04-06..08 (age, settings, over-limit) in a `flags-on` project run nightly and by the verifier (PE-4). 0 flaky over `--repeat-each=3`.
- **Gherkin:** the journey is the QD §7 scenario in `tests/features/e2e_journey.feature` (new scenario). **IT:** n/a beyond E2E (the E2E is the integration level for UI); `junit_rate.py` ids. **Unit:** helper unit tests in `web/tests/unit/e2e-helpers-*.test.ts` if helpers are added. **Dirs:** `web/e2e/sprint-04/`, `web/e2e/helpers/`, `web/playwright.config.ts` (project only), `tests/features/`.

#### ST-066 README prototype walkthrough
- **AC:** README "Run it locally" gains "Try the prototype": `make up`, `make demo`, open the stats URL, open `/plan`, open a drill's "why" and "Show me", mark a session done, "Not for me", `make down`; `check_readme_quickstart.py` checks the new named items.
- **Gherkin:** `tests/features/readme_quickstart.feature` new scenario (negative first: a missing step fails the checker). **IT:** `infra/tests/test_readme_quickstart.py` new case on the real README. **Unit:** checker unit test. **Dirs:** `README.md`, `scripts/ci/check_readme_quickstart.py`, `infra/tests/`, `tests/features/`.

#### ST-067 Config scaffold
- **AC:** `Settings` gains `coaching_weakness_unit` (only `rallies_lost_per_game`; anything else fails at start), `feature_age_gate`, `feature_retention_setting`, `feature_training_consent`, `feature_quotas` (all default `False`), `age_minimum` 18, `retention_choices_days` (30, 90, 365, none) and default 90, `match_creations_per_hour` 10, `storage_quota_bytes` 20 GB; `infra/env.example` lists them off with a comment naming each value's source ("ADR 0023, OQ-nn"; "(judgment), P8" for the storage quota); a `GET /config/public` (or existing config route) exposes the flags the web needs.
- **Gherkin:** `tests/features/feature_flags.feature`: negative first "unknown weakness unit refuses to start"; "flags are off by default". **IT:** `backend/tests/integration/test_it_04_17_public_config.py`. **Unit:** settings parsing tests. **Dirs:** `backend/src/racket/platform/settings.py`, `backend/src/racket/platform/http.py` (route), `infra/env.example`, `backend/tests/`, `tests/features/`.

#### QA-HARNESS-4a Live harness for the plan
- **AC:** `scripts/measure/planlib.py`: an independent reference (standard library only) for weakness ranking from a tag script (catalogue rules) and a code grader for QD-PL-01..04 on a plan JSON; `scripts/measure/live_plan.py --runs N`: the G04-01 journey per run as a fresh account over https, G04-02 timings, G04-03 (a) comparison; fail closed (rc 1 on any failed step, rc 2 below the disk floor or unreadable stack). Written red against the PE-4 contract; dry-run row written before VERIFY-04 (ADR 0033 rule 2).
- **Gherkin:** `tests/features/live_plan_harness.feature` (negative first: "a plan breaking QD-PL-01 is reported as a failed step"). **IT:** `infra/tests/test_live_plan_harness.py` against a stub HTTPS server. **Unit:** `infra/tests/test_planlib.py` pinned to the COACH-4 worked examples. **Dirs:** `scripts/measure/`, `infra/tests/`, `tests/features/`.

#### QA-HARNESS-4b Live harness for privacy and quotas
- **AC:** `scripts/measure/live_privacy.py`: G04-09 and G04-10 steps with a `--flags on|off` mode (the verifier restarts the stack with the env set); counts accounts in Postgres for the under-18 case; runs the purge job with a dev `--now` offset for retention; builds a label set through the dataset CLI for consent; bursts 50 match creations for the rate limit; uploads past the quota; checks the alert-rule test command. Fail closed.
- **Tests:** feature `tests/features/live_privacy_harness.feature`, IT against a stub, unit tests. **Dirs:** `scripts/measure/`, `infra/tests/`, `tests/features/`.

#### ST-068a Age confirmation API (FR-003)
- **AC:** with `feature_age_gate` on, a newly signed-in address has no usable account until `POST /me/age-confirmation {"is_adult": true}`; `false` deletes the pending sign-in state and creates no account row (403 `under_age` with the interim text); routes other than confirmation return 403 `age_confirmation_required` until confirmed; only `age_confirmed_at` is stored, never a birth date; flag off → behaviour as today (no extra step).
- **Gherkin:** `tests/features/age_confirmation.feature` (FR-003 both scenarios; negative first "Under-age applicant"; "flag off → no question"). **IT:** IT-04-06 `test_it_04_06_age_gate.py` (DB: 0 account rows after under-18). **Unit:** identity domain rule tests. **Dirs:** `backend/src/racket/players/`, `backend/src/racket/migrations/versions/0019_*`, `backend/tests/`, `tests/features/`.

#### ST-068b Age question page and footage notice (FR-003)
- **AC:** A-01 single-question page after sign-in when the public config says the flag is on; under-18 path shows why and what to do instead (interim text, PM-4); upload page shows the footage notice (no minors) when the flag is on; flag off → no change to existing screens.
- **Tests:** Vitest (negative first: under-18 path), contract test, Gherkin binding; E2E-04-06 lives in ST-065's flags-on project (spec added here if ST-065 merged first). **Dirs:** `web/src/app/welcome/` or `web/src/app/age/`, `web/src/components/`, `web/tests/`.

#### ST-069 Video retention (FR-008; ADR 0006)
- **AC:** with `feature_retention_setting` on, `PUT /me/retention {"review_video_days": 30|90|365|null}` (default 90); match API shows `review_video_delete_at`; the purge job deletes review video objects whose date passed (objects first, then the media row), keeping tags, stats and plans; the system rule (originals 30 days after analysis) keeps its current behaviour; the purge accepts a dev-only `--now` override for tests; flag off → no deletion by this rule.
- **Gherkin:** `tests/features/video_retention.feature` (FR-008; negative first "flag off → video kept"). **IT:** IT-04-07 `test_it_04_07_retention_purge.py` (object 404, stats 200). **Unit:** retention date rules. **Dirs:** `backend/src/racket/players/` (setting), `backend/src/racket/video_ingest/` (dates), `backend/src/racket/platform/purge.py`, migration `0020_*`, `backend/tests/`, `tests/features/`.

#### ST-070 Training-data consent (FR-009)
- **AC:** with `feature_training_consent` on, `PUT /me/training-consent {"opt_in": bool}` (default false, audit row per change); the label-set/gold-manifest builder in `racket.dataset` includes only matches whose owner has opted in at build time; revoke → excluded from the next build; frozen gold-set versions are not edited and retire at their next scheduled refresh (OQ-06, accepted 2026-10-05, ADR 0023; documented); flag off → the builder behaves as today (consented-match rule of FR-150 unchanged).
- **Gherkin:** `tests/features/training_consent.feature` (FR-009 both scenarios; negative first "not opted in → excluded"). **IT:** IT-04-08 `test_it_04_08_consent_label_set.py`. **Unit:** dataset selection rule tests. **Dirs:** `backend/src/racket/dataset/`, `backend/src/racket/players/` (consent setting), migration `0021_*`, `backend/tests/`, `tests/features/`.

#### ST-071 Privacy settings R-01
- **AC:** `/settings/privacy` (when either flag is on): retention choice with each match's video deletion date list, consent toggle (off by default) with interim explanation; saves with confirmation and error states; keyboard and 320/360 px.
- **Tests:** Vitest (negative first: save error keeps the old value), contract tests, Gherkin bindings. **Dirs:** `web/src/app/settings/privacy/`, `web/src/components/settings/`, `web/tests/`.

#### ST-072a Rate limit and storage quota (FR-160; NFR-023)
- **AC:** with `feature_quotas` on: the 11th `POST /matches` within an hour → 429 `rate_limited` with `retry_at` (reusing `platform.ratelimit`); a tus upload whose declared length would push the account past `storage_quota_bytes` → refused before any byte is stored (code per PE-4) with limit and usage; resumed uploads count once; per-account keys; quota regression suite asserts 0 accepted requests beyond each limit over a burst of 50; flag off → today's limits only.
- **Gherkin:** `tests/features/rate_limits.feature` (FR-160; negative first "11th match refused with a time"). **IT:** IT-04-09 `test_it_04_09_quota_regression.py` (burst; quota; flag off). **Unit:** quota arithmetic tests. **Dirs:** `backend/src/racket/matches/`, `backend/src/racket/video_ingest/`, `backend/src/racket/platform/ratelimit.py`, `backend/tests/`, `tests/features/`.

#### ST-072b Over-limit messages Q-01
- **AC:** the match-create and upload screens show "You can start a new match at HH:MM" (local time) and "You have used X of Y GB" per PD-4 when the API returns those codes; no message when the flag is off.
- **Tests:** Vitest (negative first: missing `retry_at` still shows a safe message), contract test, Gherkin binding. **Dirs:** `web/src/components/MatchSetup*`, `MatchUpload*`, `web/src/lib/api/`, `web/tests/`.

#### ST-073 Billing alerts (NFR-022)
- **AC:** `infra/observability/alerts/billing.yml` with 6 rules (LLM provider and object store × 50/80/100% of a monthly budget metric), budgets as env settings with no provider credentials; `promtool test rules` (pinned image via mirror) or an equivalent tested evaluator proves each rule fires at its threshold and not 1% below; documented in `docs/ops/`.
- **Gherkin:** `tests/features/billing_alerts.feature` (negative first "49% → no alert"). **IT:** IT-04-10 `infra/tests/test_billing_alert_rules.py` (rule test run). **Unit:** YAML structure tests. **Dirs:** `infra/observability/`, `infra/tests/`, `docs/ops/`, `tests/features/`.

#### VERIFY-04 and RETRO-04
- **VERIFY-04:** after the build tickets merge, the verifiers (senior-qa-engineer with sre-devops-engineer) run every scorecard method on a fresh isolated stack at one recorded `main` head; each round is one PR that fills Actual/Met/Evidence, writes findings in the ledger format, and merges before the next round (ADR 0050 rules 4-5). Checks: `open_defects.py` and `reconcile_due.py` on both ledgers; `junit_rate.py` reports.
- **RETRO-04:** `docs/sprints/04/sprint-report.md`, `docs/retros/2026-12-11-sprint-04.md`, consolidated `decision-log.md` (from the per-ticket files), `blockers.md`, `status.json`, `progress.md`, roadmap §12 actuals, traceability-matrix Sprint 4 section.

### 3.8 Definition of Ready check (business-analyst with engineering-manager, 2026-10-17)

| Story | Ready? | Condition (owner, gate ticket) |
|---|---|---|
| ST-055 | Ready on condition | COACH-4 catalogue; PE-4 ACL; OQ-08 accepted (ADR 0003); side-out part `@needs-verification` until P7 (ADR 0051 rule 2) |
| ST-056, ST-057 | Ready on condition | PE-4 aggregate; COACH-4 warm-up rule; PM-4 ADR 0005 (ST-057) |
| ST-058a..c | Ready on condition | COACH-4 checklist and scope |
| ST-059, ST-060 | Ready on condition | COACH-4 scope; library after ST-058c |
| ST-061a/b, ST-062 | Ready on condition | PE-4 contract and migration numbers; SEC-4 BOLA rows |
| ST-063a/b/c | Ready on condition | PD-4 flows and DR-04 cells; PM-4 wording; API tickets merged |
| ST-064, ST-065, ST-066 | Ready on condition | API and UI tickets merged |
| ST-067 | Ready on condition | PE-4 setting names |
| ST-068a..ST-073 | Ready on condition | SEC-4 threat notes; PE-4 routes; PM-4 interim wording (values PO-accepted, ADR 0023; texts pending legal review P16; storage quota size P8) |
| C4-* | Ready | inputs in the Sprint 3 ledger and report §9 |

## 4. Task breakdown per role agent

| Role | Tasks |
|---|---|
| engineering-manager | PLAN-04 (this); reconciliation row after every review and verification round (ADR 0047 rule 1); status step with `merged_verdict.py` on every merged PR (B1) and `reconcile_due.py`; PR-policy decisions (`size-waiver` only for a single unsplittable commit, B4); Fixed rows of C4-G12; RETRO-04 |
| product-manager | PM-4; DR-04 cell; interim wording review in FE PRs |
| principal-engineer | PE-4; reviews every ticket PR; ticket map (§15) kept current |
| business-analyst | DoR (§3.8); DR-04 cell; traceability rows checked in RETRO-04 |
| principal-designer | PD-4 with DR-04; C4-G12 (DR-03 record) |
| security-privacy-engineer | SEC-4; DR-04 cell; specialist review of ST-061b, ST-068a, ST-069, ST-070, ST-072a |
| pickleball-domain-coach | COACH-4; ST-058a..c; DR-04 cell; specialist review of ST-055, ST-056 |
| senior-backend-engineer | ST-055, ST-056, ST-057, ST-061a, ST-061b, ST-062, ST-067, ST-068a, ST-069, ST-072a; senior reviews per §3; PR #27 verdict (C4-G12) |
| senior-frontend-engineer | ST-063a, ST-063b, ST-063c, ST-068b, ST-071, ST-072b; senior reviews per §3 |
| senior-qa-engineer | C4-TAC5, C4-RECON, ST-059, ST-065, QA-HARNESS-4a/b, VERIFY-04; TCR decisions; senior reviews per §3 |
| sre-devops-engineer | C4-CA, C4-LOCUST, C4-RED, ST-064, ST-066, ST-073; any `ci_fix` ticket; VERIFY-04 with QA |
| senior-ml-cv-engineer | ST-060, ST-070; senior reviews per §3 |

## 5. TDD plan (negative case first) [EP/ENG-18]

| Unit under test | First failing test (negative) | Then |
|---|---|---|
| Weakness ranking | no tagged match → empty ranking with reason | FR-120 example; serve/receive split; ties; GS-AN-1 per side; conservation property |
| Plan assembly | solo player without ball machine gets a ball-machine drill → must be impossible | time fit; weekly fit; warm-up first; 40% cap; infeasible weakness named; determinism; property ≥ 1,000 |
| Citations | assignment without citation is refused | value and n equal stats; rally ids ⊆ evidence; limited-data note at low sample |
| Coverage check | fixture library with an empty cell passes → must fail naming the cell | full library passes; deprecated/draft drills not counted |
| Eval | planted violating plan passes → must fail | 30+ cases × 3 runs, byte-identical |
| Done/swap | replayed op id bumps the version → must not | swap keeps metric and constraints; no alternative → unchanged |
| Age gate | under-18 answer creates an account → must not | adult proceeds; flag off unchanged |
| Retention | flag off deletes video → must not | 30-day choice deletes video after date; stats kept |
| Consent | non-consented match in a label set → must not | opt in included; revoke excluded |
| Quotas | 11th match accepted → must not | quota refused before bytes; resume counted once; flag off unchanged |
| Billing alerts | 49% fires → must not | 50/80/100 fire per provider |
| `Red:` check | code commit without red step passes → must fail | test-first and `Red:` pass; docs-only passes |
| Demo plan | plan step failure returns rc 0 → must be rc 1 | idempotent re-run |

## 6. Integration tests

Real Postgres, object store (SeaweedFS) and Mailpit through `scripts/dev-postgres.sh` / `scripts/dev-objectstore.sh` or Compose; https where the browser path matters (ADR 0029).

| ID | Ticket | What it proves |
|---|---|---|
| IT-04-01 | ST-055 | Weakness ranking through the Analytics ACL on a tagged match equals the catalogue worked example |
| IT-04-02 (a, b, c, API) | ST-056, ST-057, ST-061a, ST-061b | Assembly over the real library; citations equal stats and evidence; repository round trip; `POST/GET /me/plan` incl. 409/422 and NFR-019 p95 ≤ 5 s |
| IT-04-03 | ST-061b | BOLA matrix rows for plan, session and assignment ids (404 to others) |
| IT-04-04 | ST-062 | Done is idempotent per op id; replay does not change version |
| IT-04-05 | ST-062 | Swap keeps metric and constraints; no alternative → 409, unchanged |
| IT-04-06 | ST-068a | Under-18 → 0 account rows; adult proceeds; flag off unchanged |
| IT-04-07 | ST-069 | Retention purge deletes the review video object, keeps stats and plan |
| IT-04-08 | ST-070 | Label-set build includes only opted-in owners; revoke excludes |
| IT-04-09 | ST-072a | 0 requests accepted beyond limits over a burst of 50; quota before bytes; flag off unchanged |
| IT-04-10 | ST-073 | Alert rules fire at 50/80/100% and not below |
| IT-04-11 | ST-064 | `make demo` creates one plan; re-run keeps it |
| IT-04-12 | C4-TAC5 | Re-created account has no labeller role (T-AC-5) |
| IT-04-13 | ST-059 | Coverage CLI passes on the library, fails on a gap fixture naming the cell |
| IT-04-14 | C4-CA | `extra_ca` secret mounted only when set; never in a layer |
| IT-04-15 | C4-RED | `Red:` check on planted commits |
| IT-04-16 | ST-060 | Plan eval CLI over the real library: pass^3 = 100% |
| IT-04-17 | ST-067 | Public config exposes the flags; defaults off |
| Earlier | all | IT-01-*, IT-02-*, IT-03-*, BOLA, strict sandbox: no regression |

## 7. Gherkin scenarios

### 7.1 Weakness ranking and plan

```gherkin
# tests/features/weakness_ranking.feature
@needs-verification
Feature: Weakness ranking
  Rule: Weaknesses are ranked by rallies lost per game, split serve and receive (OQ-08, ADR 0003; the side-out part needs verification)
    Scenario: No tagged match
      Given Ivy has no tagged match
      When her weaknesses are ranked
      Then she has no weakness ranking
      And she is told to tag a match first
    Scenario: Serving errors are not undercounted
      Given Ivy lost 10 rallies on serve to her unforced errors and 4 rallies on receive to serve faults
      When her weaknesses are ranked
      Then "unforced errors" ranks above "serve faults"
      And each weakness shows rallies lost on serve and on receive
      And the serve and receive split is marked as not yet verified
```

```gherkin
# tests/features/training_plan.feature
Feature: Rules-only training plan
  Rule: Plans respect the player's constraints
    Scenario: No ball machine, no ball-machine drill
      Given Ivy plays alone and has no ball machine
      When she asks for a plan
      Then no drill in her plan needs a ball machine or more than 1 player
    Scenario: Solo player with 30 minutes
      Given Ivy plays alone with 30 minutes per session, 3 sessions a week and a wall
      When she asks for a plan
      Then the plan has 2 weeks of 3 sessions
      And every session lasts at most 30 minutes and starts with a warm-up
      And no drill takes more than 40% of a session
      And every drill is a reviewed library drill
    Scenario: Same input, same plan
      Given Ivy's stats and preferences do not change
      When she asks for a plan twice
      Then both plans are identical
```

```gherkin
# tests/features/drill_rationale.feature
Feature: Drill rationale
  Scenario: A drill cannot be assigned without a reason
    Given a drill assignment has no metric citation
    When the plan is built
    Then the assignment is refused
  Scenario: Why this drill
    Given Ivy's plan includes a serve-consistency drill
    When she opens it
    Then she sees the metric it targets, her value and its n
    And a link to the rallies behind that value
```

```gherkin
# tests/features/limited_data_plan.feature
Feature: Limited-data plan
  Scenario: One short match
    Given Ivy has 1 tagged match with 12 rallies
    When she asks for a plan
    Then she sees that the plan is based on limited data from 12 rallies
```

```gherkin
# tests/features/plan_follow_through.feature
Feature: Plan follow-through
  Scenario: No alternative drill
    Given no other reviewed drill targets the same metric within Ivy's constraints
    When she chooses "Not for me"
    Then she is told no alternative fits
    And her plan is unchanged
  Scenario: Swap a drill
    Given Ivy's session includes a drill she cannot do
    When she chooses "Not for me"
    Then a different library drill targeting the same metric replaces it
    And the session still fits her time limit
  Scenario: Mark done offline twice
    Given Ivy is offline
    When she marks the same session done twice and comes back online
    Then the session is done once
```

### 7.2 Drill library and eval

```gherkin
# tests/features/drill_coverage.feature
@needs-verification
Feature: Drill coverage
  Scenario: Missing coverage cell
    Given no reviewed drill targets AN-05 for beginners with 2 or fewer players
    When the coverage check runs
    Then it fails and names the empty cell
  Scenario: Starter library
    Given the starter library
    When the coverage check runs
    Then it prints the matrix, counts at least 20 reviewed drills and passes
```

```gherkin
# tests/features/plan_eval.feature
Feature: Rules-only plan eval (NFR-005 a)
  Scenario: A violating plan is caught
    Given a planted plan whose session is longer than the player's time
    When the code graders run
    Then the eval fails and names the case and the rule
  Scenario: The eval set passes at pass^3
    Given at least 30 eval cases
    When each case runs 3 times
    Then every run of every case passes and the 3 runs are identical
```

### 7.3 Privacy and quotas (flags on unless stated)

```gherkin
# tests/features/age_confirmation.feature
Feature: Age confirmation (OQ-05 accepted; wording interim until legal review)
  Scenario: Under-age applicant
    Given Sam is creating an account
    When Sam answers that he is under 18
    Then the account is not created
    And Sam sees why and what he can do instead
  Scenario: Adult confirms
    Given Ivy is creating an account
    When Ivy confirms she is 18 or over
    Then her account is created
  Scenario: Flag off
    Given the age gate is switched off
    When Ivy signs in for the first time
    Then she is not asked her age
```

```gherkin
# tests/features/video_retention.feature
Feature: Video retention (OQ-07 accepted, ADR 0006; legal adequacy open)
  Scenario: Flag off keeps the video
    Given the retention setting is switched off
    When the purge runs
    Then no review video is deleted by the user rule
  Scenario: Retention period passes
    Given Ivy chose "keep video 30 days" for a match analysed 31 days ago
    When the purge runs
    Then the review video is deleted
    And her stats, tags and plan remain
```

```gherkin
# tests/features/training_consent.feature
Feature: Training-data consent (OQ-06 accepted; wording interim until legal review)
  Scenario: User has not opted in
    Given Ivy has not opted in to training use
    When the next label set is built
    Then none of Ivy's matches or corrections are in it
  Scenario: User revokes consent
    Given Ivy opted in and later revokes
    When the next label set is built
    Then none of Ivy's matches are in it
```

```gherkin
# tests/features/rate_limits.feature
Feature: Rate limits and storage quota (OQ-13 accepted; storage quota size (judgment) until P8)
  Scenario: Too many matches
    Given Ivy has created 10 matches in the last hour
    When she starts another
    Then she is told she can start a new match after a stated time
  Scenario: Storage quota
    Given Ivy's videos use her whole storage quota
    When she starts another upload
    Then it is refused before any byte is stored and she sees her usage and limit
```

```gherkin
# tests/features/billing_alerts.feature
Feature: Billing alerts (NFR-022)
  Scenario Outline: Spend thresholds
    Given the monthly budget for <provider> is 100 units
    When spend reaches <spend>
    Then the alert "<alert>" is <state>
    Examples:
      | provider     | spend | alert   | state      |
      | llm          | 49    | 50%     | not firing |
      | llm          | 50    | 50%     | firing     |
      | object_store | 80    | 80%     | firing     |
      | object_store | 100   | 100%    | firing     |
```

### 7.4 Prototype journey and carry-over

```gherkin
# tests/features/e2e_journey.feature (new scenario; QD §7)
Feature: R1 journey
  Scenario: Upload to plan
    Given Ivy signs in on a fresh local stack
    When she uploads a match, Quick Tags it and opens the score sheet and the stats
    And she asks for a plan
    Then every drill in her plan cites a metric, its value, its n and the rallies behind it
    And she can mark a session done offline and swap a drill with "Not for me"
```

```gherkin
# tests/features/red_first_check.feature
Feature: Red-first check (R3-IN-1)
  Scenario: Code without a red step
    Given a PR commit adds backend code with no "Red:" line and no earlier test-only commit
    When the red-first check runs
    Then it fails and names the commit
  Scenario: Test-only commit first
    Given a PR has a test-only commit before the code commit
    When the red-first check runs
    Then it passes
```

```gherkin
# tests/features/compose_extra_ca.feature
Feature: Build behind a TLS-intercepting proxy (VR3-S3-01)
  Scenario: No extra CA
    Given no extra CA file is configured
    When the stack images are built
    Then no build secret is mounted and no CA file is in any image
  Scenario: Extra CA configured
    Given EXTRA_CA_FILE names a CA certificate
    When the stack images are built
    Then the builds trust that CA and the certificate is not in any image layer
```

## 8. Quality gates

Every PR (CI, `ci-gate` required; merge only through `merge_ready.py` on the exact head SHA):

- All Sprint 3 gates unchanged: lint, types (strict on domain modules incl. `racket.coaching`), unit, integration (< 10 min), domain suite (< 10 s, `DOMAIN_TEST_PATHS` gains `tests/unit/coaching`), web checks (Vitest, ESLint, types), E2E Chromium and WebKit with axe, fixture integrity, infra tests, secrets and audit, SBOM and licences, drill lint, PR policy (test immutability, size ≤ 400 or EM waiver), perf baseline.
- New: **`Red:` check** (C4-RED, in `pr-policy`); **drill coverage** (ST-059, in `drill-lint`); **plan eval pass^3** (ST-060); Locust gate on stats/evidence (C4-LOCUST).
- Coverage: changed lines ≥ 85%; `racket.coaching` ≥ 90% line; web ≥ 80% line.
- Mutation (nightly + VERIFY-04): `coaching/plan` + `coaching/weakness` ≥ 0.80 (first gate); rules ≥ 0.85 unchanged.
- Reviews: principal-engineer + named senior reviewer, latest verdicts APPROVE on the current head (PO 2026-10-07; ADR 0050 rule 3: "senior engineer" = a `senior-*` role).
- Separation of duties: no ticket merges, enables auto-merge or touches the policy labels.

## 9. Definition of Done

Ticket DoD (`docs/process/definition-of-done.md` plus):

- Gherkin + IT + unit tests in the PR, written first and seen failing (commit history or `Red:` line), negative case first; docs-only tickets: the named checks.
- Bounded context respected: Coaching domain code imports no FastAPI/SQLAlchemy; Analytics data only through `analytics.public`; ubiquitous language of `coaching.md` and the catalogue.
- `docs/sprints/04/decisions/<ID>.md` with each small decision and its evidence (command + result).
- CI green incl. `ci-gate` on the head; two APPROVE verdicts on the head; merged by the gated merge step.

Sprint DoD:

- Every scorecard row "yes" (G04-01..G04-12), measured live by VERIFY-04 on `main`.
- `make up` + `make demo` + README walkthrough work on a fresh clone (G04-06).
- `merged_verdict.py` rc 0 for every merged Sprint 4 PR (B1); ≤ 20% of PRs with `size-waiver`, median ≤ 300 lines (B4).
- Each verification round's PR merged before the next round (ADR 0050 rule 4); reconciliation row per round.
- Traceability matrix lists the Sprint 4 feature files; retro 3 actions reviewed first in retro 4.

### 9.1 Sprint-DoD rows for human-gated items (PO P12 option b)

| Row | Item | Status at planning |
|---|---|---|
| S4-DoD-P15 | Human coach review of the starter drills (`verified`, FR-141) | not met: waiting on P15 |
| S4-DoD-P16 | Legal review (NFR-070, US + AU) of the age wording, footage notice, consent text and retention windows (values PO-accepted, ADR 0023) | not met: waiting on P16 |
| S4-DoD-P7 | Coach verification of the side-out rule behind the serve/receive split (OQ-08's open part; needs the OQ-01 rulebook) | not met: waiting on P7 |
| S4-DoD-P8 | Storage quota size and monthly budgets (OQ-13) | not met: waiting on P8 |
| S4-DoD-P6 | Screen-reader pass of Sprint 1-4 screens (NFR-027 b) | not met: waiting on P6 |
| S4-DoD-P10 | Repository visibility | not met: waiting on P10 |
| S4-DoD-P11 | Footage bucket provider (gates SPIKE-02/05 and Full Tag on real footage) | not met: waiting on P11 |

## 10. Risks for this sprint

| # | Risk | Mitigation |
|---|---|---|
| R4-1 | CI turns red under new suites (Sprint 3: 5 red `main` runs) | CI-first rule; run new suites on CI in their own PR before dependents; budgets measured on runners |
| R4-2 | Migration head conflicts between parallel BE tickets | PE-4 assigns 0018-0021; dependency chain ST-061a → ST-068a → ST-069 → ST-070; ST-072a has no migration |
| R4-3 | `library.lock` conflicts between drill PRs | ST-058a → b → c in series |
| R4-4 | Settings conflicts between privacy tickets | ST-067 adds every flag and value first |
| R4-5 | Drill content wrong or unsafe (agent-only review) | `@needs-verification`, interim notice, QD-DR-04 safety notes, P15 |
| R4-6 | Offline sync flakiness in E2E | idempotent op ids (ST-062); `--repeat-each=3`, 0 flaky gate |
| R4-7 | Disk below 10 GB on the shared machine | P5 prune; `disk-precheck.sh`; stop own services |
| R4-8 | Tickets grow past 400 lines | slices fixed here; a growing ticket is split by the EM before a waiver |

## 11. Dependencies

- External: P6, P7, P8, P10, P11, P15, P16 (§0.4). None blocks the goal metrics.
- Internal: §3.6 order; dependency ids per ticket in §3.3-§3.5 and the ticket map §15.

## 12. Demo script (sprint review, 2026-12-11)

1. `git clone` → `make up` → `make demo` (prints the stats URL and `https://localhost:3000/plan`). [G04-06]
2. Sign in as Ivy; open the demo match: score sheet with "unofficial" label; stats with n and Wilson ranges. [Sprint 3]
3. Open the plan: weaknesses by rallies lost per game with the serve/receive split (side-out part not yet verified); limited-data banner "based on limited data from 12 rallies". [FR-120, FR-123]
4. Open a drill: "why" names metric, value and n; "Show me" plays the rallies. [FR-122]
5. Go offline (devtools), mark a session done, reload, go online: synced once. [FR-124]
6. "Not for me" on a drill: a different drill for the same metric; session still ≤ 30 min. [FR-124]
7. Generate a new plan as a fresh user with 4 players and a ball machine: different drills, constraints hold. [FR-121]
8. CI: drill coverage matrix and plan eval pass^3 in the latest `main` run. [FR-141, NFR-005a]
9. Restart with `FEATURE_*=1`: age question (under-18 refused), privacy settings, 11th match refused with a time; billing alert rule test. [FR-003/008/009/160, NFR-022]
10. Scorecard: 12 rows with live evidence; the "not met: waiting on P-n" rows. [PO P12]

## 13. Retrospective

`docs/retros/2026-12-11-sprint-04.md`, 4Ls, facilitated by the engineering-manager in RETRO-04. Review retro 3 actions B1-B5 first. Inputs: per-ticket decision files, PR reviews, `merged_verdict.py` audit, VERIFY-04 rounds, CI history.

## 14. Traceability

| FR/NFR | Tickets | Feature file | Scorecard |
|---|---|---|---|
| FR-120 | ST-055, ST-061b | weakness_ranking.feature | G04-01, G04-03 |
| FR-121 | ST-056, ST-061a/b, ST-063b | training_plan.feature | G04-01, G04-03 |
| FR-122 | ST-057, ST-063a | drill_rationale.feature | G04-01, G04-03 |
| FR-123 | ST-057, ST-063a | limited_data_plan.feature | G04-01 |
| FR-124 | ST-062, ST-063c | plan_follow_through.feature | G04-01, G04-07 |
| FR-141 | ST-058a..c, ST-059 | drill_coverage.feature | G04-05 |
| NFR-005 (a) | ST-060 | plan_eval.feature | G04-04 |
| NFR-019 (rules-only) | ST-061b | rules_only_plan_api.feature | G04-02 |
| FR-003 | ST-068a/b | age_confirmation.feature | G04-09 |
| FR-008 | ST-069, ST-071 | video_retention.feature | G04-09 |
| FR-009 | ST-070, ST-071 | training_consent.feature | G04-09 |
| FR-160, NFR-023 | ST-072a/b | rate_limits.feature | G04-10 |
| NFR-022 (R1) | ST-073 | billing_alerts.feature | G04-10 |
| NFR-066 (c) | ST-069 | video_retention.feature | G04-09 |
| QD §7 journey | ST-064, ST-065, ST-066 | e2e_journey.feature, demo_seed.feature | G04-01, G04-06, G04-07 |
| NFR-010, NFR-041 (stats reads) | C4-LOCUST | ci_perf_gates.feature | G04-12 |

## 15. Ticket map (ADR 0047 rule 4; principal-engineer keeps it current)

Every ticket branches from `main` as `s04/<id-lowercase>` (e.g. `s04/st-061b`, `s04/c4-g12`, `s04/qa-harness-4a`) when its dependencies are merged, and opens its PR with its first pushed commit. PR title: `[<ID>] <title>`. The dependency column of §3.1-§3.5 is the source; the structured plan returned to the orchestrator carries the same ids, owners, senior reviewers and dependencies.
