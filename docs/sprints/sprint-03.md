# Sprint 3: Starter stats with uncertainty and evidence; deletion; labelling tools

- **Dates:** Mon 2026-11-16 → Fri 2026-11-27
- **Planning:** 2026-11-16 · **Sprint review:** 2026-11-27 · **Retrospective:** 2026-11-27
- **Retro file:** `docs/retros/2026-11-27-sprint-03.md` from [`docs/retros/TEMPLATE.md`](../retros/TEMPLATE.md). Format: **Start/Stop/Continue**. Focus area: **does the ADR 0037 process work (reconciliation, scheduled deciders, human-gated items)** [EP/ENG-15].
- **Status:** Planned at Sprint 3 planning on **2026-10-06** by the engineering-manager with the product-manager, principal-engineer, business-analyst and senior-qa-engineer (§0). Like Sprints 1 and 2, the work runs in a compressed session before the planned dates; the planned dates are kept for the review and the retro. Branch `sprint-03`, based on `sprint-02` at `ce91984`. The roadmap outline (roadmap §6 "S3") is replaced by this file.
- **Goal scorecard (PO standing rule):** [`docs/sprints/03/goal-scorecard.md`](03/goal-scorecard.md), 12 metrics G03-01..G03-12, each measured on the live local stack.
- **Progress and status:** `docs/sprints/03/progress.md`, `docs/sprints/03/status.json`. Decisions: `docs/sprints/03/decision-log.md`. Blockers and the PO list: `docs/sprints/03/blockers.md`. Findings: `docs/sprints/03/review-rounds.md` (starts with the 14 open Sprint 2 rows). Test changes: `docs/sprints/03/test-change-requests.md`.
- **Related ADRs:** 0003 (rallies-lost unit, FR-109), 0005 (Wilson interval and minimum n, Proposed), 0006 (deletion windows, interim), 0009, 0010, 0014, 0022, 0023, 0029, 0030, 0033, 0035 (gold-set manifest), 0036 (local H.264 browser), 0037 (reconciliation, scheduled deciders, human-gated goal items). Citation prefixes: working-agreement §0.

## 0. Planning record (2026-10-06)

### 0.1 Preconditions

| Precondition | Status at planning | Consequence |
|---|---|---|
| Metric dictionary AN-01..AN-07 at `coach-reviewed` (FR-102: users see only coach-reviewed or verified entries) | **Not met:** every entry is `draft` (`docs/domain/metric-dictionary.md` §3) | Task **COACH-1** (§3.3) on D1-D2: the QD-AN-03 hand count on the 3 golden tag scripts of ST-049, and the D-1/D-2 open issues. ST-044 computes all seven from day 1; ST-048 shows only entries the coach has moved to `coach-reviewed`. The second-reviewer part of QD-AN-03 needs a human (OQ-20, P9): see §0.4 |
| ADR 0005 (Wilson 95%, n < 20 or width > 30 points, count metrics < 2 games) | **Proposed** | Task **PM-1** + **COACH-1** on D1: accept or amend. Built meanwhile to the FR-101 values, all as configuration, so an amendment is a config change plus a TCR row |
| Analytics design: `MetricSnapshot`, recompute on `RallyScored`/`ScoreCorrected`, idempotency, versions (sprint-02 §4 PE task "D9: Analytics design note") | **Not met:** only the context canvas `docs/architecture/contexts/analytics.md` exists | Task **PE-2** on D1 with a design review on D2 (BE, QA, coach, security). ST-044 (pure computation) starts on D1 because it does not depend on the snapshot design; ST-046 starts after the review |
| API contract for Sprint 3 (stats, evidence, delete match, delete account, labels) | **Not met:** no `docs/architecture/api-sprint-03.md` | Task **PE-1** on D1-D2. Until then the harness assumptions live only in `scripts/measure/statscontract.py` (decision-log 2026-10-06) |
| Deletion and purge design (soft delete, hidden ≤ 1 min, purge ≤ 7 days, store and DB, idempotent retries) | **Not met** | Task **PE-3** (with security SEC-1 threat notes) on D1-D2. ST-050/ST-051 start after it |
| Flows for the stats dashboard (D-), evidence (E-), deletion (X-) and Full Tag (L-) with all states, HAX and WCAG checklists | **Not met:** only `flows-sprint-01.md` and `flows-sprint-02.md` exist | Task **PD-1** on D1-D2, then **DR-03** (design review) on D3 with FE, coach, BA, PM, security, each invoked with a brief (ADR 0037 rule 2). **No Sprint 3 UI story starts before DR-03 is held**, unless the PO records a waiver first |
| Sprint 2 design reviews DR-01, DR-02 | **Not held** (6 of the 14 open Sprint 2 rows) | Decider tasks **DR-01**, **DR-02** on D1, each decider invoked with its brief (§3.3) |
| Sprint 2 merged, CI green at the head | **Not met:** PR #2 red on PR policy (TCR rows 24-28 undecided, no size waiver) | C3-01 (QA) and C3-05 (SRE, orchestrator, PO labels) first |
| OQ-01 rulebook (P7, need-by 2026-11-16) | **Not supplied** | Scoring stays `PROVISIONAL-UNVERIFIED`. AN-01, AN-02, AN-03, AN-05 and AN-06 read the provisional score sequence, so every metric card carries the same "unofficial scoring (rules not yet verified)" notice as the score sheet (metric-dictionary rule 0.5, FR-055) |
| OQ-13 spend (P8) | **Not answered** | SPIKE-04 (GPU provider) is **not** in this sprint (§0.5) |

These are recorded as an Open row in `docs/sprints/03/blockers.md`. The stories in §3 are **Ready on condition** (§14.2): each condition has an owner and a day.

### 0.2 Product-owner decisions applied (ADR 0023; `docs/requirements/po-input-2026-10-05.md`)

- **Accept all recommendations.** Nothing here departs from an accepted OQ recommendation. ADR 0006 deletion windows are the PO's interim defaults: hidden ≤ 1 min, purged ≤ 7 days, abandoned uploads freed ≤ 24 h.
- **Jurisdictions US and AU (OQ-05).** No real-user beta in Sprint 3. Account and match deletion are written so that the NFR-070 legal review can check them against both (security threat notes SEC-1 name the AU APP 11.2 and US state-law questions as open, not as claims).
- **https for the dev stack, no insecure-cookie flag (ADR 0029).** Every live method runs over https through `web-tls`. No story may add an insecure-cookie switch; account deletion signs out through the same `__Host-` cookie path.
- **Rulebook PDFs later (OQ-01).** Presets stay `PROVISIONAL-UNVERIFIED`; rule-dependent scenarios keep `@needs-verification`; the score sheet and every metric card say "unofficial". Rule-dependent metric rows count toward no Must FR (QD-QG-P5).
- **Go port in S6 (PO 2026-10-06).** Nothing in Sprint 3 changes for it, except that every new behaviour is pinned by a language-independent test (Gherkin, HTTP-level IT, Playwright, live scorecard), which the port reuses (judgment).
- **Repository is public (P10 open).** Nothing in this sprint may rely on the repository being private: no consented footage, no labels of real people and no secrets go into git (gold-capture protocol §2 step 6).

### 0.3 Retro 2 actions applied (`docs/retros/2026-11-13-sprint-02.md` §7)

| Action | How this plan applies it |
|---|---|
| A1 P6, P10, P11 to the PO; escalate DR-02 | The Sprint 3 PO list (blockers.md row 1) repeats P6-P11 with dates and adds P12 (§0.4). DR-02 is a decider task on D1, not a hope |
| A2 Hold DR-02 and finish DR-01 with every decider invoked | §3.3 tasks DR-01 and DR-02: chair principal-designer; each decider (FE, coach, BA, PM, security) gets its own brief and runs on D1. Their routed rows PD-RV2-DR-* close only by a decision written in the flows file |
| A3 Agent-owned blockers/majors red-first before any Sprint 3 story | C3-01..C3-05 are the first items of their lanes (§3.2): QA-RV3-02, PE-S2-R3-02 then PE-S2-R3-01, QA-RV3-04, PE-S2-R3-03 |
| A4 CI and smoke at the close head, merge chain | C3-05 (SRE with the orchestrator): green `ci-gate` at the `sprint-02` head, `smoke.md` "Sprint-close head", merge `sprint-02` → `sprint-01`, PR #1 → `main`, first nightly. Same step again at the Sprint 3 close (SRE-SMOKE-3) |
| A5 ADR 0037 from planning | Reconciliation step after every review and verification round (§4 EM row); decider tasks scheduled with briefs and dates (§3.3); human-gated goal items put to the PO at planning (§0.4) |

### 0.4 Goal items that depend on a human input (ADR 0037 rule 3)

The session that builds Sprint 3 is compressed (it runs on 2026-10-06/07); every PO need-by date below falls after it. The PO is asked at planning (blockers.md row 1, item P12) to choose for each item: **(a)** supply the input before the close, or **(b)** move the item out of the goal into a named sprint-DoD row reported as "not met: waiting on P-n". **Until the PO answers, each item stays in the goal** (G03-12 counts its open row).

| Item | Open row(s) | Waits on | Need-by | Default with no answer |
|---|---|---|---|---|
| Manual VoiceOver/TalkBack pass of Sprint 1-3 screens (NFR-027 b) | QA-R3-GATE-01 / C-06 (major) | P6 tester with devices | 2026-11-13 (overdue at Sprint 3 start) | Stays in G03-12 |
| Repository visibility | SEC-RV3-01 (major) | P10 make private or confirm public | 2026-11-16 | Stays in G03-12 |
| Private footage bucket | BLK-GOLD-01 (major) | P11 provider | 2026-11-16 | Stays in G03-12 |
| Second reviewer of the metric dictionary (QD-AN-03: "a second coach or a 4.0+ player recomputes 1 match") | none yet; it gates `coach-reviewed` if the coach reads QD-AN-03 as requiring it | P9 (OQ-20) recruits | 2026-11-16 | The coach decides on D1 whether `coach-reviewed` needs the second recompute or whether it is the step to `verified` (COACH-1 brief). If it needs it, goal bullet 1 cannot be met without P9, and P12 asks the PO for (a) or (b) |

ST-025 (phone recordings, P3) is **not** in the goal; it stays ML stretch.

### 0.5 What changed from the outline (roadmap §6 "S3")

- **Carry-over first:** about 5 agent units (C3-01..C3-05) plus the decider tasks DR-01, DR-02 (retro 2 A2-A5).
- **Pulled in:** ST-038 (abandoned uploads expire; it shares the purge job with ST-050) and ST-042 (worker least-privilege credentials, moved here by the Sprint 2 plan). Both are gates before any non-dev deployment (S5 release candidate).
- **Out:** SPIKE-04 (P8 unanswered). FR-047 (gaps and resync) stays stretch, as do ST-035, ST-034, ST-033 and ST-036 from Sprint 2.
- **FR-151 scope:** the manifest format and checks exist (ST-011, ST-040, ADR 0035). Sprint 3 adds the first analytics gold set **GS-AN-1 v1** (the 3 golden tag scripts of ST-049, frozen) and the Full Tag export in the gold-label-schema format (ST-052). No footage of people (P11, P10).
- **Full Tag consent:** training consent (FR-009) is a Sprint 4 story. Sprint 3's Full Tag tool opens only matches with a team-held consent record written by the labeller-admin CLI (ST-052) and refuses every other match. It is shown on the synthetic clip (no people).
- **New rows:** C3-01..C3-10, QA-ACC-3, QA-FUZZ-3, SRE-PURGE, SRE-SMOKE-3, the decider tasks (§3.3), IT-03-01..IT-03-14, E2E-03-01..E2E-03-07, story cards and the DoR check (§14), build lanes (§15).

## 1. Sprint goal

- A player opens the stats of a tagged match and sees the 7 starter stats per side (AN-01..AN-07). Each shows its sample size n; each proportion shows a 95% Wilson interval; small samples are flagged "low sample" in text, de-emphasised and never hidden. The values equal the coach's hand count, update after every tag or correction, and carry the "unofficial scoring (rules not yet verified)" notice. Only `coach-reviewed` metrics are shown, each with "How is this measured?".
- Every stat has "Show me": up to 10 of the rallies behind it, with "see all n", each opening the video at that rally.
- A player can delete a match or their whole account. It is gone from the account within 1 minute; the purge then leaves no row and no stored object behind; deleting the account signs out every session.
- The team can Full Tag a consented match (labeller role only, frame by frame) and export the labels in the gold-set format; drill files are checked by a schema lint in CI.
- The Sprint 2 blockers and majors that agents own are fixed first (C3-01..C3-05), the DR-01/DR-02 decisions are made, and no blocker or major is open at the close (human-gated items as agreed with the PO, §0.4).

**How it is measured:** the 12 metrics of [`03/goal-scorecard.md`](03/goal-scorecard.md), on the live local stack over https (PO standing rule).

**Stretch, not goal:** ST-035 singles (a), ST-034 mid-game start (a), ST-033 correction consequences, ST-036 gaps and resync, ST-025 (only with P3 clips).

**Not in this sprint:** weakness ranking and training plans (Sprint 4), the drill library content (FR-141, Sprint 4; this sprint only the schema and lint), retention settings and training consent (FR-008, FR-009, Sprint 4), trends (FR-104, R2), GPU spike (P8).

## 2. Capacity (ADR 0010)

Load factor **0.8 (12.8 units per lane)**, kept from Sprints 1-2 (decision-log 2026-10-06: implemented ratios 0.906 and 0.978, `dod_done` 0 and 0 for external reasons only; retro 2 §8). The minors of the carry-over (C3-10) go into the review-loop reserve, the uncommitted rest of each lane.

| Lane | Committed | Stretch (in order) | Streams (ADR 0010, ≤ 2, disjoint) |
|---|---|---|---|
| BE | 12.5: ST-043 0.5, ST-044 2, ST-045 1, ST-046 2, ST-047 (API) 1, ST-050 (API, purge) 2, ST-051 (API) 2, ST-038 1, ST-042 (grants) 1 | ST-035 1, ST-034 1, BE minors (SEC-RV3-02, SEC-S2-TM-03-DOC) | 1: `analytics` and the `sports/pickleball` metric dictionary (ST-043..ST-047). 2: `platform` purge job, `players` account deletion, `matches` deletion, `video_ingest` expiry, migrations (ST-050, ST-051, ST-038, ST-042) |
| FE | 11.0: C3-03 1, ST-048 4, ST-047 (UI) 2, ST-050 (UI) 1, ST-051 (UI) 1, ST-052 (UI) 2 | FE minors PD-R3S2-01, PD-R3S2-02, PE-S2-R3-08, then ST-034 (UI) 0.5, ST-033 | 1: stats dashboard and evidence (`web/src/app/matches/[matchId]/stats`). 2: deletion and account (`web/src/app/settings`, match menu), then Full Tag (`web/src/app/label`) |
| QA | 9.5: C3-01 0.5, QA-ACC-3 2, QA-FUZZ-3 1, ST-049 2, ST-054 (QA) 2, C3-06 0.5, scorecard dry-runs 1, QA minors (QA-RV3-06, SEC-RV3-03) 0.5 | — | 1: golden matches, scenario steps, fuzz, ITs (`backend/tests`, `tests/features`). 2: Playwright specs, timing, crawl (`web/e2e`) |
| SRE | 7.0: C3-04 0.5, C3-05 0.5, ST-042 (Compose roles, S3 identity) 1, SRE-PURGE 1, ST-054 (SRE) 1, SRE-SMOKE-3 1, C3-08 bucket 1 (only once P11 names the provider), SRE minors 1 | — | 1: CI, Locust, smoke (`.github/`, `infra/tests`, `scripts/ci`). 2: Compose, roles, scheduler, object store (`infra/compose.yaml`, `infra/docker`, `infra/tls`) |
| ML | 3.0: ST-052 (labels API, consent record, export) 2, ST-053 1 | ST-025 1 (only with P3 clips) | 1: `backend/src/racket/dataset`, drill schema and lint (`backend/src/racket/coaching/drills`, `content/drills`), `docs/data` |
| **Total** | **43.0** | | |

The BE lane is the bottleneck (12.5 of 12.8). If ST-050's purge takes more than its size, ST-038 moves to stretch first, with the PO told (it stays a gate before any non-dev deployment). The FE lane has 1.8 units of reserve for C3-03 follow-ups and the DR-02 FE follow-ups (judgment).

## 3. Committed backlog

### 3.1 Carry-over from Sprint 2 (first in each lane; retro 2 A3, A4)

Every row is an open Sprint 2 blocker or major, copied as an Open row into `docs/sprints/03/review-rounds.md` at planning (`python3 scripts/measure/open_defects.py docs/sprints/02/review-rounds.md` → rc=1, open 14).

| Row | Finding(s) | Work | Owner (R) | Reviewer | Size |
|---|---|---|---|---|---|
| C3-01 | QA-RV3-02 (blocker) | Decide TCR rows 24-28 of `docs/sprints/02/test-change-requests.md` (accept, or reject with the change reverted by its owner red-first); then 0 pending, so `qa-approved-test-change` may go on PR #2 | senior-qa-engineer | principal-engineer | XS |
| C3-02 | PE-S2-R3-02 (major) | Amend `api-sprint-02.md` §3/§4.2 and `match-aggregate.md` §4/§8: `decision/not_last_in_game` and "latest kept rally first"; `tagcontract.py` unchanged unless a route moves | principal-engineer | senior-frontend-engineer, senior-backend-engineer | 0 (docs task PE-4) |
| C3-03 | PE-S2-R3-01 (major) | S-01 offers "Move rally n to the next game" only on the latest kept rally; the client reads the `decision/not_last_in_game` field code and says why, not "Try again". Red first: a Vitest case and E2E-03-07 | senior-frontend-engineer | principal-designer, senior-qa-engineer | S |
| C3-04 | QA-RV3-04 (major) | `scripts/dev-chrome.sh`: installs Chrome for Testing at the ADR 0036 version with its sha256 check, idempotent; infra test first | sre-devops-engineer | senior-qa-engineer | XS |
| C3-05 | PE-S2-R3-03 (major); retro 2 A4 | Dispatch CI at the `sprint-02` head; fill `docs/sprints/02/smoke.md` "Sprint-close head"; EM records the PR size waiver; after C3-01, labels and merge `sprint-02` → `sprint-01`, PR #1 → `main`; dispatch the first `nightly-quality.yml` | sre-devops-engineer with the orchestrator; human PO (labels, merge) | senior-qa-engineer | XS |
| C3-06 | QA-R3-GATE-01 / C-06 (major) | Manual screen-reader pass (24 rows of `docs/sprints/02/a11y-manual.md`, plus the Sprint 3 screens D/E/X/L added by QA) by a human tester | senior-qa-engineer (plan, record); human PO (P6) | principal-designer | XS (agent part) |
| C3-07 | SEC-RV3-01 (major) | Repository visibility: the PO makes it private or confirms public; the record is corrected from the GitHub API, not from memory (retro 2 L5) | human PO (P10); engineering-manager (record) | security-privacy-engineer | — |
| C3-08 | BLK-GOLD-01 (major) | Private footage bucket and access policy once the PO names the provider (P11) | sre-devops-engineer; security-privacy-engineer (policy review) | security-privacy-engineer | S (only after P11) |
| C3-09 | PD-R1-06 / DR-01 / DR-02 family (blocker) and PD-RV2-DR-FE, -COACH, -BA, -PM (blockers), -SEC (major) | Decider tasks DR-01 and DR-02 (§3.3) | principal-designer (chair) and the named deciders | — | 0 units (decisions) |
| C3-10 | Minors and nits: PE-S2-R3-07 / SEC-S2-TM-03-DOC, PE-S2-R3-08, PE-S2-R3-09, SEC-RV3-02, SEC-RV3-03, SEC-RV3-04, SEC-S2-TM-04/-05/-07, QA-RV3-06, PD-R3S2-01, PD-R3S2-02, PD-FL2-03/-05, VR1-01 | Each as described in its Sprint 2 row; review-loop reserve. SEC-RV3-02 (refuse a dev key outside dev/test) is due before any non-dev deployment | the owner named in its Sprint 2 row | the reviewer that raised it | about 3 units across lanes |

### 3.2 New stories

| Story | Title | FR / NFR | Owner (R) | Required reviewers | Size | Depends on |
|---|---|---|---|---|---|---|
| ST-043 | Metric dictionary in code: versioned entries AN-01..AN-07 with status; only `coach-reviewed`/`verified` entries reach the API | FR-102; NFR-075 | BE | QA, pickleball-domain-coach | XS | COACH-1 (statuses), PE-2 |
| ST-044 | Starter stats AN-01..AN-07 computed from the projected score sheet, per side and per tagged player, with n, Wilson 95% interval and the low-sample rule from config | FR-100, FR-101; NFR-004; ADR 0005 | BE | QA, pickleball-domain-coach, principal-engineer | M | ST-026 (Sprint 2 projection) |
| ST-045 | Attribution conservation: every rally lost is attributed once (categories + "unattributed"), split serve/receive, checked on every computation | FR-109; ADR 0003 | BE | QA, principal-engineer | S | ST-044 |
| ST-046 | `MetricSnapshot` recomputed on `RallyScored`/`ScoreCorrected` (idempotent, versioned by `metric_def_version` and `rules_version`); `GET /matches/{id}/stats` | FR-100; NFR-010, NFR-017 (analogue), NFR-051, NFR-075 | BE | QA, principal-engineer, security-privacy-engineer (BOLA) | M | PE-1, PE-2 review |
| ST-047 | "Show me": up to 10 rallies behind each metric and side, "see all n", each opening the video moment | FR-103, FR-027; NFR-038, NFR-014 | BE (S) + FE (M) | QA, principal-designer | S+M | ST-046; DR-03 (UI) |
| ST-048 | Stats dashboard: metric cards with value, n, interval, low-sample text, "How is this measured?", unofficial notice; empty, loading, error and low-sample states; 360 px | FR-100, FR-101, FR-102, FR-055; NFR-011, NFR-027, NFR-033, NFR-034, NFR-039 | FE | QA, principal-designer, pickleball-domain-coach | L | ST-046; DR-03 |
| ST-049 | Golden matches QD-GD-03: 3 tagged golden matches with the coach's hand counts, frozen as gold set GS-AN-1 v1; the regression asserts exact equality | NFR-004; FR-151 | QA | pickleball-domain-coach, principal-engineer | M | COACH-1 |
| ST-050 | Delete a match: confirmation that states the consequences; hidden ≤ 1 min; purge job removes every row and stored object ≤ 7 days; idempotent and retried | FR-006; NFR-066 (a, b); ADR 0006 | BE (M) + FE (S) | QA, security-privacy-engineer, principal-engineer | M+S | PE-3, SEC-1; DR-03 (UI) |
| ST-051 | Delete my account: every match deleted as in ST-050, profiles and sessions removed, signed out everywhere; signing in again with the address gives a new, empty account | FR-007; NFR-066 (b), NFR-057 | BE (M) + FE (S) | QA, security-privacy-engineer | M+S | ST-050; PM-1 (re-sign-in rule) |
| ST-038 (carried) | Abandoned uploads expire after 24 h (config); bytes freed; not listed or resumable; runs on the ST-050 purge job | FR-024; NFR-066 (d) | BE | QA, security-privacy-engineer | S | ST-050 job runner |
| ST-042 (carried) | Least-privilege credentials for the media sandbox worker: own Postgres role (SELECT/UPDATE on job, media, upload tables only; nothing on `sessions`, `sign_in_*`, `accounts`), own S3 key | NFR-054 | BE (grants, S) + SRE (Compose roles, S3 identity, S) | security-privacy-engineer, principal-engineer | S+S | — |
| ST-052 | Full Tag labelling tool (internal): labeller role; consented matches only; frame stepping; hit, bounce, hitter, rally boundary, outcome tags; export in `gold-label-schema` v1 | FR-150, FR-151; NFR-078 | ML (M) + FE (M) | QA, security-privacy-engineer (role, consent), principal-designer | M+M | PE-1; DR-03 (UI) |
| ST-053 | Drill JSON Schema and CI lint: unknown metric, unknown or cyclic progression, duration > 45 min, success criterion without a number, no source or rationale → fail naming drill and reason; deprecate, never delete; edits bump the version | FR-140 | ML | QA, pickleball-domain-coach | S | ST-043 (metric ids) |
| ST-054 | E2E journey v2 and stats performance baseline: Playwright journey to stats, evidence and deletion; evidence crawl; dashboard timing and layout shift (QA). Locust on stats and evidence at 50 RPS in CI, and `tests/unit/analytics` added to CI's `DOMAIN_TEST_PATHS` so NFR-073 covers the new domain code (SRE) | NFR-010, NFR-011, NFR-038, NFR-039 | QA (M) + SRE (S) | principal-engineer, sre-devops-engineer | M+S | ST-048, ST-047 |

**Planning additions (2026-10-06, engineering-manager):**

| Row | Title | FR / NFR | Owner (R) | Required reviewers | Size | Depends on |
|---|---|---|---|---|---|---|
| QA-ACC-3 | Acceptance first: step modules for §7.1-§7.6, the IT-03 files and E2E-03-01..07 written red before their stories (`red_until` the story) | FR-006, FR-007, FR-100..FR-103, FR-109, FR-140, FR-150 | QA | principal-engineer (contract use), principal-designer (states) | M | PE-1 (D2), PD-1 (D2) |
| QA-FUZZ-3 | Rule L11 on every new JSON string field (delete confirmations, label bodies, consent record); a concurrency case for every new limit (parallel delete + tag; parallel purge runs) | NFR-023, NFR-058 | QA | security-privacy-engineer | S | — |
| SRE-PURGE | The purge/expiry job runs on a schedule in Compose (at least daily, NFR-066 c) and once on demand (`--once`) for evidence; object-store deletes through the app's key only; job health visible in logs and the tracing UI | NFR-066 (c), NFR-047 | SRE | senior-backend-engineer, security-privacy-engineer | S | ST-050 job |
| SRE-SMOKE-3 | Integration smoke before review round 1 and at the sprint-close head, isolated and self-cleaning (ADR 0022, ADR 0033 rule 3), in `docs/sprints/03/smoke.md` | working-agreement §7 step 1a | SRE | senior-qa-engineer | S | integrated tree |

**Stretch, in this order:** ST-035, ST-034, ST-033, ST-036 (cards in sprint-02 §3), then the lane minors. A stretch story starts only when its lane's committed stories are implemented and their review round 1 is held.

### 3.3 Decider and design tasks (ADR 0037 rule 2: scheduled like lanes)

D1 = 2026-11-16 (in the compressed session: **step 1**, before any lane writes UI or ST-046/ST-050 code). D2 = 2026-11-17 (step 2). D3 = 2026-11-18 (step 3). The orchestrator invokes each role on its day with the brief below; the EM checks the output exists before the dependent story starts.

| Task | Role | Brief (objective · output · done-check) | Date |
|---|---|---|---|
| DR-02 | principal-designer (chair) | Hold the Sprint 2 flows review: collect each decider's answer below into `flows-sprint-02.md` §13.1 R2-1..R2-7, record the outcome, amend the flows. Done: every cell filled or explicitly escalated to the PO | D1 |
| DR-02-FE | senior-frontend-engineer | Answer R2-2 and R2-5 in `flows-sprint-02.md` §13.1 (feasibility, the chosen state behaviour). Output: your text in the cell, signed and dated. Done: cell not empty | D1 |
| DR-02-COACH | pickleball-domain-coach | Answer R2-4 and R2-7 (domain wording of calls, endings, conflict copy). Done: cells filled | D1 |
| DR-02-BA | business-analyst | Answer R2-3 (requirement trace and acceptance wording). Done: cell filled | D1 |
| DR-02-PM | product-manager | Answer R2-5 and R2-7 (priority and scope of the options). Done: cells filled | D1 |
| DR-02-SEC | security-privacy-engineer | Answer R2-6 (security wording). If you cannot write files, return the text; the chair commits it attributed to you | D1 |
| DR-01 | principal-designer with the same deciders | Finish `flows-sprint-01.md` §10.1 (R-1..R-6, D-8 consent line PD-R2R-03) the same way | D1 |
| COACH-1 | pickleball-domain-coach | (1) Run QD-AN-03 on the 3 golden tag scripts of ST-049: hand-count AN-01..AN-07 and write the values in `docs/domain/metric-dictionary.md` §2b; (2) decide open issues D-2 (forced vs unforced) and AN-02's UI name; (3) say whether `coach-reviewed` needs the second recompute (OQ-20) or whether that is the step to `verified`; (4) move each entry to `coach-reviewed` only when (1) matches the reference `scripts/measure/statslib.py` exactly; (5) review ADR 0005 thresholds. Done: review record row per entry | D1-D2 |
| PM-1 | product-manager | Confirm the §3 priorities and the re-plan; decide FR-007's re-sign-in rule (new empty account vs refused); chase P6-P12; accept or amend ADR 0005 with the coach | D1 |
| PE-1 | principal-engineer | `docs/architecture/api-sprint-03.md`: stats and evidence shapes, delete match / account (status codes, confirmation body), Full Tag label routes, consent record, error codes, BOLA rows; update `scripts/measure/statscontract.py` in the same commit; dry-run G03-01..G03-05 with the method authors | D1-D2 |
| PE-2 | principal-engineer (chair), reviewers BE, QA, coach, security | `docs/architecture/analytics-snapshots.md`: `MetricSnapshot` aggregate, event consumption (outbox or in-transaction, idempotency key), recompute scope, versions, read model; design review held and recorded | D1 (doc), D2 (review) |
| PE-3 | principal-engineer with security-privacy-engineer | Deletion and purge design (in `api-sprint-03.md` §deletion or its own doc): soft delete, hide, purge order (objects then rows, or the reverse with an outbox), retries, idempotency, audit, what remains (nothing), the purge CLI name for the scorecard | D1-D2 |
| PE-4 | principal-engineer | C3-02 contract amendment | D1 |
| PD-1 | principal-designer | `docs/design/flows-sprint-03.md`: D- (dashboard), E- (evidence), X- (delete match, delete account), L- (Full Tag) with all states (empty, loading, error, low-sample, draft hidden, deleted), HAX and WCAG checklists, screen ids for axe attachments | D1-D2 |
| DR-03 | principal-designer (chair) with FE, coach, BA, PM, security, each invoked with a brief | Review `flows-sprint-03.md`; record the outcome. **No Sprint 3 UI story starts before this is held** | D3 |
| SEC-1 | security-privacy-engineer | Threat notes: deletion completeness and ordering (objects, rows, logs, backups out of scope with the reason), account deletion and session revocation, BOLA on new routes, labeller role privilege and consent check, ST-042 grants; the AU/US questions for NFR-070 as open items. If you cannot write files, return the text; the EM commits it attributed to you | D1-D2 |
| BA-1 | business-analyst | §14 cards and DoR (done at planning with the EM); traceability rows for the Sprint 3 feature files; Sprint 4 stories (weakness ranking, plan, drills content, age gate, retention, consent, quotas) to DoR | D2, D8 |

### 3.4 Acceptance notes per story

- **ST-043:** the dictionary is data (one file per sport plug-in, `sports/pickleball/metrics.json` or similar, PE-2 decides), each entry with id, version, name, plain-language definition, formula text, unit, data level, min sample, owner, status, source. A `draft` entry never reaches the stats response or the UI (FR-102). Changing a definition bumps its version; old snapshots keep their version (NFR-075).
- **ST-044:** pure functions over the projected sheet (no I/O). Rules 0.1-0.6 of the metric dictionary: replays and rallies after a game end ("needs your decision") are excluded; attribution is derived (winner → winning side; error/fault → losing side); per player only where `responsible_player` is tagged, never spread. Thresholds in config. The worked example in metric-dictionary §2 is the first unit test, then the golden matches (ST-049).
- **ST-045:** for each game and side: attributed + unattributed rallies lost = total rallies lost, separately on serve and on receive (FR-109). A property test with ≥ 1,000 generated matches (profile `ci`) finds 0 violations.
- **ST-046:** recompute is idempotent (the same event twice gives one snapshot version), runs after the scoring transaction commits (one aggregate per transaction, ddd-guidelines §4.1), and the stats are current within 5 s p95 of a tag or correction (NFR-017's target, used as an analogue, judgment). Stats response carries `rules_version`, `metric_def_version`, `unofficial` and the label. BOLA: 404 for another account.
- **ST-047:** ≤ 10 rallies per metric and side, ordered by rally time, with total n ("see all n" lists them all, paginated). Each item opens the rally video at its start (FR-027, the Sprint 2 media link, TTL ≤ 15 min). The crawl (NFR-038 a) finds 0 metric without a working link; no metric is shown without n (NFR-038 b).
- **ST-048:** values with printed numbers (no colour-only meaning, NFR-034); low-sample flag in text plus de-emphasis (FR-101); AN-07 as a stacked bar with printed values per segment; "How is this measured?" shows the plain-language definition; the unofficial notice is on the page; interactive ≤ 2.0 s p95 warm (NFR-011); no layout shift when values load (NFR-039); 320/360 px without sideways scroll.
- **ST-049:** 3 golden matches (one 2-game, one 3-game, one with corrections and needs-decision rallies), each a tag script under the provisional preset; the coach's hand counts are the expected values; the manifest GS-AN-1 v1 records sha256, rules version, metric-dictionary version and labeller role (FR-151); the regression fails naming metric, side and match on any difference (NFR-004).
- **ST-050:** confirmation names what goes (video, tags, stats, derived files) and that it cannot be undone (DES FR-UX-90); hidden for the owner within 1 min (in practice in the same request, judgment); the purge removes every DB row referencing the match and every stored object; the IT asserts storage and DB empty (NFR-066 b); deletion is audited by pseudonymous id only (NFR-057). Plans do not exist yet, so FR-006's "evidence removed" note is Sprint 4's (out of scope).
- **ST-051:** every session of the account is revoked (two devices → both 401); every match purged as ST-050; the address is no longer linked to any data; re-sign-in behaviour per PM-1 (default: a new, empty account).
- **ST-038:** an upload not finished within 24 h (config) is expired by the purge job: bytes freed, not listed, not resumable (HEAD/PATCH → 404/410 per contract).
- **ST-042:** a worker-uid process cannot read `sessions`, `sign_in_*` or `accounts` (a test reads them and gets a permission error); the worker uses its own S3 key limited to the media buckets.
- **ST-052:** the route and page answer 404 to a non-labeller (FR-150 "not available"); a match without a consent record is refused; frame stepping by keys (`,`/`.`) and buttons, no dragging (NFR-030); export validates against `docs/data/gold-label-schema.md` v1 and contains the tagged frame and player.
- **ST-053:** the lint is a CLI and a CI job; each failure rule has a negative fixture; the valid fixture passes; deprecated drills keep their content (FR-140).
- **ST-054:** Playwright journey v2 (sign in → upload → tag the worked example → stats = reference → Show me plays → delete match → gone); Locust stats/evidence at 50 RPS recorded (NFR-010 baseline, gate at S5).

### 3.5 Order of work per lane (retro 2 A3)

1. **BE:** ST-044 (pure, D1) → ST-043 (after COACH-1) → ST-045 → ST-046 (after PE-2 review) → ST-047 API → ST-050 (after PE-3) → ST-051 → ST-038 → ST-042 grants → stretch.
2. **FE:** C3-03 (red first, D1) → DR-02 FE follow-ups → after DR-03: ST-048 → ST-047 UI → ST-050 UI → ST-051 UI → ST-052 UI → minors.
3. **QA:** C3-01 (D1, before anything else) → QA-FUZZ-3 → ST-049 (with COACH-1) → QA-ACC-3 → ST-054 → C3-06 (with the human) → scorecard dry-runs → minors.
4. **SRE:** C3-04 → C3-05 → ST-042 Compose half → SRE-PURGE → ST-054 Locust → SRE-SMOKE-3 → C3-08 when P11 is answered.
5. **ML:** ST-053 → ST-052 backend; ST-025 when P3 is answered.

## 4. Task breakdown per role agent

| Agent | Tasks | Due | Done-check |
|---|---|---|---|
| engineering-manager | D0: this plan, scorecard, carried rows, PO list P6-P12. Brief each lane with slices (≤ 400 changed lines, waivers before the commit). Brief each decider task of §3.3 on its day. **After every review and verification round: the ADR 0037 reconciliation step** (returned ids vs `review-rounds.md` rows, Open rows for missing ids, `open_defects.py` output with the counts) before the next step. EM status step after every fix round (`status.json`, `progress.md`, sprint-report §1). D10: retro | D0, each round, D10 | `open_defects.py` equals the reviewers' returned ids every round; no decision cell older than its date |
| product-manager | PM-1; DR-02-PM; DR-03; P-list chasing | D1, D3 | Answers in `decision-log.md` or the flows file |
| business-analyst | BA-1; DR-02-BA; DR-03 | D1, D2, D8 | Sprint 4 stories meet DoR; traceability lists Sprint 3 feature files |
| principal-engineer | PE-1..PE-4; review ST-044..ST-046 (aggregate and event rules), ST-050/051 (ordering) | D1-D2 | Docs Accepted; `statscontract.py` aligned; G03-01..G03-05 dry-run rows |
| principal-designer | DR-01, DR-02 (chair); PD-1; DR-03 (chair); review all Sprint 3 UI | D1-D3 | Flows approved before any UI story starts |
| security-privacy-engineer | SEC-1; DR-02-SEC; DR-03; review ST-042, ST-050, ST-051, ST-052, QA-FUZZ-3; SEC-RV3-04 text | D1-D2, reviews | Notes attached to the story cards; controls named as acceptance criteria |
| pickleball-domain-coach | COACH-1; DR-02-COACH; DR-03; review ST-044, ST-049, ST-053 and every metric wording | D1-D2, reviews | Each AN entry `coach-reviewed` with a review-record row, or the reason it is not |
| senior-backend-engineer | §3.5 BE order | D1-D9 | IT-03 ids of its stories green; scenarios green |
| senior-frontend-engineer | §3.5 FE order | D1-D9 | Playwright, axe, keyboard and timing journeys green |
| senior-qa-engineer | §3.5 QA order; sprint test report | D1-D10 | Every QA-owned method has a dry-run row; report separates `@needs-verification` |
| sre-devops-engineer | §3.5 SRE order; G03-05 dry-run | D1-D9 | CI green at the head; smoke at the integrated head and the close head |
| senior-ml-cv-engineer | §3.5 ML order | D2-D8 | Lint job in CI; export validates; Full Tag ITs green |

## 5. TDD plan (negative case first) [EP/ENG-18]

| Domain object / unit | Context | First tests, in order |
|---|---|---|
| `wilson(k, n)` | analytics | 1. k > n or negative → error; 2. n = 0 → no interval; 3. k = 0 lower bound exactly 0, k = n upper exactly 1; 4. 22/40 → 0.398-0.693 |
| `LowSamplePolicy` | analytics | 1. n < min → flagged; 2. width > 0.30 at n ≥ 20 → flagged (10/20); 3. 22/40 → not flagged; 4. count metric with 1 game → flagged; thresholds from config |
| `StarterStats` (AN-01..AN-07) | analytics | 1. an empty sheet → every metric n = 0, flagged, no value; 2. replays and needs-decision rallies excluded; 3. the metric-dictionary §2 worked example exactly; 4. per-player AN-04 never spreads untagged rallies; 5. AN-05 lower bound flagged when a serving-side fault has no subtype |
| `Attribution` (FR-109) | analytics | 1. a rally attributed twice → invariant error; 2. a lost rally missing → invariant error; 3. property: ≥ 1,000 generated matches, attributed + unattributed = lost on serve and receive |
| `MetricDictionary` | sports/pickleball → analytics | 1. unknown status → error; 2. duplicate id → error; 3. draft entries filtered out of the published set; 4. version bump on a definition change (fixture diff) |
| `MetricSnapshot` | analytics | 1. the same event twice → one version; 2. a correction event → new snapshot with the same `metric_def_version`; 3. snapshot carries `rules_version` |
| `Evidence` | analytics | 1. limit > 10 → refused; 2. rallies not behind the metric never listed; 3. total = n |
| `MatchDeletion` | matches / platform | 1. delete another account's match → 404, nothing changes; 2. delete twice → same result (idempotent); 3. after delete every read → 404; 4. purge with an object-store failure → retried, rows kept until objects are gone (or the order PE-3 decides), no orphan |
| `AccountDeletion` | players | 1. two sessions → both revoked; 2. all matches deleted; 3. re-sign-in per PM-1 |
| `UploadExpiryPolicy` (ST-038) | video_ingest | 1. 23 h 59 min → not expired; 2. 24 h → expired; 3. completed uploads never expire by this rule |
| Worker grants (ST-042) | migrations | 1. worker role SELECT on `sessions` → permission denied; 2. on `accounts` → denied; 3. on the job table → allowed |
| `FullTagAccess` | dataset | 1. player role → 404; 2. labeller on a match without a consent record → refused; 3. labeller with consent → allowed |
| `LabelExport` | dataset | 1. a label with an unknown player → refused; 2. frame out of range → refused; 3. export validates against the schema |
| `DrillLint` | coaching/drills | 1. unknown target metric "AN-99" → fails naming drill and metric; 2. progression cycle → fails naming the cycle; 3. duration 46 min → fails; 4. criterion with no number → fails; 5. no source and no rationale → fails; 6. the valid fixture passes |

Front-end (Vitest): metric card view-model (1. n missing → render refused, NFR-038 b; 2. low-sample → text flag and de-emphasis class; 3. draft entry never rendered), delete-confirmation reducer (1. confirm not typed → button disabled; 2. server error keeps the dialog with a support ref), S-01 move offer (C3-03: 1. not the latest kept rally → no "Move" option; 2. `not_last_in_game` → explained).

## 6. Integration tests

| ID | Boundary | Test | Story |
|---|---|---|---|
| IT-03-01 | API ↔ DB | Tag the worked example and a 30-rally game; the snapshot equals the expected stats; `metric_def_version` and `rules_version` stored | ST-044, ST-046 |
| IT-03-02 | Events ↔ DB | `RallyScored` delivered twice → one snapshot version; `ScoreCorrected` → recomputed; a failure in recompute does not roll back the tag (separate transaction) and is retried | ST-046 |
| IT-03-03 | API | A `draft` dictionary entry is absent from the stats response; a `coach-reviewed` one is present with its definition | ST-043 |
| IT-03-04 | API ↔ DB ↔ store | Evidence: ≤ 10 items, total = n, every item behind the metric, the item's media link answers Range with 206 | ST-047 |
| IT-03-05 | BOLA matrix | Stats, evidence, delete match, delete account, label and consent routes added; another account gets 404 on each; inventory diff covers them (NFR-051) | ST-046..ST-052 |
| IT-03-06 | API ↔ DB ↔ store | Delete a match: every read 404 at once; run the purge job: no row in any public table references the match (information-schema inventory) and no object under its keys remains | ST-050 |
| IT-03-07 | Job ↔ store ↔ DB | A store failure injected mid-purge: the job retries and completes; no orphan rows or objects; a second run is a no-op | ST-050 |
| IT-03-08 | API ↔ DB | Delete an account with two sessions and three matches: both sessions 401, three matches purged, re-sign-in per PM-1 | ST-051 |
| IT-03-09 | Scheduler ↔ store ↔ DB | Abandoned upload expiry after 24 h (clock injected): object removed, session hidden, HEAD/PATCH refused (was IT-02-07) | ST-038 |
| IT-03-10 | DB roles | The worker role cannot read `sessions`, `sign_in_*`, `accounts`; can read and update job, media and upload rows; worker S3 key limited to the media bucket | ST-042 |
| IT-03-11 | API ↔ DB | Full Tag: player 404; labeller without consent refused; with consent: tag a hit at frame 18,402 by B1, export validates against the schema and contains it | ST-052 |
| IT-03-12 | API boundary | Rule L11 over every new JSON string field (delete confirmations, labels, consent record): 4xx never 5xx, no row written; parallel delete + tag on one match → one consistent outcome | QA-FUZZ-3 |
| IT-03-13 | Logs | Deletion, purge and labelling log lines carry ids and the pseudonymous user id only, never the address (NFR-057, NFR-069) | ST-050, ST-051, ST-052 |
| IT-03-14 | CLI ↔ files | Drill lint over the fixture library: each failure rule fails naming drill and reason; the valid library passes; a deprecated drill keeps its content | ST-053 |

Files are named `test_it_03_<nn>_<slug>.py` so the scorecard's `junit_rate.py --require test_it_03_<nn>_` finds each id (G03-04).

**E2E (Playwright, `web/e2e/sprint-03/`):** E2E-03-01 journey v2 (sign in → upload → tag the worked example → stats equal the reference with n, interval and low-sample text, unofficial notice → Show me → the rally plays → delete the match → gone). E2E-03-02 evidence crawl over the dashboard: every metric card has n and a working "Show me" (NFR-038). E2E-03-03 "How is this measured?" shows the definition; a draft metric is not shown; low-sample text present. E2E-03-04 delete account: the confirmation states the consequences; signed out; signing in again shows an empty account. E2E-03-05 Full Tag: labeller frame-steps by keys, tags a hit, exports; a player cannot open Full Tag. E2E-03-06 keyboard-only dashboard and evidence; 320/360 px with no sideways scroll. E2E-03-07 S-01 "Move" offered only on the latest kept rally (C3-03). axe on every page (attachments `axe-<screen id>`, families D, E, X, L), 24×24 targets. Titles carry their id.

**Timing spec (ST-054):** `web/e2e/sprint-03/timing.spec.ts` attaches `timing-dashboard-interactive` (warm), `timing-show-me-first-frame` (9/1.5 Mbit/s, 4× CPU) and `timing-layout-shift` (`{"ms": <CLS × 1000>}`, so the existing `pw_timings.py` reads it); ≥ 20 samples each.

## 7. Gherkin scenarios

### 7.1 Starter stats and uncertainty

```gherkin
# tests/features/starter_stats.feature
@M4 @story-ST-044 @nfr-004
Feature: Starter stats
  The definitions are the coach's (metric-dictionary v0.1); scoring is provisional.

  Background:
    Given Ivy has tagged the worked-example game of the metric dictionary

  Rule: Every stat equals the coach's hand count

    Scenario: Rallies won on serve
      When she opens her stats
      Then "Rallies won on serve" shows 57% for her side with "n = 7"

    Scenario: Replays are not counted
      When she opens her stats
      Then no stat counts rally 8, which was a replay

    Scenario: Errors are charged to the side that made them
      When she opens her stats
      Then her side shows 2 unforced errors in the game
      And the other side shows 1 with "player not tagged in 1 rally"

  Rule: Stats follow corrections

    Scenario: A correction changes the stats
      Given her stats show "Rallies won when receiving" as 33% with "n = 6"
      When she changes rally 3 to won by her side
      Then "Rallies won when receiving" shows 40% with "n = 5"
```

```gherkin
# tests/features/metric_uncertainty.feature
@M4 @story-ST-044 @fr-101
Feature: Metrics show their uncertainty
  Rule: Small samples are flagged, never hidden

    Scenario Outline: Low-sample flag
      Given Ivy received serve in <n> rallies and won <won>
      When she opens her stats
      Then "Rallies won when receiving" shows <pct> with "n = <n>" and the low-sample flag "<flag>"
      Examples:
        | n  | won | pct | flag |
        | 8  | 4   | 50% | yes  |
        | 20 | 10  | 50% | yes  |
        | 40 | 22  | 55% | no   |

    Scenario: The interval is shown
      Given Ivy received serve in 40 rallies and won 22
      When she opens her stats
      Then she sees the range 40% to 69% next to 55%

    Scenario: One game is too few for a per-game count
      Given Ivy has tagged one game
      When she opens her stats
      Then "Unforced errors per game" is shown and flagged "low sample"
```

### 7.2 Metric dictionary

```gherkin
# tests/features/metric_dictionary.feature
@M0 @story-ST-043 @fr-102
Feature: Metric dictionary
  Scenario: Draft metric hidden
    Given metric AN-05 has status "draft"
    When Ivy opens her stats
    Then AN-05 is not shown

  Scenario: Definition shown
    Given AN-02 is coach-reviewed
    When Ivy opens "How is this measured?" on "Rallies won when receiving"
    Then she sees its definition in plain words

  Scenario: Unofficial scoring is said on the stats too
    Given the rules preset contains an unverified rule
    When Ivy opens her stats
    Then she sees "unofficial scoring (rules not yet verified)"
```

### 7.3 Evidence

```gherkin
# tests/features/metric_evidence.feature
@M0 @story-ST-047 @nfr-038
Feature: Evidence behind a metric
  Scenario: Show me the rallies
    Given Ivy's stats show "Rallies won on serve" with "n = 7"
    When she opens "Show me" on it
    Then she sees the 7 rallies her side served, each with a link that plays it

  Scenario: More than ten rallies
    Given a stat is based on 23 rallies
    When Ivy opens "Show me" on it
    Then she sees 10 rallies and "See all 23"

  Scenario: Every number can be checked
    When Ivy opens her stats
    Then every stat shows its sample size and a working "Show me"
```

### 7.4 Attribution conservation

```gherkin
# tests/features/attribution_conservation.feature
@M0 @story-ST-045 @fr-109
Feature: Attribution conservation
  Scenario: Every lost rally is accounted for once
    Given side A lost 14 rallies in game 1, 6 on serve and 8 on receive
    When the lost rallies are attributed
    Then the attributed and unattributed rallies on serve total 6
    And on receive they total 8
```

### 7.5 Deletion and expiry

```gherkin
# tests/features/match_deletion.feature
@M0 @story-ST-050 @nfr-066
Feature: Delete a match
  Rule: A deleted match is gone from the account at once and from storage soon after

    Scenario: Delete a tagged match
      Given Ivy has a tagged match with stats
      When she deletes the match and confirms the stated consequences
      Then within 1 minute the match no longer appears anywhere in her account
      And after the clean-up runs no stored file or record of the match remains

    Scenario: The confirmation says what will go
      When Ivy starts deleting a match
      Then she is told the video, tags, score sheet and stats will be deleted and cannot be restored

    Scenario: Someone else's match
      Given Carlos knows the address of Ivy's match
      When he tries to delete it
      Then he is told it does not exist
      And Ivy's match is unchanged
```

```gherkin
# tests/features/account_deletion.feature
@M0 @story-ST-051 @nfr-066
Feature: Delete my account
  Scenario: Delete account
    Given Ivy has 3 matches and is signed in on her phone and her laptop
    When she deletes her account and confirms
    Then she is signed out on both devices
    And after the clean-up runs none of her matches or her profile remain stored

  Scenario: Signing in again starts empty
    Given Ivy deleted her account
    When she signs in again with the same address
    Then she sees no matches
```

The Sprint 2 `abandoned_upload_expiry.feature` (sprint-02 §7.6) is used unchanged for ST-038.

### 7.6 Full Tag and drill lint

```gherkin
# tests/features/full_tag.feature
@M0 @story-ST-052 @fr-150
Feature: Full Tag
  Scenario: Labeller tags a hit
    Given a labeller is stepping frame by frame through a consented match
    When they tag a hit by player B1 at frame 18,402
    Then the exported label file contains that hit with its frame and player

  Scenario: Player cannot open Full Tag
    Given Ivy has a normal player account
    Then the Full Tag mode is not available to her

  Scenario: Match without consent
    Given a labeller opens a match that has no consent record
    Then they are told the match cannot be labelled
```

```gherkin
# tests/features/drill_library.feature
@M5 @story-ST-053 @fr-140
Feature: Drill library integrity
  Scenario Outline: A drill file breaks a rule
    Given a drill file that <breaks>
    When the library is validated
    Then validation fails naming the drill and "<reason>"
    Examples:
      | breaks                                   | reason              |
      | targets metric "AN-99"                   | unknown metric      |
      | lists itself as its own progression      | progression cycle   |
      | lasts 46 minutes                         | duration over 45    |
      | has a success criterion with no number   | criterion no number |
      | has neither a source nor a rationale     | no source           |

  Scenario: Plan keeps a deprecated drill
    Given a drill at version 2 that was later deprecated
    When the library is validated
    Then version 2 is still present with its content
```

### 7.7 Carry-over

```gherkin
# tests/features/corrections_replay.feature (addition)
@M0 @story-C3-03
  Rule: Only moves the server accepts are offered

    Scenario: Move offered only on the latest kept rally
      Given rallies 12 to 14 need Ivy's decision
      When she opens the options of rally 12
      Then "Move to the next game" is not offered
      And she is told only the latest kept rally can be moved first
```

## 8. Quality gates

All Sprint 0-2 per-PR gates, plus:

| Gate | Threshold | Source |
|---|---|---|
| Golden matches GS-AN-1 v1 | 100% exact for every coach-reviewed metric, side and match | NFR-004; QD-QG-S5 |
| Attribution conservation property | ≥ 1,000 matches (profile `ci`), 0 violations | FR-109 |
| Evidence crawl | 0 metrics without a working "Show me"; 0 shown without n | NFR-038 |
| Deletion IT | storage and DB empty after the purge (IT-03-06/-08) | NFR-066 (b) |
| Coverage on analytics | ≥ 90% line (first sprint with analytics code) | NFR-071 |
| Mutation on `sports/pickleball/rules` | ≥ 0.85 (kept) | NFR-072 |
| Mutation on the starter-stats module | ≥ 0.80 (first gate, judgment; decision-log 2026-10-06) | NFR-072 extended (judgment) |
| JSON boundary fuzz | IT-03-12 green; 0 5xx | rule L11 |
| Drill lint | CI job present and green on the library; red on each negative fixture | FR-140 |
| Open blocker/major | 0 in `docs/sprints/03/review-rounds.md` (carried rows included) | DoD; ADR 0030, 0033, 0037 |
| Stats current after a tag or correction | p95 ≤ 5 s live | NFR-017 analogue (judgment) |
| Dashboard interactive | p95 ≤ 2.0 s warm | NFR-011 |
| Layout shift on stats load | 0 | NFR-039 |

Baselines recorded but not yet gating: NFR-010 at 50 RPS on stats/evidence (gate at the S5 review).

## 9. Definition of Done

Story and sprint levels as in `docs/process/definition-of-done.md`. Sprint 3 adds:

- [ ] Every metric card in the demo shows n, the "unofficial scoring" notice and a working "Show me".
- [ ] Only `coach-reviewed` metrics are shown; the review record lists each entry's change with evidence.
- [ ] Rule-dependent rows are reported separately and counted toward no Must FR (QD-QG-P5).
- [ ] The traceability matrix lists the feature files for FR-006, FR-007, FR-024, FR-100..FR-103, FR-109, FR-140, FR-150, FR-151.
- [ ] Sprint 4 stories meet the DoR (BA-1).
- [ ] Retro 2 actions reviewed first.
- [ ] **Every row of `docs/sprints/03/goal-scorecard.md` is "yes"**, filled by an independent verifier from one isolated, self-cleaning run at one recorded head (PO standing rule; ADR 0033). The sprint report leads with the scorecard.
- [ ] Every scorecard method has a dry-run row before the verifier runs it (ADR 0033 rule 2).
- [ ] Every review and verification round has an EM reconciliation row (ADR 0037 rule 1).
- [ ] Every decider task of §3.3 has its output, or an escalation row, by its date (ADR 0037 rule 2).
- [ ] Human-gated items handled as the PO chose (§0.4), or still counted in G03-12 if the PO did not answer.

## 10. Risks for this sprint

| Risk | Signal | Response |
|---|---|---|
| The coach does not move entries to `coach-reviewed` (or needs the human second reviewer) | COACH-1 output missing on D2, or the coach rules that P9 is required | Stats are computed and tested but hidden (FR-102); goal bullet 1 fails; P12 put to the PO on D2 (judgment) |
| Purge misses a table or object | IT-03-06 inventory finds rows | Inventory is generic (information schema), so a new table is caught; PE-3 lists every owner of match/account data |
| Snapshot recompute too slow or racing corrections | G03-02 p95 > 5 s; IT-03-02 flakes | Recompute only the changed match; idempotency key per event; PE-2 review |
| Design inputs late again (DR-02, DR-03) | Cells empty at D3 | EM escalates to the PO on D3 with the options (wait, or a recorded waiver); no UI story starts without one (ADR 0037 rule 2) |
| Sprint 2 not merged; DoD-done 0 for a third sprint | PR #2 still red at D5 | C3-01/C3-05 first; the EM records the size waiver; PO list |
| Disk near the floor | `disk-precheck.sh` rc=3 | P5 standing approval: prune images and build cache |

## 11. Dependencies

- Sprint 2: the `Match` projection (ST-026), corrections (ST-031/032), rally media links (ST-037), the BOLA matrix (IT-02-05).
- Design: PE-1, PE-2, PE-3, PD-1, DR-03.
- Domain: COACH-1 (dictionary statuses, golden hand counts).
- Human: P6, P7 (OQ-01), P9 (OQ-20), P10, P11, P12.

## 12. Demo script (sprint review, 2026-11-27)

1. Sign in; open "Saturday doubles" tagged with the worked-example game (metric-dictionary §2).
2. Open Stats: 7 metric cards per side, each with n; "Rallies won on serve" 57% (n = 7) with its range and "low sample" in text; the unofficial notice; open "How is this measured?".
3. "Show me" on "Rallies won on serve": the 7 rallies; open one, the video plays at the rally.
4. Correct rally 3's winner on the score sheet; return to Stats: "Rallies won when receiving" changed from 33% (n = 6) to 40% (n = 5), because the serve sequence after rally 3 changes.
5. Narrow to 360 px; show the stacked cards and the AN-07 bar with printed values.
6. Delete the match; show the confirmation text; the match is gone from the list; show the purge job's log and the empty inventory.
7. Delete the account from a second browser session; the first session is signed out.
8. As a labeller, open the consented synthetic match in Full Tag; step frames by keys; tag a hit; export; show the file validating. Show a player account getting "not found".
9. Run the drill lint on the fixture library: a failing file named with its reason; the valid set passing.
10. Show the goal scorecard filled by the verifier, then the test report: golden matches, conservation property, mutation, evidence crawl, open defects (0).
11. Ask the PO: P6-P12; OQ-01 status; accept ADR 0005.

## 13. Retrospective

- **Date:** 2026-11-27. **File:** `docs/retros/2026-11-27-sprint-03.md` from [`docs/retros/TEMPLATE.md`](../retros/TEMPLATE.md).
- **Format:** Start/Stop/Continue. **Focus:** did ADR 0037 work: reconciliation counts, decider tasks on time, the PO's answers to human-gated items.
- Review retro 2 action items first [EP/ENG-15].

## 14. Story specifications and Definition of Ready (business-analyst with engineering-manager, 2026-10-06)

- **Feature files:** `tests/features/` (repository root); step modules in `backend/tests/features/`; browser journeys in `web/e2e/sprint-03/`.
- **Priority:** from the FR's MoSCoW priority: all Must (FR-006, 007, 024, 100..103, 109, 140, 150, 151; NFR-054). PM confirms at PM-1.
- **Milestone:** M0 for platform, deletion, dictionary, evidence and Full Tag; M4 subset for the starter stats (FR-100); M5 subset for the drill lint (FR-140).

### 14.1 Story cards

#### ST-043 Metric dictionary in code
- **Value:** As a player, I want to see only metrics a coach has checked, so that I can trust what I read.
- **Context / aggregate:** Sport Plug-in (definitions, Published Language) → Analytics. No aggregate; versioned data.
- **Out of scope:** editing entries in the UI; the `verified` status (needs OQ-01 and the second reviewer).
- **Files:** `backend/src/racket/sports/pickleball/metrics*` (PE-2 names the file), `backend/tests/unit/sports/…`. **E2E step:** E2E-03-03.

#### ST-044 Starter stats AN-01..AN-07
- **Value:** As a player, I want my serve, receive, error and run numbers with how sure they are, so that I know what to work on.
- **Context:** Analytics, pure functions over the Match projection (read model), no write to `Match`.
- **Out of scope:** trends (FR-104), per-player AN-01 beyond "rallies served by this player", rally-scoring presets (AN-03 "not used").
- **Files:** `backend/src/racket/analytics/starter_stats.py`, `uncertainty.py`; unit tests under `backend/tests/unit/analytics/`. **E2E step:** E2E-03-01.

#### ST-045 Attribution conservation
- **Value:** As a coach, I want every lost rally accounted for exactly once, so that weakness rankings (Sprint 4) never double-count.
- **Context:** Analytics. **Out of scope:** the weakness ranking itself (FR-120, Sprint 4).
- **Files:** `backend/src/racket/analytics/attribution.py`; property test in QA's `backend/tests/regression/`.

#### ST-046 `MetricSnapshot` and the stats API
- **Value:** As a player, I want the stats to be current after every tag or correction, so that fixing a call fixes the numbers.
- **Context / aggregate:** Analytics `MetricSnapshot` (recomputable read model); consumes `RallyScored`, `ScoreCorrected` (context map R6).
- **Out of scope:** cross-match aggregates, trends, caching beyond the snapshot.
- **Files:** `backend/src/racket/analytics/{snapshot,api}.py`, a migration. **E2E step:** E2E-03-01; IT-03-01/-02.

#### ST-047 "Show me" evidence
- **Value:** As a player, I want to see the rallies behind a number, so that I can believe it or correct it.
- **Out of scope:** clips (FR-030, R3); sharing.
- **Files:** BE `analytics/evidence.py`; FE `web/src/app/matches/[matchId]/stats/evidence/*`. **E2E:** E2E-03-01, -02.

#### ST-048 Stats dashboard
- **Value:** As a player, I want one page with my starter stats, their sample sizes and honest flags, so that I can read my match at a glance.
- **Out of scope:** charts beyond AN-06 histogram and AN-07 bar; trends; export.
- **Files:** `web/src/app/matches/[matchId]/stats/*`, `web/src/lib/stats/*`. **E2E:** E2E-03-01, -03, -06; timing spec.

#### ST-049 Golden matches and GS-AN-1 v1
- **Value:** As the team, we want three hand-counted matches frozen as a gold set, so that every metric change is checked against a coach's count.
- **Out of scope:** video gold sets (QD-GD-04, R2); real footage.
- **Files:** `backend/tests/regression/golden_matches/`, manifest via `racket.dataset.manifest`. **Check:** `pytest -m golden_an`.

#### ST-050 Delete a match
- **Value:** As a player, I want to delete a match and know it is really gone, so that I control my footage.
- **Context / aggregate:** `Match` (soft delete command), Capture & Media (objects), platform purge job; events `MatchDeleted`.
- **Out of scope:** plan notes "evidence removed" (Sprint 4); backups (documented in SEC-1).
- **Files:** BE `matches/deletion.py`, `platform/purge.py`, migration; FE match menu and `X-01` dialog. **E2E:** E2E-03-01; IT-03-06/-07.

#### ST-051 Delete my account
- **Value:** As a player, I want to delete my account and everything in it, so that nothing of mine stays behind.
- **Out of scope:** data export before deletion (FR-010, R2); admin deletion.
- **Files:** BE `players/deletion.py`; FE `web/src/app/settings/account/*`. **E2E:** E2E-03-04; IT-03-08.

#### ST-038, ST-042 (carried)
- Cards in sprint-02 §3 (ST-038 "Moved out at planning"; ST-042 "Security carry-over"), unchanged except that ST-038 runs on the ST-050 purge job.

#### ST-052 Full Tag labelling tool
- **Value:** As a labeller, I want to tag hits, bounces and rally boundaries frame by frame on consented footage, so that the team can build gold sets for R2.
- **Context:** Dataset & Labelling (`racket.dataset`), labeller role in Identity & Players (role flag set by CLI).
- **Out of scope:** user-facing training consent (FR-009, Sprint 4); inter-labeller κ tooling; real footage (P11, P10).
- **Files:** ML `backend/src/racket/dataset/{labels_api,consent,export}.py`; FE `web/src/app/label/*`. **E2E:** E2E-03-05; IT-03-11.

#### ST-053 Drill schema and lint
- **Value:** As the coach, I want every drill file checked automatically, so that the library never points at a metric or drill that does not exist.
- **Out of scope:** drill content (FR-141, Sprint 4); the plan workflow.
- **Files:** `backend/src/racket/coaching/drills/{schema.json,lint.py}`, `content/drills/` (fixtures only), CI job. **Check:** IT-03-14.

#### ST-054 E2E journey v2 and performance baseline
- Defined in §3.2 and §6.

#### C3-01..C3-10, QA-ACC-3, QA-FUZZ-3, SRE-PURGE, SRE-SMOKE-3
- Defined in §3.1 and §3.2. Each names its files, its test or evidence and its reviewer there.

### 14.2 Definition of Ready check (2026-10-06)

Key: ✓ met; **R** pending, with owner and day below; — not applicable.

| DoR item | C3-01 | C3-03 | C3-04 | C3-05 | 043 | 044 | 045 | 046 | 047 | 048 | 049 | 050 | 051 | 038 | 042 | 052 | 053 | 054 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ID, value statement | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PM-assigned priority | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 | R1 |
| FR/NFR and milestone linked | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Out of scope listed | — | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Declarative Gherkin incl. negative cases | — | ✓ §7.7 | — | — | ✓ | ✓ | ✓ | ✓ (§7.1 correction) | ✓ | ✓ (§7.1-7.3) | — (regression) | ✓ | ✓ | ✓ (sprint-02 §7.6) | — (IT-03-10) | ✓ | ✓ | — (journey) |
| NFRs measurable | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| QA agrees testable, levels named | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 | R2 | ✓ (QA-owned) | R2 | R2 | R2 | R2 | R2 | R2 | ✓ |
| Domain truth verified, or no rule claim | — | ✓ (a) | — | — | R5 | R5 (`@needs-verification` where rules enter) | ✓ (counts only) | — | — | R5 (wording) | R5 | — | — | — | — | ✓ (no rule) | R5 (metric ids) | — |
| Glossary terms used / added | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Context and aggregates named | — | ✓ | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Design doc / ADR approved | — | ✓ C3-02 | ✓ ADR 0036 | — | R3 | — (pure) | — | R3 | R4 | R4 | — | R4, R6 | R4, R6 | ✓ ADR 0006 | ✓ sprint-02 card | R4 | — | — |
| UI flow and all states; WCAG, HAX | — | ✓ flows-02 S-01 | — | — | — | — | — | — | R7 | R7 | — | R7 | R7 | — | — | R7 | — | — |
| Design review held | — | R8 (DR-02) | — | — | — | — | — | R3 | R7 | R7 | — | R7 | R7 | — | — | R7 | — | — |
| Threat-model notes attached | — | — | — | — | — | — | — | R6 | — | — | — | R6 | R6 | R6 | R6 | R6 | — | — |
| Sized; slices named | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Dependencies available | ✓ | C3-02 | ✓ | C3-01 | COACH-1 | ✓ (ST-026) | ST-044 | ST-044, R3 | ST-046 | ST-046 | COACH-1 | R6 | ST-050 | ST-050 | ✓ | R4 | ST-043 | ST-048 |
| Files, interfaces, E2E step named | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

| # | Pending item | Owner | Due |
|---|---|---|---|
| R1 | Confirm the priorities (all Must) and the stretch order (PM-1) | product-manager | D1 |
| R2 | Agree that every criterion in §7 is testable and name the level | senior-qa-engineer | D1 (before QA-ACC-3) |
| R3 | `analytics-snapshots.md` reviewed and Accepted (PE-2); the dictionary file location decided | principal-engineer and reviewers | D2 |
| R4 | `api-sprint-03.md` written and reviewed (PE-1); `statscontract.py` aligned | principal-engineer | D2 |
| R5 | COACH-1: entries `coach-reviewed` (or the reason not), hand counts for ST-049, metric ids final for ST-053 | pickleball-domain-coach | D2 |
| R6 | SEC-1 threat notes; PE-3 deletion and purge design | security-privacy-engineer, principal-engineer | D2 |
| R7 | `flows-sprint-03.md` (PD-1) and DR-03 held | principal-designer with FE, coach, BA, PM, security | D2, D3 |
| R8 | DR-02 held (C3-03's S-01 behaviour is a DR-02 decision cell) | principal-designer with deciders | D1 |

**Verdict (business-analyst and engineering-manager, 2026-10-06):** every BA-owned DoR item is met for the committed rows. C3-01, C3-04, C3-05, ST-044 and ST-042 are **Ready now** once R1 and R2 are ticked on D1; they are the first work of their lanes. The other rows are **Ready on condition** of R3-R8 by D1-D3; no code for them is committed before their conditions are ticked in this table (a dated note per tick in `decision-log.md`). Rule-dependent rows stay `@needs-verification` and count toward no Must FR (QD-QG-P5).

## 15. Build lanes (engineering-manager, 2026-10-06; ADR 0010: ≤ 5 lanes, ≤ 2 streams per role, disjoint directories)

| Lane | Role | Stories (in order) | Directories (write) |
|---|---|---|---|
| L1 backend | senior-backend-engineer | ST-044, ST-043, ST-045, ST-046, ST-047 (API), ST-050 (API, purge job), ST-051 (API), ST-038, ST-042 (grants); stretch ST-035, ST-034, BE minors | `backend/src/racket/` except `dataset/` and `coaching/drills/`; `backend/src/racket/migrations/`; `backend/tests/unit/{analytics,matches,players,video_ingest,sports,platform}/` |
| L2 frontend | senior-frontend-engineer | C3-03, DR-02 FE follow-ups, then after DR-03: ST-048, ST-047 (UI), ST-050 (UI), ST-051 (UI), ST-052 (UI); FE minors | `web/src/`, `web/tests/` |
| L3 quality | senior-qa-engineer | C3-01, QA-FUZZ-3, ST-049, QA-ACC-3, ST-054 (journey, crawl, timing), C3-06, scorecard dry-runs, QA minors | `tests/features/`, `backend/tests/{features,integration,regression,oracle,perf,support}/`, `web/e2e/`, `docs/process/testing-strategy.md`, `docs/sprints/03/{test-change-requests,a11y-manual}.md` |
| L4 platform | sre-devops-engineer | C3-04, C3-05, ST-042 (Compose roles, S3 identity), SRE-PURGE, ST-054 (Locust in CI), SRE-SMOKE-3, C3-08 when P11 is answered, SRE minors | `infra/`, `.github/`, `scripts/ci/`, `scripts/dev-*.sh`, `scripts/disk-precheck.sh`, `docs/ops/`, `docs/sprints/03/{smoke,ci-status}.md` |
| L5 data and content tooling | senior-ml-cv-engineer | ST-053, ST-052 (labels API, consent record, export); ST-025 when P3 is answered | `backend/src/racket/dataset/`, `backend/src/racket/coaching/drills/`, `backend/tests/unit/{dataset,coaching}/`, `content/drills/`, `docs/data/`, `fixtures/` |

- **Disjointness:** L1 writes production code under `backend/src/racket/` except `dataset/` and `coaching/drills/` (L5). L3 owns every acceptance, integration, regression and E2E test. A lane that needs a file in another lane's directory asks that lane, or the EM routes it.
- **Docs roles (scheduled tasks, §3.3, not lanes):** principal-engineer (`docs/architecture/`, `scripts/measure/statscontract.py` and `tagcontract.py` with the contracts), principal-designer (`docs/design/`), business-analyst (`docs/requirements/`), security-privacy-engineer (`docs/security/`), pickleball-domain-coach (`docs/domain/`), product-manager and engineering-manager (`docs/sprints/`, `docs/decisions/`, `docs/retros/`).
- **Streams per role:** BE 2 (analytics; deletion/platform), FE 2 (stats and evidence; deletion and Full Tag), QA 2 (backend tests; browser tests), SRE 2 (CI; Compose), ML 1.
