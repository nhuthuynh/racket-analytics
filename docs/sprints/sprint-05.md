# Sprint 5: R1 hardening and release readiness, agent-measurable gates proven live

- **Dates (calendar of record):** Mon 2026-12-14 → Tue 2026-12-22 (shortened, 7 working days; roadmap §2). **Re-baselined working dates:** the sprint runs as a compressed agent session from **2026-11-03** (like Sprints 1-4); the in-session due dates below (2026-11-05 … 2026-11-13) are the ones the EM status step checks. The 2026-12-22 review and retro keep the PO cadence.
- **Planning:** 2026-11-03 by the engineering-manager with the product-manager, principal-engineer, business-analyst and senior-qa-engineer (ticket PLAN-05, branch `s05/plan` from `origin/main` at `04c6a826`). Kickoff input from all 12 roles: [`05/kickoff.md`](05/kickoff.md).
- **Retro file:** `docs/retros/2026-12-22-sprint-05.md`, format **Start / Stop / Continue plus the all-role reflection** (PO 2026-10-31). Focus: **did the tiers, WIP limits and the single close hold, and what did each PR cost (the 12-role question, ADR 0056 decision 1)?**
- **Delivery:** every ticket is its own branch `s05/<ticket-id-lowercase>` and its own **draft** PR into `main` (ADR 0039, ADR 0052), marked ready only when local checks pass. No sprint branch. Merges only through `merge_ready.py`, one at a time, by the gated merge step (ADR 0050).
- **Goal scorecard:** [`05/goal-scorecard.md`](05/goal-scorecard.md), 12 metrics G05-01..G05-12, each measured live; human-only items in its §5.
- **Atomic requirements:** [`05/requirements-breakdown.md`](05/requirements-breakdown.md) (atomic item → story → ticket → test).
- **Shared sprint files:** `docs/sprints/05/review-rounds.md` (findings ledger), `test-change-requests.md`, `blockers.md`, `decision-log.md`, `status.json`, `progress.md`. **Ticket PRs never edit** `status.json`, `progress.md`, `decision-log.md` or `blockers.md`; each ticket writes `docs/sprints/05/decisions/<TICKET-ID>.md`. Only RETRO-05 consolidates. Ticket PRs may add ledger rows to `review-rounds.md` and their own §6 row to the scorecard.
- **Related ADRs:** 0008 (Locust), 0010 (capacity), 0014 (fail closed), 0026 (SLIs), 0033, 0037, 0047 (gates first), 0050 (merge discipline), 0052 (draft first), 0053 (red-run notice), 0054 (size = production lines), 0055 (verification order, live dry-run, evidence PRs merged), **0056 (12 roles + cost per PR, tiered review, WIP limits and flow metrics)**. New ADRs this sprint: PE-5a (SLOs and alerts), PE-5b (backup and restore), ST-084a (model regression tolerances). Citation prefixes: working-agreement §0.

## 0. Planning record (2026-11-03)

### 0.1 Preconditions

| Precondition | Status at planning | Consequence |
|---|---|---|
| **CI on `main` green (CI FIRST)** | **Push: green.** `gh api .../actions/runs?branch=main&event=push`: 41643389454 at `04c6a826` → success; 41639406875 at `785b4ab4` → success. **Scheduled: not green.** CI run 41622904539 (`schedule`, `888760df`, 2026-11-03 10:52) → `cancelled`: the Flaky-test report job ran 55 min against `timeout-minutes: 45` (usually 20-22 min), and `scripts/ci/scheduled_red_notice.py` line 28 treats `cancelled` as "none", so nobody was told | **CI-NOTICE-CANCELLED** (`ci_fix`) is the first ticket and pre-empts feature work; it fixes the notice and finds the hang's root cause |
| Open PRs | `gh api .../pulls?state=open` → 0 | Nothing to merge before planning |
| Sprint 4 ledger | `python3 scripts/measure/open_defects.py docs/sprints/04/review-rounds.md` → `open 0`, rc 0 | No blocker/major carried; minor QA-VERIFY04R5-01 carried as a ticket |
| Retro 4 actions | F1 (single close), F3 (close checklist): due at this sprint's close; **F2 / E2 TCR rows 11 and 14: overdue** (due 2026-11-02, `grep -c Pending` → 2); **E3 CI-RECON-ON-PR: not started** (due 2026-11-13); **F4 QA-VERIFY04R5-01** (due 2026-11-13); E4 (dry-run rows): applied in scorecard §6 | Tickets QA-TCR-04, CI-RECON-ON-PR, QA-VERIFY04R5-01, EM-CLOSE-CHECKS; §0.3 |
| ADR 0056 required tickets | merge_ready tiers; doc-check job | **CI-TIERS-a/b**, **CI-DOC-CHECK** (wave 1) |
| SLO/alert design; backup design | No burn-rate rules (`infra/observability/alerts/` holds billing only); no backup tooling (`git grep -E 'pg_dump\|pg_basebackup\|wal-g\|pgbackrest'` over infra, scripts, docs/ops → nothing) | Gate tickets **PE-5a**, **PE-5b** before any build ticket on them |
| Threat notes for S5 work | none | Gate ticket **SEC-5** |
| Flows; DR-04 never held | `flows-sprint-04.md` §14.2: all five DR-04 decider cells "pending" | **PD-5**, **PD-DR04** |
| Disk | 30 GB free on `/` (`df -h /`) | Above both floors; every build runs `bash scripts/disk-precheck.sh` first; the stack creator prunes (P5) |

### 0.2 Product-owner decisions applied (quoted in `docs/requirements/po-input-2026-10-05.md`)

- **"start Sprint 5 once the PRs merge"** (2026-11-03): #183-#185 merged; planning starts.
- **Way of working (2026-10-31):** kickoff with feedback (§0.5, `05/kickoff.md`); work split by role fit (§3); plan and brainstorm skills (§0.6); FR/NFR to atomic level (`05/requirements-breakdown.md`); goal with stories and tickets, complex stories split into tickets (§3); one PR per ticket with unit + integration tests, green CI, principal-engineer review and a QA test before merge (§8, §9); all-role reflection after the sprint (RETRO-05).
- **Audit decisions (2026-11-03, ADR 0056):** keep 12 roles and measure cost per PR (§9 cost table, G05-11); review depth tiered by risk (§8, CI-TIERS-a/b); keep sprints with WIP limits and flow metrics (§2.1, G05-11).
- **CI FIRST** (2026-10-08); **separation of duties** (2026-10-09); **goals measured live, human-only items as P12 rows**; **PR size counts production code** (2026-10-28, ADR 0054).

### 0.3 Retro 4 carry-over and open findings applied

| Item | Source | Ticket |
|---|---|---|
| F1 / E5 single close after VERIFY | retro 4 §12 | EM-CLOSE-CHECKS (`retro_ready.py`), RETRO-05 depends on it |
| F2 / E2 TCR rows 11 and 14 | retro 4 §12 | **QA-TCR-04** (first QA task) |
| F3 close checklist (PR set = `status.json` map; Open blocker rows have open causes) | retro 4 §12 | EM-CLOSE-CHECKS |
| F4 `make demo` on a flag-on stack (QA-VERIFY04R5-01, minor) | retro 4 §12 | **QA-VERIFY04R5-01** |
| E3 `reconcile_due.py` in pr-policy; decisions-file findings joined to the ledger; id format | retro 4 §11 | **CI-RECON-ON-PR** |
| E4 one rc 0 dry-run row per metric | retro 4 §11 | scorecard §6, every method ticket |
| ADR 0053 part 2 (admin setting 6) | sprint-report §14.3 | human row S5-S6 |
| Disk floor misses (M9) | retro 4 | P5 prune owner sre-devops-engineer; precheck at 10 and 16 GB |
| Author-found gap: single-weakness "Not for me" (checklist §3.1) | coach kickoff | ST-081a/b |
| Author-found gap: offline "as of" line not asserted by E2E; focus return per close path | FE kickoff (ST-065, QA-ST065-01) | ST-085 |
| DR-04 never held, UI shipped (retro 3 M3 pattern) | PD kickoff | PD-DR04 |

### 0.4 Goal items that depend on a human input (ADR 0037 rule 3; PO P12 option b)

Not goal metrics. Each is a row in `goal-scorecard.md` §5 ("not met: waiting on P-n") from day 1. Human-gated work is **not a ticket**; the table says what the team prepares.

| Item | Waits on | Need-by (asked in EM-ESC-05) | What the team prepares |
|---|---|---|---|
| Moderated usability test, ≥ 5 players (NFR-036.1-.3) | **P9** (OQ-20) | testers booked by 2026-12-16 | ST-083 kit, COACH-5 safety review, ST-080 (NFR-036.4) |
| Legal review (NFR-070, US + AU), including whether tester footage needs it first | **P16** | before any real-user beta and before the usability session | SEC-5 question list and ADR skeleton |
| Rulebook (OQ-01) and side-out verification | **P7** | PO-accepted fallback "R1 ships unofficial scoring" by 2026-11-10 | COACH-5 queue mapped to rule ids |
| Human coach review of drills | **P15** | fallback accepted by 2026-11-10 | ST-081b drills at `coach-reviewed` |
| Budgets, storage quota, GPU (OQ-13) | **P8** | 2026-11-10 | interim settings |
| Footage bucket and consented footage (SPIKE-02/05/07, QD-GD-04 v1 data) | **P11** (OQ-06) | by S7 planning so SPIKE-07 can run | ST-084a/b (footage-free) |
| Screen-reader pass | **P6** | overdue | automated a11y checks |
| Repository visibility | **P10** | sooner is safer | nothing private in git |
| SLO commitment and error-budget policy (NFR-041.2, NFR-042.2, NFR-049.1) | **P17** (new) | 2026-11-12 | ST-075c drafts |
| R1 release-candidate sign-off | **P18** (new) | after VERIFY-05 | ST-082 notes; PM readiness recommendation |
| Residual-risk ADR (ASVS fails, threat-note residuals, ADR 0031 re-review) | **P19** (new) | 2026-11-12 | SEC-5 + ST-078a-c draft |
| Real-device iOS Safari / Android Chrome (NFR-024.4-.5; OQ-17) | **P20** (new) | 2026-12-16 | ST-079 device checklist |
| Admin setting 6 (ADR 0053 part 2) | **setting 6** | open | nothing |

### 0.5 Kickoff

All 12 roles gave keep / change / lessons / risks / work-I-fit / breakdown advice. Every "change" item has a decision in [`05/kickoff.md`](05/kickoff.md) §2 (77 items from 12 roles: 4 deferred with an owner and a date, 1 routed to the PO, every other one accepted as a ticket, a rule or a row in the tier table).

### 0.6 Planning method and skills used (PO 2026-10-31; audit item 12 default (a))

| Step | Skill / input | Output summary |
|---|---|---|
| 1. Explore | `product-management:brainstorm` (installed skill) | Framed the problem as "the roadmap S5 goal is mostly human-gated". Options: (A) a release-readiness evidence pack of agent-measurable gates; (B) a process-first sprint; (C) usability kit first; (D) R2 readiness first. **Chosen: A**, with process work capped and the kit and R2 work as small side tickets. Riskiest assumption: the SLO and restore infrastructure fits 7 days in ≈ 100-line slices; mitigated by PE-5a/5b designs first and nightly (not per-PR) placement. Parked: FR-162 fake door, client-side usability instrumentation, WebKit on drafts, error-envelope contract export. |
| 2. Scope | `product-management:sprint-planning` (installed skill) | One-sentence goal; capacity at load factor 0.85 × 7/10 days; P0 = CI fix, tiers, doc-check, gates; P1 = R1 gates; P2 = R2 readiness and coverage gaps (first to slip: ST-085, ST-084b, ST-082 rollback part). Buffer ≈ 25 % for review loops. |
| 3. Atomic breakdown | business-analyst advice (kickoff) applied by the EM; BA-5 re-checks | `05/requirements-breakdown.md`: 62 atomic NFR items, 5 FR rules, 6 release/demo items, 27 process items; human items marked |
| 4. Stories → tickets | EM with principal-engineer slicing advice | 13 stories, 46 tickets (§3), each ≤ 400 production lines |
| 5. Owners by role fit | kickoff "work_i_fit" answers | §3 owner column; §4 per role |

## 1. Sprint goal

**R1 is a release candidate whose agent-measurable release gates are each proven live on the local stack, and every human gate has a ready kit and a dated PO ask.**

Scorecard bullets (each a G05 row): read latency at 50 RPS (G05-01); SLO burn-rate alerts that fire on an injected fault (G05-02); a timed restore drill (G05-03); the automated browser matrix (G05-04); fix-a-call in ≤ 2 taps (G05-05); data classification and client hygiene (G05-06); every applicable ASVS L2 row assessed (G05-07); the tiered merge gate and doc checks (G05-08); the prototype still runs flags off and on (G05-09); test strength (G05-10); flow and cost per PR measured (G05-11); green CI, tier verdicts, 0 open majors, one close (G05-12).

**Product Goal** (PM-5 writes it into roadmap §"Product Goal"; draft, judgment): R1 is a release candidate that a real amateur player can use, upload to plan in ≤ 15 min median, with every number and drill traceable, signed off by the PO.

**Out of scope:** FR-162 pricing fake door (OQ-14); SPIKE-02/03/05/07 (P11, P8); QD-GD-04 v1 data freeze (P11); client-side usability instrumentation; the Go port (S6); any real-user exposure (P16).

## 2. Capacity (ADR 0010)

- **Load factor 0.85** (lower of 0.85 and the median completion of S3 0.919 and S4 1.00). Shortened sprint: 7 of 10 working days. Capacity per stream = 8 × 0.7 × 0.85 ≈ **4.8 units**. Sizes: XS 0.5 · S 1 (≈ 100-150 production lines) · M 2 (≤ 400). Nothing larger than M.
- **Lanes:** BE 2 streams, SRE 2 streams, QA 2 streams (disjoint: `scripts/measure` + `infra/tests` vs `web/e2e`), FE 1, ML 1. Docs/gate roles carry dated tickets without units.

| Lane | Tickets (units) | Planned | Capacity |
|---|---|---|---|
| SRE | CI-NOTICE-CANCELLED 0.5, CI-DOC-CHECK 1, CI-TIERS-a 1, CI-TIERS-b 1, CI-RECON-ON-PR 1, ST-075b 1, ST-075c 1, ST-076a 1, ST-076c 1, ST-082 1, SMOKE-05 0.5 | 10 | 9.6 (at cap; ST-082 rollback part slips first) |
| BE | QA-VERIFY04R5-01 1, ST-074 1, ST-075a 0.5, ST-075d 0.5, ST-076b 1, ST-077 1, ST-078d 1, ST-081a 0.5 | 6.5 | 9.6 |
| QA | QA-TCR-04 0.5, QA-DOR-CHECK 0.5, QA-FLOW-METRICS 1, QA-PIN-05 1, ST-080 1, VERIFY-05 1 | 5 | 9.6 |
| FE | ST-078e 1, ST-079 1, ST-085 1 | 3 | 4.8 |
| ML | ST-084a 0.5, ST-084b 1 | 1.5 | 4.8 |
| Docs/gates | PM-5, BA-5, PE-5a, PE-5b, SEC-5, PD-5, PD-DR04, COACH-5, EM-ESC-05, EM-CLOSE-CHECKS, ST-078a/b/c, ST-081b, ST-083, RETRO-05 | dated | — |
| **Total** | 46 tickets (PLAN-05 is this PR) | **26 units** | 38.4 |

Process share: 12 of 46 tickets (CI-*, QA-TCR/DOR/FLOW/PIN, EM-*), 7.5 of 26 units (29 %), inside the PM's ≤ 40 % cap. Headroom ≈ 12.4 units is the review loop and the CI-first reserve.

### 2.1 WIP limits and flow (working-agreement §3; ADR 0056 decision 3)

| Stage | Limit this sprint | Rule |
|---|---|---|
| In progress | **4** (sprint brief; under §3's lane cap of 5) | no new ticket starts while 4 are in progress |
| In review | 3 | full → the next agent turn reviews |
| Awaiting QA | 2 | full → QA tests before anyone starts |
| Awaiting merge | 1 | merges run one at a time (ADR 0050) |

The EM status step (working-agreement §7 3c) records the four counts, the age of every open ticket, `open_defects.py`, the `merged_verdict.py` audit and the decisions-file grep for "can only|not covered|known gap" (until PRC-4.2 lands) in the ticket's decisions file. A breach needs a one-line reason. Flow metrics (cycle time, throughput, work item age, breaches) and cost per PR are reported by RETRO-05 from `flow_metrics.py` (G05-11), never as targets [ASB/AGL-02].

## 3. Committed backlog

Ticket fields: id, title, story, owner (role fit), tier (ADR 0056: 0 docs/process, 1 ordinary code, 2 security / personal data / schema / API contract), specialists (tier 2, working-agreement §6), depends_on, size, atomic items. Full scope per ticket in §3.7. Every code ticket: Gherkin scenario + integration test + unit tests first, seen failing, red output recorded in its decisions file (`Red:` line); principal-engineer review; senior-qa-engineer test of the PR head.

### 3.1 CI first (wave 0)

| ID | Title | Owner | Tier | Depends on | Size | Items |
|---|---|---|---|---|---|---|
| CI-NOTICE-CANCELLED | Cancelled and timed-out scheduled runs raise the red notice; root-cause the Flaky-test report hang | sre-devops-engineer | 1 | — | XS | PRC-1.1-1.3 |

### 3.2 Gate and process tickets (wave 1; ADR 0047 rule 2: before any build ticket that depends on them)

| ID | Title | Owner | Tier | Specialists | Depends on | Size | Items |
|---|---|---|---|---|---|---|---|
| CI-DOC-CHECK | CI `doc-check` job: repo paths exist, `[ASB/ID]` citations resolve to Confirmed rows, `.claude/agents` front matter parses, `check_flows.py --decider` | sre-devops-engineer | 1 | — | CI-NOTICE-CANCELLED | S | PRC-3.1-3.4 |
| CI-TIERS-a | `merge_ready.py`: path → tier classifier as data, fail closed to tier 2, specialist flags | sre-devops-engineer | 2 | security-privacy-engineer | CI-NOTICE-CANCELLED | S | PRC-2.1-2.3 |
| CI-TIERS-b | `merge_ready.py`: verdict sets per tier, QA by name on tier 1-2, security on tier 2, author-role verdicts ignored | sre-devops-engineer | 2 | security-privacy-engineer | CI-TIERS-a, CI-DOC-CHECK | S | PRC-2.4-2.7 |
| CI-RECON-ON-PR | `reconcile_due.py` in pr-policy; decisions-file findings joined to the ledger; id format written down | sre-devops-engineer | 1 | — | CI-NOTICE-CANCELLED | S | PRC-4.1-4.3 |
| QA-TCR-04 | Decide TCR rows 11 and 14 (retro F2/E2) | senior-qa-engineer | 0 | — | — | XS | §4.1 |
| QA-DOR-CHECK | `check_atomic_breakdown.py` in the doc-check job (DoR "enforced by check") | senior-qa-engineer | 1 | — | CI-DOC-CHECK | XS | PRC-7.1 |
| QA-FLOW-METRICS | `flow_metrics.py` over REST: cycle time, throughput, age, breaches, cost-row completeness; fix working-agreement §10 command | senior-qa-engineer | 1 | — | — | S | PRC-5.1-5.5 |
| PM-5 | Roadmap "Product Goal" section; S5 priorities, out-of-scope, FR-162 recommendation | product-manager | 0 | — | — | docs | — |
| BA-5 | DoR verdict per story; traceability rows; glossary (SLO, error budget, RPO, RTO, release candidate); FR-120 wording note | business-analyst | 0 | — | — | docs | all |
| PE-5a | ADR: SLIs, SLOs, burn-rate alerts, metrics backend (OTel collector + Prometheus `obs` profile) | principal-engineer | 0 | — | — | docs | NFR-041, NFR-042, NFR-049 |
| PE-5b | ADR: backup and restore (daily dump + object mirror, encryption, deletion within backups), rollback path | principal-engineer | 0 | — | — | docs | NFR-045, REL-1.2/1.3 |
| SEC-5 | Threat notes S5 (usability test, backup/restore, SLO/log pipeline, release build); `check_threat_notes.py` requires an ADR id on "Accepted residual" | security-privacy-engineer | 1 | — | — | S | NFR-069.1, NFR-050.9 |
| PD-5 | `flows-sprint-05.md`: degraded/error states, release-notes copy, usability task screens; per-SC WCAG gap list incl. 3.2.6 and 3.3.7; DR-05 cells scheduled | principal-designer | 0 | — | — | docs | USAB-1.1 |
| PD-DR04 | Collect the five DR-04 decider cells on shipped Sprint 4 screens (or a PO waiver request); re-read pending DR-01..03 cells | principal-designer | 0 | — | — | docs | — |
| COACH-5 | Domain review of RC copy and notices; ledger row for the single-weakness gap; usability drill safety list; P7/P15 fallback request draft; NFR-036.4 call types | pickleball-domain-coach | 0 | — | — | docs | FR-124, FR-055 |
| EM-ESC-05 | One PO escalation note: P6-P20, setting 6, the S5 "Done when" change, audit items 12-15, drill JSON in size — each with options, default, deadline | engineering-manager | 0 | — | PM-5 | docs | — |
| QA-VERIFY04R5-01 | `make demo` works on a flag-on stack (age-confirm demo users via the domain service); flags-on test fixture | senior-backend-engineer | 2 | security-privacy-engineer | — | S | DEMO-1.1 |

### 3.3 R1 release gates (wave 2: build; each starts only when its gates merged)

| ID | Title | Story | Owner | Tier | Specialists | Depends on | Size | Items |
|---|---|---|---|---|---|---|---|---|
| ST-074 | R1 read latency gate at 50 RPS, per endpoint, flags on, nightly `perf-r1` job | ST-074 | senior-backend-engineer | 1 | sre-devops-engineer | BA-5 | S | NFR-010.1-.9 |
| ST-075a | SLI export wiring to the collector; PII-free labels and logs test | ST-075 | senior-backend-engineer | 2 | security-privacy-engineer, sre-devops-engineer | PE-5a, SEC-5 | XS | NFR-069.1 |
| ST-075b | OTel collector + Prometheus in a Compose `obs` profile; env parity; series present | ST-075 | sre-devops-engineer | 1 | — | PE-5a | S | NFR-042.5 |
| ST-075c | Burn-rate rules + promtool tests; `inject_5xx.py` drill through the ST-075d seam; drill-only Compose override; `docs/ops/slo.md`; error-budget policy draft | ST-075 | sre-devops-engineer | 2 | security-privacy-engineer | ST-075a, ST-075b, ST-075d | S | NFR-041.1-.5, NFR-042.1-.4, NFR-049.1 |
| ST-075d | API 5xx fault value on the existing ADR 0012 seam `RACKET_FAULT_INJECTION` (honoured only when `APP_ENV=test`) | ST-075 | senior-backend-engineer | 2 | security-privacy-engineer, principal-engineer | PE-5a, SEC-5 | XS | NFR-041.5 (fault path), NFR-041.6 |
| ST-076a | Backup service: nightly encrypted `pg_dump` + object-store mirror; backup metadata with age | ST-076 | sre-devops-engineer | 2 | security-privacy-engineer | PE-5b, SEC-5 | S | NFR-045.1 |
| ST-076b | Confirmed-corrections integrity check (count + SHA-256) as a module + CLI | ST-076 | senior-backend-engineer | 2 | security-privacy-engineer | PE-5b | S | NFR-045.3 |
| ST-076c | `restore_drill.py`: destroy, restore, time RTO, read RPO, run integrity and object checks | ST-076 | sre-devops-engineer | 2 | security-privacy-engineer | ST-076a, ST-076b | S | NFR-045.1-.5 |
| ST-077 | Data-classification map + test that every table, column, bucket prefix and backup artefact is classified | ST-077 | senior-backend-engineer | 2 | security-privacy-engineer, principal-engineer | SEC-5 | S | NFR-063.1-.2 |
| ST-078a | ASVS 5.0 L2 assessment V1-V5 + `asvs_status.py` tool | ST-078 | security-privacy-engineer | 1 | principal-engineer | SEC-5 | S | NFR-050.1, .4, .5 |
| ST-078b | ASVS assessment V6-V10 | ST-078 | security-privacy-engineer | 0 | principal-engineer | ST-078a | docs | NFR-050.2, .4, .5 |
| ST-078c | ASVS assessment V11-V17; residual-risk ADR draft for the PO | ST-078 | security-privacy-engineer | 0 | principal-engineer | ST-078b | docs | NFR-050.3-.5 |
| ST-078d | API hygiene: `no-store` on every authenticated GET; BOLA matrix completeness test | ST-078 | senior-backend-engineer | 2 | security-privacy-engineer | SEC-5 | S | NFR-067.1, NFR-050.6 |
| ST-078e | Client hygiene: logout clears storage, SW never caches media, security headers, pre-hydration form lock | ST-078 | senior-frontend-engineer | 2 | security-privacy-engineer, principal-designer | SEC-5 | S | NFR-067.2-.3, NFR-050.7-.8 |
| ST-079 | `android-chrome` Playwright project; `@critical` tags; browser-matrix report; device checklist for P20 | ST-079 | senior-frontend-engineer | 1 | — | BA-5 | S | NFR-024.1-.3 |
| ST-080 | E2E tap/key counter: fix any call in ≤ 2 | ST-080 | senior-qa-engineer | 1 | principal-designer | BA-5, COACH-5 | S | NFR-036.4 |
| ST-081a | Coverage rule for single-weakness and 3+-drill sessions (red first) and the swap ITs | ST-081 | senior-backend-engineer | 1 | pickleball-domain-coach | COACH-5 | XS | FR-124.R1-R2, FR-141.R1 |
| ST-081b | Drills that close the gaps the new rule reports (≤ 6 drills) | ST-081 | pickleball-domain-coach | 0 | — | ST-081a | docs | FR-141.R1 |
| ST-082 | R1 release notes (+ checker), rollback drill, migration round-trip IT | ST-082 | sre-devops-engineer | 1 | pickleball-domain-coach | PE-5b, PM-5, COACH-5 | S | REL-1.1-1.3, FR-055.R1 |
| ST-083 | Usability-test kit for NFR-036 (protocol, tasks, interim consent, observation sheet) | ST-083 | principal-designer | 0 | — | PD-5, COACH-5, SEC-5 | docs | USAB-1.1 |
| ST-084a | ADR: model regression tolerances per NFR-006 metric; regression vs capability split | ST-084 | senior-ml-cv-engineer | 0 | — | — | docs | NFR-006.5 |
| ST-084b | Rally-segmentation F1 matcher (R1-R4), unit + property, mutation ≥ 0.80 | ST-084 | senior-ml-cv-engineer | 1 | — | ST-084a | S | NFR-006.1-.4 |
| ST-085 | SW unit tests for the offline plan read and sync queue; focus return per dialog close path | ST-085 | senior-frontend-engineer | 1 | principal-designer | — | S | NFR-034 (a), FR-124 offline |

### 3.4 Measurement pinning and close (wave 3)

| ID | Title | Owner | Tier | Depends on | Size |
|---|---|---|---|---|---|
| QA-PIN-05 | Pin every timed/load method (G05-01, G05-03 RTO, G05-10 integration) to its CI or nightly step by an infra test; G05-09/10 dry-run rows | senior-qa-engineer | 1 | ST-074, ST-076c, ST-075c | S |
| EM-CLOSE-CHECKS | `retro_ready.py` (RETRO trigger) and `retro05_check.py` (PR set = status map; open causes) under `docs/sprints/05/close-checks/` | engineering-manager | 1 | QA-FLOW-METRICS | S |
| VERIFY-05 | Measure G05-01..12 live; one merged PR per round | senior-qa-engineer | 0 | every ticket in §3.1-§3.4 except SMOKE-05, RETRO-05 | S |
| SMOKE-05 | Post-verify smoke on the close head (prototype, SLO drill, restore drill), stacks pruned | sre-devops-engineer | 0 | VERIFY-05 | XS |
| RETRO-05 | The one close: sprint report (DORA, flow, cost per PR), status files, all-role reflection, retro | engineering-manager | 0 | SMOKE-05, EM-CLOSE-CHECKS | docs |

### 3.5 Stories

| Story | Value | Priority (PM-5 confirms) | Tickets |
|---|---|---|---|
| ST-074 R1 reads stay fast under load | players get pages in ≤ 300 ms p95 | P1 | ST-074 |
| ST-075 We know when R1 is unhealthy | outages are seen before players report them | P1 | ST-075a/b/c/d |
| ST-076 Nothing a player corrected is lost | recovery within RPO/RTO | P1 | ST-076a/b/c |
| ST-077 Every stored datum has a class | privacy rules per class | P1 | ST-077 |
| ST-078 R1 passes an ASVS L2 review | security evidence for the RC | P1 | ST-078a-e |
| ST-079 R1 works on the phones players use | browser matrix | P1 | ST-079 |
| ST-080 Fixing a call is quick | NFR-036.4 | P1 | ST-080 |
| ST-081 "Not for me" never dead-ends | swap on single-weakness plans | P2 | ST-081a/b |
| ST-082 R1 can be released and rolled back | release notes, rollback | P1 | ST-082 |
| ST-083 The usability test can run the day testers arrive | NFR-036 kit | P1 | ST-083 |
| ST-084 R2 entry is measurable | tolerance ADR, rally F1 | P2 | ST-084a/b |
| ST-085 Offline and focus behaviour is tested | known coverage gaps closed | P2 | ST-085 |
| PRC-05 The process rules are enforced by checks | ADR 0056, retro 4 | P0 | CI-*, QA-TCR-04, QA-DOR-CHECK, QA-FLOW-METRICS, QA-PIN-05, EM-CLOSE-CHECKS |

### 3.6 Order of work and CI-first rule

1. **Wave 0:** CI-NOTICE-CANCELLED. If `main` turns red at any point, the next ticket is a `ci_fix` ticket that pre-empts everything (CI FIRST).
2. **Wave 1 (gates, in parallel within WIP 4; merge-by 2026-11-05):** CI-DOC-CHECK and CI-TIERS-a first (the tier ticket relieves review load), then CI-TIERS-b; QA-TCR-04 first in QA; PE-5a, PE-5b, SEC-5, PD-5, PD-DR04, COACH-5, PM-5, BA-5, EM-ESC-05 (sent by 2026-11-05); CI-RECON-ON-PR (due 2026-11-13); QA-VERIFY04R5-01 (due 2026-11-13).
3. **Wave 2 (build; merge-by 2026-11-11):** a story starts only when BA-5 marks it Ready and its gates merged (§3.8). SRE runs two streams (ST-075b/c and ST-076a/c); BE two (ST-074, ST-077, ST-078d / ST-075a, ST-075d, ST-076b, ST-081a); FE, QA, ML one each.
4. **Wave 3:** QA-PIN-05 and EM-CLOSE-CHECKS; then VERIFY-05 (2026-11-12) only when every build ticket is merged and every scorecard §6 row is rc 0; misses go to fix tickets `FIX-05-<n>` and a dated re-measure; SMOKE-05; RETRO-05 (2026-11-13) only when `retro_ready.py` exits 0.

### 3.7 Ticket specifications

Each block: story · atomic items · acceptance · tests carried (Gherkin / IT / unit) · QA test plan · bounded context · directories. "Red first" means the listed negative test is committed and seen failing before any implementation.

#### CI-NOTICE-CANCELLED (ci_fix)
PRC-05 · PRC-1.1-1.3 · **Acceptance:** a scheduled run concluding `cancelled` or `timed_out` opens/updates the `[CI-RED]` notice; `success`/`skipped` do not; the Flaky-test report job's hang is root-caused (bisect run 41622904539 vs 41434196891, step timings) and fixed or bounded with its own step timeout so the job ends < 45 min. · **Tests:** `infra/tests/test_scheduled_red_notice.py` cases for each conclusion (red first: `cancelled` → expected notice, today `none`); `tests/features/scheduled_red_notice.feature` scenario "a cancelled scheduled run is red". · **QA:** run the script against the recorded payload of 41622904539; confirm the next scheduled run's duration. · **Context:** platform/CI. · **Dirs:** `scripts/ci/scheduled_red_notice.py`, `.github/workflows/ci.yml` (flaky-report job only), `infra/tests/`.

#### CI-DOC-CHECK
PRC-05 · PRC-3.1-3.4 · **Acceptance:** a `doc-check` job in `ci-gate` runs `scripts/ci/check_docs.py` on changed `*.md` and `.claude/agents/*.md`: dangling repo path → fail; `[ASB/<ID>]` not Confirmed and not marked "(unverified)" → fail; agent front matter not parsing or missing `name`/`description`/`tools` → fail; `docs/design/tools/check_flows.py --decider` on the newest `flows-sprint-NN.md`. Runs on Tier 0 PRs too (draft skip as ADR 0052). · **Tests:** `infra/tests/test_doc_check.py` (planted break per rule, red first), workflow test that `ci-gate` needs `doc-check`. · **QA:** planted-break PR fixture set; runtime < 60 s. · **Context:** platform/CI. · **Dirs:** `scripts/ci/check_docs.py`, `.github/workflows/ci.yml`, `infra/tests/`.

#### CI-TIERS-a (tier 2)
PRC-05 · PRC-2.1-2.3 · **Acceptance:** `scripts/ci/review_tiers.py` (data: glob rules → tier + specialist roles), imported by `merge_ready.py`. **Resolution (no rule order):** a file gets the **highest** tier of every rule it matches, so a later or broader rule never lowers a tier; the PR gets the highest tier over its files; a path that matches no rule is tier 2 (fail closed). **Executable floor:** an executable file is at least tier 1 wherever it lives: extensions `*.py`, `*.sh`, `*.js`, `*.mjs`, `*.ts`, `*.tsx`, `*.sql`, any file under `.github/workflows/`, `Makefile`, `Dockerfile*`, or a file with a shebang line or the executable bit in the PR's tree. So `docs/security/tools/*.py` (incl. `check_threat_notes.py`, the new `asvs_status.py`), `docs/design/tools/*.py` (`check_flows.py`), `docs/domain/tools/*.py` and `docs/sprints/*/close-checks/*` are tier 1, never tier 0. **Tier 0** = a non-executable `*.md` file under `docs/**`, a top-level `*.md`, or `.claude/agents/*.md`, and only when no tier 1 or tier 2 rule also matches it. **Tier 2** globs per SEC-1 (auth, `video_ingest`, storage, media URLs, privacy/age/consent/retention, quotas, logging config, secrets, the fault seam `backend/src/racket/platform/fault*`, `.github/workflows/**` permissions, `backend/migrations/**`, `docs/architecture/api-*.md` (stays tier 2 although it also matches the tier 0 `docs/**/*.md` rule), `scripts/ci/merge_ready.py`, `scripts/ci/review_tiers.py`); specialist flags: UI → principal-designer, drills/domain → pickleball-domain-coach, `worker/`, `dataset/`, eval → senior-ml-cv-engineer, client security → senior-frontend-engineer. Tier is computed, never read from an author label. · **Tests:** `infra/tests/test_review_tiers.py` Scenario Outline over planted paths (red first: classifier absent → import error recorded), with these negative cases: `docs/security/tools/check_threat_notes.py` → 1; `docs/security/tools/asvs_status.py` → 1; `docs/sprints/05/close-checks/retro05_check.py` → 1; an extensionless file under `docs/` with a shebang → 1; `docs/architecture/api-matches.md` → 2; PR {`README.md`, `docs/x.md`, `docs/design/tools/check_flows.py`} → 1; PR {`docs/x.md`, `docs/architecture/api-x.md`} → 2; PR {`docs/x.md`, `docs/unknown/thing.bin`} → 2 (unmatched). · **QA:** QA writes the tier matrix scenarios before the code (writer/reviewer split). · **Context:** platform/CI. · **Dirs:** `scripts/ci/review_tiers.py`, `infra/tests/`.

#### CI-TIERS-b (tier 2) — required ticket (a) of ADR 0056
PRC-05 · PRC-2.4-2.7 · **Acceptance:** `merge_ready.py` requires per tier: T0 one fresh-context APPROVE (any role but the author's) + `doc-check` success on the head; T1 `Reviewer: principal-engineer` + `Reviewer: senior-qa-engineer` APPROVE on the head + `ci-gate` success; T2 = T1 + `Reviewer: security-privacy-engineer` APPROVE on the head on **every** tier 2 PR, whatever made it tier 2 (security path, schema or migration, API contract, or a fail-closed unmatched path; kickoff SEC-1) + flagged specialists. **Author role is computed, never written by the author:** `merge_ready.py` looks up the PR's head branch (`s05/<id>`) in the current sprint plan's §15 ticket map on `main` (`Owner` column, mapped by a fixed abbreviation table in `review_tiers.py`: be → senior-backend-engineer, sre → sre-devops-engineer, qa → senior-qa-engineer, and so on), cross-checked with `docs/sprints/<nn>/status.json` `ticket_prs` once the status step has recorded the PR; on disagreement or a branch with no row it fails closed and names the missing row. PR body, labels and the author's own comments are never read for the author role. An APPROVE whose `Reviewer:` role equals the computed author role is ignored; exit codes and messages name the missing role. Interim rule ends when this merges. · **Tests:** `infra/tests/test_merge_ready_tiers.py` with `github_stub.py` fixtures: T0 docs PR passes; T1 PE + senior-backend fails; T2 PE + QA without security fails, once each for a security path, `backend/migrations/` only, `docs/architecture/api-*.md` only and an unmatched path only; wrong-role verdict ignored; author role taken from the ticket map even when the PR body claims another role; head branch with no ticket-map row fails closed; `tests/features/merge_tiers.feature`. · **QA:** planted wrong-role APPROVE; T0 PR with a hidden code file. · **Context:** platform/CI. · **Dirs:** `scripts/ci/merge_ready.py`, `infra/tests/`, `docs/ops/branch-protection.md` §3.

#### CI-RECON-ON-PR
PRC-05 · PRC-4.1-4.3 · **Spec by** engineering-manager in the decisions file (red-first acceptance: a planted decisions file naming a major with no ledger row fails pr-policy). **Acceptance:** `pr-policy` runs `reconcile_due.py --pr`; fails on (a) a blocker/major id in a changed `decisions/*.md` with no ledger row, (b) a "known gap|can only|not covered" line without an id; id format documented. · **Tests:** `infra/tests/test_reconcile_on_pr.py` (red first). · **QA:** run on the merged Sprint 4 decisions (expect ST-062-part2 flagged). · **Dirs:** `scripts/measure/reconcile_due.py`, the `pr-policy` job in `.github/workflows/ci.yml`, `infra/tests/`, `docs/ops/evidence-runs.md`.

#### QA-TCR-04
Carry-over F2 · **Acceptance:** rows 11 and 14 of `docs/sprints/04/test-change-requests.md` decided (accept/reject with reason, head SHA, files); `grep -c Pending` → 0. Docs ticket: TDD does not apply; doc checks run (paths exist). · **Dirs:** `docs/sprints/04/test-change-requests.md`, `docs/sprints/05/decisions/QA-TCR-04.md`.

#### QA-DOR-CHECK
PRC-7.1 · **Acceptance:** `scripts/ci/check_atomic_breakdown.py docs/sprints/<nn>/requirements-breakdown.md` fails on an NFR row missing metric, method, target or test level, an FR `Rule:` without a negative Example, or an id that `measurelib._FINDING_ID` cannot parse; added to `doc-check`. · **Tests:** `infra/tests/test_atomic_breakdown.py` (planted rows, red first). · **Dirs:** `scripts/ci/`, `infra/tests/`.

#### QA-FLOW-METRICS
PRC-5.1-5.5 · **Acceptance:** `scripts/measure/flow_metrics.py` reads `GET /repos/.../pulls?state=closed`, `/pulls/{n}/commits` and `actions/runs` (REST only) and writes cycle time (median, max), throughput, work item age of open ticket PRs, WIP breaches (from `decisions/*.md` "Stage counts" lines), CI minutes per PR, and cost-table completeness; working-agreement §10 command replaced by the script call. · **Tests:** unit tests on stubbed REST JSON (red first). · **QA:** dry-run against Sprint 4's PR range; numbers equal sprint-report §2 ± rounding. · **Dirs:** `scripts/measure/`, `infra/tests/`, `docs/process/working-agreement.md` (§10 one line).

#### PM-5, BA-5, PE-5a, PE-5b, PD-5, PD-DR04, COACH-5, EM-ESC-05, ST-078b, ST-078c, ST-081b, ST-083, ST-084a (docs, tier 0)
TDD does not apply (no executable behaviour; text and decisions). Each runs the doc checks: referenced paths exist, citations resolve to Confirmed rows or carry "(unverified)", front matter parses (by hand until CI-DOC-CHECK merges, then by the job). **Outputs:** PM-5 `docs/sprints/roadmap.md` §"Product Goal" + `decisions/PM-5.md` (priorities, FR-162 recommendation). BA-5 `docs/sprints/05/requirements-breakdown.md` DoR column, `docs/requirements/traceability-matrix.md` rows, `docs/process/ddd-guidelines.md` glossary. PE-5a `docs/decisions/0057-*.md` (SLOs, burn-rate windows, `obs` profile, no paid service). PE-5b `docs/decisions/0058-*.md` (backup, restore, encryption, backups inside the NFR-066 purge, rollback). PD-5 `docs/design/flows-sprint-05.md` with states, HAX, WCAG tables, DR-05 decider cells dated. PD-DR04 `docs/design/flows-sprint-04.md` §14.2 cells or a waiver request in EM-ESC-05; any reject becomes a ledger row. COACH-5 `docs/domain/drill-review-checklist.md` §3.1, ledger row COACH-S5-01, `docs/domain/usability-drill-safety.md`. EM-ESC-05 `docs/sprints/05/po-escalations.md` (question, options, recommendation, evidence, deadline per item; working-agreement §8). ST-078b/c `docs/security/asvs-l2-checklist.md` rows, `docs/decisions/0059-*.md` draft (Proposed, PO decides). ST-081b `content/drills/*.json` (≤ 6 drills, lint + coverage green). ST-083 `docs/design/usability-test-kit-r1.md`. ST-084a `docs/decisions/0060-*.md`.

#### SEC-5 (tier 1: tool change)
**Acceptance:** `docs/security/threat-notes-sprint-05.md` with T5-* rows for ST-075 (labels, logs, alert payloads), ST-076 (backup encryption, credentials, deletion inside backups), ST-083 (tester data, possible minors, footage), ST-082 (release build); `check_threat_notes.py` fails on an "Accepted residual" row without an ADR id. · **Tests:** `docs/security/tools` tests with a planted residual row (red first). · **Dirs:** `docs/security/`.

#### QA-VERIFY04R5-01 (tier 2: age confirmation is personal data)
DEMO-1.1 · **Acceptance:** `make demo` on a flag-on stack confirms the demo users' age through the public age-confirmation API (the domain service the player uses), rc 0, twice (idempotent); no direct SQL. Adds a `flags_on` pytest fixture for integration tests. · **Tests:** `infra/tests/test_seed_demo_plan.py` flag-on case (red: 403 `age_confirmation_required`), `infra/tests/test_demo_seed_live.py` on a flag-on Compose project. · **QA:** `make up` with the four FEATURE_* flags on, `make demo` twice. · **Context:** players (identity), demo tooling. · **Dirs:** `scripts/demo/`, `infra/tests/`, `backend/tests/conftest.py` (fixture).

#### ST-074
NFR-010.1-.9 · **Acceptance:** `backend/tests/perf/locustfile_r1.py` (match, score sheet, dashboard, plan reads; seeded per user); `perf_verdict.py` gains `--per-endpoint`, `--min-rps`, `--warmup-s`, `--max-error-pct`; nightly job `perf-r1` (not PR-blocking at first, judgment, PE risk) on a flags-on stack. Any endpoint over target → BE fix in the same ticket only if ≤ 400 lines, else a `FIX-05-n` ticket. · **Tests:** `infra/tests/test_perf_verdict_endpoints.py` (red: a CSV with one slow endpoint must fail), `tests/features/r1_read_latency.feature`. · **QA:** dry-run row G05-01 incl. planted `--p95-ms 1`. · **Context:** match, scoring, analytics, coaching reads. · **Dirs:** `backend/tests/perf/`, `scripts/ci/perf_verdict.py`, `.github/workflows/nightly-quality.yml`.

#### ST-075a (tier 2)
NFR-069.1 · **Acceptance:** API and worker export metrics over OTLP when `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` is set; IT scans log lines and metric attributes after a demo run for emails, nicknames, signed URLs → 0. · **Tests:** `backend/tests/integration/test_it_05_pii_labels.py` (red first: planted email in an attribute fails). · **Context:** platform. · **Dirs:** `backend/src/racket/platform/`, `backend/tests/`.

#### ST-075b
NFR-042.5 · **Acceptance:** Compose profile `obs` with `otel-collector` and `prometheus` (pinned images), API env wired, `test_shipped_env_example_and_compose_are_in_parity` extended; after `make demo` both SLI series exist. · **Tests:** `infra/tests/test_compose_obs_profile.py` (red first), live dry-run. · **Dirs:** `infra/compose.yaml`, `infra/observability/`, `infra/env.example`, `infra/tests/`.

#### ST-075d (tier 2)
NFR-041.5 (fault path), NFR-041.6 · **Owner:** senior-backend-engineer (the only `backend/src` slice of ST-075 besides ST-075a). **Acceptance:** no new variable and no new flag. The existing ADR 0012 seam `RACKET_FAULT_INJECTION`, which `Settings.from_env` keeps only when `APP_ENV=test` (`backend/src/racket/platform/settings.py` line 248, pinned by `backend/tests/unit/platform/test_settings.py::test_fault_injection_is_dropped_outside_test`), gains one value, `api:5xx_on_header`: a request carrying `X-Racket-Fault: 5xx` then gets a 500 problem response from a platform middleware before routing. Without the header, or with any other seam value, nothing changes. The middleware reads only `Settings.fault_injection`, so under `APP_ENV` dev, staging or prod it is inert by construction; shipped defaults (`infra/env.example` `APP_ENV=dev`, `infra/compose.yaml`) do not change. QA adds the seam row to `backend/tests/support/contract.py` (ADR 0012 owner). · **Tests (red first):** `backend/tests/unit/platform/test_fault_seam.py` (seam + header → 500; header without the seam → normal; seam value set with `APP_ENV=dev` → header ignored, negative), `backend/tests/integration/test_it_05_12_fault_seam.py` over `ASGITransport`, a `tests/features/slo_alerts.feature` step. · **Review:** tier 2: principal-engineer, senior-qa-engineer test, security-privacy-engineer APPROVE on the head. · **Context:** platform. · **Dirs:** `backend/src/racket/platform/fault.py` (new), the middleware registration line in `backend/src/racket/platform/app.py`, `backend/tests/`.

#### ST-075c (tier 2)
NFR-041.1-.5, NFR-042.1-.4, NFR-049.1 · **Acceptance:** `infra/observability/alerts/slo.yml` (4 alerts) and `slo.test.yml` (8 promtool cases); `scripts/ops/inject_5xx.py` sends `--rate` % of its requests with `X-Racket-Fault: 5xx` through the ST-075d seam (no `backend/src` change in this ticket); `infra/compose.fault-drill.yaml`, a drill-only override that adds nothing but `RACKET_FAULT_INJECTION: api:5xx_on_header` to the `api` service. The G05-02 stack gets `APP_ENV=test` from the shell for its own Compose project (`racket-obs05`; shell values override `infra/.env`), so `infra/env.example` keeps `APP_ENV=dev` and `infra/compose.yaml` stays unchanged. Known test-mode difference: the session cookie is not `__Host-`/Secure under `APP_ENV=test` (`infra/compose.yaml` web-tls note); the drill calls the API only, so this does not touch the SLI series. `docs/ops/slo.md`; `docs/ops/error-budget-policy.md` (draft, P17). · **Tests:** promtool cases (red first: rules absent), `infra/tests/test_slo_rules.py` wraps promtool, `infra/tests/test_compose_fault_drill.py` (the override sets only the seam variable; `infra/compose.yaml` and `infra/env.example` never mention `RACKET_FAULT_INJECTION` and `env.example` keeps `APP_ENV=dev`, negative pin), `tests/features/slo_alerts.feature`. · **Review:** tier 2 with security-privacy-engineer (it drives a fault path). · **QA:** G05-02 dry-run row incl. planted 100 % threshold and the header sent to a `make up` stack (`APP_ENV=dev`) → no 5xx. · **Dirs:** `infra/observability/alerts/`, `infra/compose.fault-drill.yaml`, `scripts/ops/`, `docs/ops/`, `infra/tests/`.

#### ST-076a (tier 2)
NFR-045.1 · **Acceptance:** `backup` service (profile `ops`) runs `pg_dump -Fc` and mirrors the object store nightly and on demand, encrypted at rest (key from `.local`, never in git), writes `backup.json` metadata with UTC time; deletion within backups as PE-5b decides. · **Tests:** `infra/tests/test_backup_service.py` (red: age > 24 h → `stale`), IT that a backup restores to a scratch DB. · **Dirs:** `infra/compose.yaml`, `infra/docker/backup/`, `scripts/ops/`, `infra/tests/`.

#### ST-076b (tier 2)
NFR-045.3 · **Acceptance:** `racket.platform.integrity.corrections_fingerprint()` → (count, sha256) over confirmed corrections in a stable order; CLI `racket-integrity`. · **Tests:** unit (ordering, empty table), IT with a planted deleted row → mismatch (red first). · **Context:** scoring (corrections). · **Dirs:** `backend/src/racket/platform/`, `backend/tests/`.

#### ST-076c (tier 2)
NFR-045.1-.5 · **Acceptance:** `scripts/ops/restore_drill.py` seeds, backs up, fingerprints, destroys volumes, restores, times to healthy + checks, writes JSON (`rpo_hours`, `rto_minutes`, `corrections.equal`, `objects.equal`); `--plant-delete-correction` → rc 1; `docs/ops/restore-runbook.md`. · **Tests:** `infra/tests/test_restore_drill.py` on fixture JSON (red first), live dry-run G05-03. · **Dirs:** `scripts/ops/`, `docs/ops/`, `infra/tests/`.

#### ST-077 (tier 2)
NFR-063.1-.2 · **Acceptance:** `docs/security/data-classification.md` (class, encryption, retention, access per type; classes decided by the security-privacy-engineer in review); `backend/tests/integration/test_it_05_data_classification.py` walks SQLAlchemy metadata, bucket prefixes and backup artefacts. · **Tests:** red first: planted unclassified column. · **Dirs:** `docs/security/`, `backend/tests/`.

#### ST-078a (tier 1: tool)
NFR-050.1, .4, .5 · **Acceptance:** `docs/security/tools/asvs_status.py` counts statuses per chapter and fails per scorecard G05-07; V1-V5 rows assessed with evidence commands or fix-ticket ids. · **Tests:** tool unit tests (planted `Not assessed`, `Fail` without owner, `Pass` without evidence). · **Dirs:** `docs/security/`.

#### ST-078d (tier 2)
NFR-067.1, NFR-050.6 · **Acceptance:** every authenticated GET sends `Cache-Control: no-store`; a test enumerates FastAPI routes with an id path parameter and fails if one is missing from `bola.MATRIX`. · **Tests:** `test_it_05_no_store.py`, `test_bola_routes_complete.py` (red first). · **Dirs:** `backend/src/racket/platform/`, `backend/tests/`.

#### ST-078e (tier 2)
NFR-067.2-.3, NFR-050.7-.8 · **Acceptance:** logout clears local/session storage, IndexedDB and SW caches; SW never caches media responses; web origin sends CSP, `nosniff`, frame denial; every `onSubmit` form disabled until hydrated. · **Tests:** Vitest SW handler tests, component tests per form, `e2e/sprint-05/logout-hygiene.spec.ts`, `test_it_05_security_headers.py` (red first). · **Dirs:** `web/src/`, `web/tests/`, `web/e2e/sprint-05/`, `backend/tests/integration/` (header IT).

#### ST-079
NFR-024.1-.3 · **Acceptance:** `android-chrome` project (`devices['Pixel 7']`, Chrome channel on CI) in `projects.ts`; `@critical` tag on E2E-04-01..05, sign-in, upload resume; nightly runs all three projects; `scripts/measure/browser_matrix.py`; `docs/qa/device-checklist-r1.md` for P20. · **Tests:** `web/tests/projects.test.ts` (red: unknown project), `e2e-helpers-journey-binding` covers tags. · **Dirs:** `web/e2e/`, `web/tests/`, `scripts/measure/`, `.github/workflows/nightly-quality.yml`.

#### ST-080
NFR-036.4 · **Acceptance:** `e2e/sprint-05/fix-call-taps.spec.ts` counts taps/keys from the screen where a call is seen to the corrected state per call type (COACH-5 list) and annotates `taps`; fails > 2. · **Tests:** the spec itself + a planted 3-step helper unit test (red first). · **Dirs:** `web/e2e/sprint-05/`, `web/tests/`.

#### ST-081a
FR-124.R1-R2, FR-141.R1 · **Acceptance:** `racket-drill-coverage` checks single-target cells and ≥ 3-drill sessions; ITs for swap on single-weakness plans; the check is expected red on today's library and goes green with ST-081b (pair merged in order a then b; a's PR records the red, the CI job marks the coverage step `@red-until ST-081b` per ADR 0046). · **Tests:** `tests/features/plan_follow_through.feature` new Rules; `test_it_05_swap_single_weakness.py`; unit on the coverage rule. · **Dirs:** `backend/src/racket/coaching/`, `backend/tests/`, `tests/features/`.

#### ST-082
REL-1.1-1.3, FR-055.R1 · **Acceptance:** `docs/releases/r1-rc.md`; `scripts/ci/check_release_notes.py` (FRs, flags, limitations with P-n, "unofficial scoring"); `scripts/ops/rollback_drill.py`; `test_it_05_migration_roundtrip.py`. · **Tests:** red first: notes without the notice fail; a migration without `downgrade` fails. · **Dirs:** `docs/releases/`, `scripts/ci/`, `scripts/ops/`, `backend/tests/`.

#### ST-084b
NFR-006.1-.4 · **Acceptance:** `backend/src/racket/dataset/rally_f1.py` pure matcher; precision, recall, F1; no I/O. Added to the nightly mutation list. · **Tests:** `backend/tests/unit/dataset/test_rally_f1.py` with R1-R4 Examples, Hypothesis property (one-to-one, F1 ∈ [0,1]), `tests/features/rally_f1.feature`. · **Context:** dataset (evaluation). · **Dirs:** `backend/src/racket/dataset/`, `backend/tests/unit/dataset/`, `.github/workflows/nightly-quality.yml`.

#### ST-085
NFR-034 (a), FR-124 offline · **Acceptance:** Vitest tests for the SW offline plan read ("as of" line) and sync-once queue; component tests: focus returns to "Not for me" on Close, Cancel and Esc (P-03.R1-R3). · **Tests:** red first per close path. · **Dirs:** `web/src/`, `web/tests/`.

#### QA-PIN-05
PRC-8.1 · **Acceptance:** infra tests assert the scorecard §4 commands equal the CI/nightly step commands for G05-01, G05-03 (RTO timer), G05-10 (integration form); G05-09/G05-10 §6 rows. · **Dirs:** `infra/tests/`, `docs/sprints/05/goal-scorecard.md` §6 (own rows).

#### EM-CLOSE-CHECKS
PRC-6.1-6.3 · **Acceptance:** `docs/sprints/05/close-checks/retro_ready.py` and `retro05_check.py` with tests (planted open VERIFY PR, planted extra PR, planted closed cause). The orchestrator calls `retro_ready.py` before briefing RETRO-05. · **Dirs:** `docs/sprints/05/close-checks/`.

#### VERIFY-05, SMOKE-05, RETRO-05
VERIFY-05 per scorecard §3 (precondition: every build ticket merged, every §6 row rc 0). SMOKE-05: `make up` → demo → SLO drill → restore drill → `make down`, `df -h /` before and after. RETRO-05: the single close PR (status files, sprint report with DORA/flow/cost, retro with the all-role reflection, review of WIP limits and the 12-role question).

### 3.8 Definition of Ready check (business-analyst with engineering-manager, 2026-11-03)

| Story | Atomic breakdown | Gates | DoR at planning |
|---|---|---|---|
| ST-074 | NFR-010.1-.9 complete | none | **Ready** after BA-5 merges |
| ST-075 | NFR-041/042/069/049 items | PE-5a, SEC-5 | Not Ready: waiting on PE-5a, SEC-5 |
| ST-076 | NFR-045.1-.5 | PE-5b, SEC-5 | Not Ready: waiting on PE-5b, SEC-5 |
| ST-077 | NFR-063.1-.2 | SEC-5 | Not Ready: waiting on SEC-5 |
| ST-078 | NFR-050.1-.9, NFR-067.1-.3 | SEC-5 | Not Ready: waiting on SEC-5 |
| ST-079 | NFR-024.1-.3 (.4/.5 human) | none | Ready after BA-5 |
| ST-080 | NFR-036.4 | COACH-5 (call types) | Not Ready: waiting on COACH-5 |
| ST-081 | FR-124.R1-R2, FR-141.R1 | COACH-5 | Not Ready: waiting on COACH-5 |
| ST-082 | REL-1.1-1.3, FR-055.R1 | PE-5b, PM-5, COACH-5 | Not Ready: waiting on those |
| ST-083 | USAB-1.1 | PD-5, COACH-5, SEC-5 | Not Ready |
| ST-084 | NFR-006.1-.5 | ST-084a (ADR) | ST-084a Ready; ST-084b waits on it |
| ST-085 | gap tests | none (existing flows) | Ready |
| PRC-05 | PRC-1..8 | none | Ready |

Per BA-1, "Ready" means its gate tickets are merged with PR numbers; the orchestrator does not route a "Not Ready" story (working-agreement §7 3e).

## 4. Task breakdown per role agent

| Role | Tickets |
|---|---|
| engineering-manager | PLAN-05, EM-ESC-05, EM-CLOSE-CHECKS, RETRO-05; status steps; CI-RECON-ON-PR spec |
| product-manager | PM-5; readiness recommendation after VERIFY-05 (in RETRO-05) |
| business-analyst | BA-5 |
| principal-engineer | PE-5a, PE-5b; review of every tier 1-2 PR (and tier 0 until CI-TIERS-b merges) |
| principal-designer | PD-5, PD-DR04, ST-083; UI reviewer |
| security-privacy-engineer | SEC-5, ST-078a/b/c; tier 2 reviewer |
| pickleball-domain-coach | COACH-5, ST-081b; domain reviewer |
| senior-backend-engineer | QA-VERIFY04R5-01, ST-074, ST-075a, ST-075d, ST-076b, ST-077, ST-078d, ST-081a |
| senior-frontend-engineer | ST-078e, ST-079, ST-085 |
| senior-qa-engineer | QA-TCR-04, QA-DOR-CHECK, QA-FLOW-METRICS, ST-080, QA-PIN-05, VERIFY-05; tier 1-2 test review of every code PR |
| sre-devops-engineer | CI-NOTICE-CANCELLED, CI-DOC-CHECK, CI-TIERS-a/b, CI-RECON-ON-PR, ST-075b/c, ST-076a/c, ST-082, SMOKE-05; P5 prune owner |
| senior-ml-cv-engineer | ST-084a, ST-084b; reviewer of worker/dataset/eval PRs |

## 5. TDD plan (negative case first) [EP/ENG-18]

Order in every code ticket: (1) Gherkin scenario committed, (2) integration test, (3) unit tests — all seen failing, the red output pasted in `decisions/<ID>.md` with a `Red:` line; (4) smallest implementation; (5) refactor in a separate commit. Negative case first per ticket:

| Ticket | First red test |
|---|---|
| CI-NOTICE-CANCELLED | `cancelled` conclusion → expects a notice; today `none` |
| CI-TIERS-a / -b | unmatched path → tier 2; T1 PR with PE + senior-backend only → must fail |
| CI-DOC-CHECK | dangling path in a planted Markdown file |
| CI-RECON-ON-PR | decisions file with a major id and no ledger row |
| QA-FLOW-METRICS | stub PR with no merge time is excluded from throughput |
| QA-VERIFY04R5-01 | flag-on `make demo` → 403 today |
| ST-074 | one endpoint over 300 ms p95 must fail the verdict |
| ST-075a | planted email attribute detected |
| ST-075c | 0.1 % 5xx series must not fire |
| ST-075d | `X-Racket-Fault: 5xx` with the seam set under `APP_ENV=dev` must not return 500 |
| ST-076a/b/c | 25 h old backup is stale; deleted correction detected; planted drill rc 1 |
| ST-077 | unclassified column detected |
| ST-078d/e | authenticated GET without `no-store`; route missing from BOLA matrix; media in SW cache |
| ST-079 | unknown project name rejected |
| ST-080 | 3-step path counted as 3 |
| ST-081a | single-weakness solo-wall cell reported as gap |
| ST-082 | release notes without the unofficial notice |
| ST-084b | end 1.01 s off is not a match |
| ST-085 | Esc does not return focus |

Docs tickets state why TDD does not apply and run the doc checks (§3.7). Mutation: every new domain module joins the nightly mutation list in its own PR (ST-084b, ST-076b).

## 6. Integration tests (new ids)

| IT id | Ticket | Boundary | Asserts |
|---|---|---|---|
| IT-05-01 | ST-075a | API + OTel exporter | metric attributes and logs carry no email, nickname or signed URL |
| IT-05-02 | ST-075b | Compose `obs` | SLI series present after a demo upload |
| IT-05-03 | ST-076a | backup service + Postgres | backup restores to a scratch DB; metadata age |
| IT-05-04 | ST-076b | Postgres | fingerprint equal after dump/restore; differs after a planted delete |
| IT-05-05 | ST-077 | ORM metadata + object store | every table/column/prefix classified |
| IT-05-06 | ST-078d | API | `no-store` on every authenticated GET |
| IT-05-07 | ST-078d | API routes | every id route in `bola.MATRIX` |
| IT-05-08 | ST-078e | web origin | CSP, `nosniff`, frame denial |
| IT-05-09 | ST-081a | plan API | swap on single-weakness plan; 409 when none fits |
| IT-05-10 | ST-082 | Alembic + Postgres | each migration down/up round-trip |
| IT-05-11 | QA-VERIFY04R5-01 | demo seeding + identity | flag-on seeding age-confirms through the service |
| IT-05-12 | ST-075d | API + `Settings` | fault header → 500 only when `APP_ENV=test` and the seam value is `api:5xx_on_header` |

Every earlier IT id keeps passing (G05-10); integration stays within the 600 s CI budget in its parallel form.

## 7. Gherkin scenarios

```gherkin
# tests/features/merge_tiers.feature (CI-TIERS-b)
Feature: The merge gate requires the verdicts of the PR's risk tier
  Rule: PRC-2.5 Tier 1 needs the principal-engineer and the senior-qa-engineer on the head
    Example: both approve the head SHA
      Given a PR that changes only "backend/src/racket/analytics/x.py"
      And APPROVE verdicts from principal-engineer and senior-qa-engineer on the head
      When merge_ready.py runs
      Then it exits 0
    Example: a senior-backend verdict does not replace QA
      Given the same PR with APPROVE from principal-engineer and senior-backend-engineer
      When merge_ready.py runs
      Then it exits non-zero naming "senior-qa-engineer"
  Rule: PRC-2.1 An unclassified path is tier 2
    Example: a new top-level directory
      Given a PR that adds "newdir/tool.py"
      When the tier is computed
      Then the tier is 2

# tests/features/slo_alerts.feature (ST-075c)
Feature: Burn-rate alerts fire on real error budgets only
  Rule: NFR-041.3 A fast burn fires the fast-burn alert
    Example: 10 % 5xx for 10 minutes
      Given the obs profile is running with the SLO rules
      When 10 % of API responses are 5xx for 10 minutes
      Then "ApiAvailabilityFastBurn" is firing within 10 minutes
    Example: 0.1 % 5xx does not fire
      When 0.1 % of API responses are 5xx for 10 minutes
      Then no SLO alert is firing

# tests/features/restore_drill.feature (ST-076c)
Feature: A restore loses no confirmed correction
  Rule: NFR-045.3 Corrections fingerprint is equal after restore
    Example: clean drill
      Given a seeded stack with a fresh backup
      When the volumes are destroyed and restored
      Then the corrections count and SHA-256 equal the values before
    Example: a correction lost
      Given a backup taken before one confirmed correction was deleted
      When the drill compares fingerprints
      Then the drill fails naming "corrections"

# tests/features/plan_follow_through.feature (ST-081a, new rules)
  Rule: FR-124.R1 Swap on a single-weakness plan returns a fitting alternative
    Example: solo player with a wall
      Given a plan that trains one weakness for a solo player with a wall
      When the player presses "Not for me" on a drill
      Then a different drill for the same metric that fits the preferences replaces it
    Example: no alternative
      Given the library has one fitting drill for that metric
      When the player presses "Not for me"
      Then the answer is 409 "no_alternative" and the plan is unchanged

# tests/features/rally_f1.feature (ST-084b)
Feature: Rally segmentation F1 matching
  Rule: NFR-006.1 Start and end within 1.0 s
    Example: within tolerance → 1 true positive
    Example: end 1.01 s off → 0 true positives, 1 FP, 1 FN

# tests/features/r1_read_latency.feature (ST-074)
Feature: R1 reads meet latency at 50 RPS
  Rule: NFR-010.7 GET /me/plan p95 ≤ 300 ms
    Example: verdict passes on a run within target
    Example: verdict fails naming "plan" when p95 is 301 ms
```

`tests/features/scheduled_red_notice.feature`, `release_notes.feature`, `data_classification.feature` follow the same Rule/Example shape (one happy, one negative per rule) in their tickets.

## 8. Quality gates

1. **Merge:** only via `merge_ready.py` on the exact head SHA, one at a time (ADR 0050). **Interim until CI-TIERS-b merges:** every PR needs principal-engineer + a senior-* APPROVE on the head; for tier 1 the senior verdict is the senior-qa-engineer's. After it merges: tier rules as §3.7 CI-TIERS-b.
2. **CI:** `ci-gate` green on the head (lint, types, unit, integration ≤ 600 s, E2E chromium + webkit, axe, BOLA, dependency and secret scans, `Red:` check, test immutability, size, `doc-check` once merged, reconcile in pr-policy once merged).
3. **Size:** ≤ 400 production lines (`check_pr_size.py`); a waiver only while draft, by the PR-policy step.
4. **Nightly (not PR-blocking at first, judgment):** `perf-r1` (G05-01), SLO promtool tests run per PR (cheap), restore drill and android-chrome nightly, mutation (coaching, rules, rally F1).
5. **Gates with tickets (retro 4 L15):** tiers CI-TIERS-a/b; doc checks CI-DOC-CHECK + QA-DOR-CHECK; 50 RPS ST-074; SLO alerts ST-075c; restore ST-076c; browser matrix ST-079; ASVS ST-078a-c; classification ST-077; release notes ST-082; method pins QA-PIN-05.
6. **Reviewer checklist additions (kickoff PE-2, QA-5, SEC-5, FE-5):** config wired end to end (Compose, CI, env.example parity); behaviour with every flag on; "which CI step does this number come from?"; "configurations exercised" line in every verdict; author-found gaps raised as findings; Nits never flip a verdict; one verdict per head SHA.

## 9. Definition of Done

Story level (`docs/process/definition-of-done.md`) plus, for this sprint:
- [ ] Gherkin + IT + unit tests first, seen failing, `Red:` output in the decisions file; docs tickets state why TDD does not apply and show the doc checks.
- [ ] Tier verdicts on the head SHA and the senior-qa-engineer test of the head (tier 1-2); `ci-gate` green.
- [ ] Atomic items listed in the decisions file; traceability rows added in the same PR.
- [ ] Any new setting wired to Compose and `env.example` (parity test), exercised flags on and off.
- [ ] Security tickets name the ASVS rows they move.
- [ ] Author-found gaps written as parseable finding ids with ledger rows (L13).
- [ ] **Cost per PR table** in `decisions/<ID>.md`: one row per round (author build, each review, each fix, each CI round) with `wall_time_min`, `total_cost_usd` or tokens when exposed, otherwise "not measured" — never estimated (ADR 0056 decision 1).
- [ ] The method's §6 dry-run row (rc 0 and planted-failure rc) for tickets that own a scorecard method.
- [ ] Stacks the ticket started are torn down; `df -h /` at start and end.

### 9.1 Sprint-DoD rows for human-gated items (PO P12 option b)
Scorecard §5 rows S5-P6 … S5-CAL, each "not met: waiting on P-n" until the human supplies the input.

## 10. Risks for this sprint

| Risk | Raised by | Mitigation |
|---|---|---|
| Goal unmeetable if human gates are in it | PM, BA, PE, QA | P12 rows; EM-ESC-05 asks the PO to change the S5 "Done when" |
| SRE lane at capacity (10 of 9.6) | EM (judgment) | ST-082 rollback part and SMOKE-05 slip first; QA owns flow metrics |
| Changing the merge gate (tiers) can block or open merges | PE, SEC, SRE | tier 2 review with security; planted fixtures; fail closed |
| Interim review rule saturates "in review 3" | EM, PE, FE | tier ticket first; PE holds tier 0 reviews to correctness |
| SLO/restore infra from zero; disk-hungry | PE, SRE, BE | PE-5a/5b first; nightly placement; precheck 10/16 GB; creator prunes |
| Integration budget (432.6 s of 600 s) | BE, SRE | new heavy suites nightly; each IT's cost in its PR |
| Measurement defects repeat (M2, M10, M12) | all | §6 rc 0 + planted-failure rows; QA-PIN-05 |
| Cost-per-PR data missing or inconsistent | EM, SRE | one table format (§9); QA-FLOW-METRICS completeness check |
| QA bottleneck (awaiting QA 2) | QA | QA reviews before own tickets; age tracked per status step |
| Personal data in logs, labels, backups, usability sessions | SEC | ST-075a, PE-5b, SEC-5, P16 before any tester footage |
| Multi-close repeat | EM, PE, QA | `retro_ready.py` precondition; ADR if a second close happens |
| Holiday PO availability (RM-12) | PM, EM | escalations sent by 2026-11-05 with defaults and deadlines |
| Unverified domain rules read as fact in rules | COACH | no rule in this sprint rests on rules-verified §5 |

## 11. Dependencies

Human: §0.4. Internal: §15 `depends_on`. External tools: Locust 2.46.7, promtool (prom/prometheus image), Playwright Chromium (preinstalled; never `playwright install`).

## 12. Demo script (sprint review, 2026-12-22)

1. `make up FLAGS=on PROFILES=obs` on a fresh worktree; `make demo` twice (DEMO-1.1).
2. Walk the R1 journey: sign in → upload → Quick Tag → score sheet ("unofficial scoring") → stats → plan → "Not for me" on a single-weakness plan (FR-124.R1).
3. Fix a call in ≤ 2 taps (NFR-036.4) on the Android phone emulation.
4. Show `perf-r1` verdict per endpoint (G05-01).
5. Inject a 5xx burst; show the fast-burn alert firing in Prometheus (G05-02).
6. Run the restore drill; show RPO, RTO and the equal corrections fingerprint (G05-03).
7. Show the browser matrix report and the ASVS status table (G05-04, G05-07).
8. Show a tier 0 docs PR merging with one reviewer + doc-check, and a tier 1 PR refused without QA (G05-08).
9. Show flow metrics and cost per PR (G05-11); the PO list with what is waiting on whom (§0.4).
10. `make down`.

## 13. Retrospective

`docs/retros/2026-12-22-sprint-05.md`, written once by RETRO-05 after VERIFY-05 (F1). Start / Stop / Continue plus the all-role reflection (every role, owned and dated actions); reviews retro 4 F1-F4 and E2-E5 first; reviews the WIP limits and the 12-role cost question with G05-11 data (ADR 0056).

## 14. Traceability

Atomic item → story → ticket → tests: `05/requirements-breakdown.md` §1-§4 and §3.7 above; scorecard rows in `05/goal-scorecard.md` §2. BA-5 adds the rows to `docs/requirements/traceability-matrix.md`.

## 15. Ticket map (ADR 0047 rule 4; branches `s05/<id-lowercase>` from current `main`)

| Ticket | Branch | Owner | Tier | Depends on | Files (disjoint per lane) | ci_fix |
|---|---|---|---|---|---|---|
| CI-NOTICE-CANCELLED | `s05/ci-notice-cancelled` | sre | 1 | — | `scripts/ci/scheduled_red_notice.py`, ci.yml flaky job, `infra/tests/` | yes |
| CI-DOC-CHECK | `s05/ci-doc-check` | sre | 1 | CI-NOTICE-CANCELLED | `scripts/ci/check_docs.py`, ci.yml, `infra/tests/` | no |
| CI-TIERS-a | `s05/ci-tiers-a` | sre | 2 | CI-NOTICE-CANCELLED | `scripts/ci/review_tiers.py`, `infra/tests/` | no |
| CI-TIERS-b | `s05/ci-tiers-b` | sre | 2 | CI-TIERS-a, CI-DOC-CHECK | `scripts/ci/merge_ready.py`, `infra/tests/`, `docs/ops/branch-protection.md` | no |
| CI-RECON-ON-PR | `s05/ci-recon-on-pr` | sre | 1 | CI-NOTICE-CANCELLED | `scripts/measure/reconcile_due.py`, `ci.yml` (`pr-policy` job) | no |
| QA-TCR-04 | `s05/qa-tcr-04` | qa | 0 | — | `docs/sprints/04/test-change-requests.md` | no |
| QA-DOR-CHECK | `s05/qa-dor-check` | qa | 1 | CI-DOC-CHECK | `scripts/ci/check_atomic_breakdown.py` | no |
| QA-FLOW-METRICS | `s05/qa-flow-metrics` | qa | 1 | — | `scripts/measure/flow_metrics.py` | no |
| PM-5 | `s05/pm-5` | pm | 0 | — | `docs/sprints/roadmap.md` | no |
| BA-5 | `s05/ba-5` | ba | 0 | — | `docs/requirements/`, `05/requirements-breakdown.md` | no |
| PE-5a | `s05/pe-5a` | pe | 0 | — | `docs/decisions/0057-*` | no |
| PE-5b | `s05/pe-5b` | pe | 0 | — | `docs/decisions/0058-*` | no |
| SEC-5 | `s05/sec-5` | sec | 1 | — | `docs/security/threat-notes-sprint-05.md`, `docs/security/tools/` | no |
| PD-5 | `s05/pd-5` | pd | 0 | — | `docs/design/flows-sprint-05.md` | no |
| PD-DR04 | `s05/pd-dr04` | pd | 0 | — | `docs/design/flows-sprint-04.md` | no |
| COACH-5 | `s05/coach-5` | coach | 0 | — | `docs/domain/` | no |
| EM-ESC-05 | `s05/em-esc-05` | em | 0 | PM-5 | `docs/sprints/05/po-escalations.md` | no |
| QA-VERIFY04R5-01 | `s05/qa-verify04r5-01` | be | 2 | — | `scripts/demo/`, `infra/tests/test_seed_demo_plan.py` | no |
| ST-074 | `s05/st-074` | be | 1 | BA-5 | `backend/tests/perf/`, `scripts/ci/perf_verdict.py` | no |
| ST-075a | `s05/st-075a` | be | 2 | PE-5a, SEC-5 | `backend/src/racket/platform/telemetry*` | no |
| ST-075b | `s05/st-075b` | sre | 1 | PE-5a | `infra/compose.yaml` (obs), `infra/observability/collector/` | no |
| ST-075c | `s05/st-075c` | sre | 2 | ST-075a, ST-075b, ST-075d | `infra/observability/alerts/slo*`, `infra/compose.fault-drill.yaml`, `scripts/ops/inject_5xx.py`, `docs/ops/slo.md` | no |
| ST-075d | `s05/st-075d` | be | 2 | PE-5a, SEC-5 | `backend/src/racket/platform/fault.py`, `backend/src/racket/platform/app.py` (middleware line), `backend/tests/` | no |
| ST-076a | `s05/st-076a` | sre | 2 | PE-5b, SEC-5 | `infra/compose.yaml` (ops), `infra/docker/backup/` | no |
| ST-076b | `s05/st-076b` | be | 2 | PE-5b | `backend/src/racket/platform/integrity.py` | no |
| ST-076c | `s05/st-076c` | sre | 2 | ST-076a, ST-076b | `scripts/ops/restore_drill.py`, `docs/ops/restore-runbook.md` | no |
| ST-077 | `s05/st-077` | be | 2 | SEC-5 | `docs/security/data-classification.md`, `backend/tests/integration/` | no |
| ST-078a | `s05/st-078a` | sec | 1 | SEC-5 | `docs/security/tools/asvs_status.py`, checklist V1-V5 | no |
| ST-078b | `s05/st-078b` | sec | 0 | ST-078a | checklist V6-V10 | no |
| ST-078c | `s05/st-078c` | sec | 0 | ST-078b | checklist V11-V17, ADR draft | no |
| ST-078d | `s05/st-078d` | be | 2 | SEC-5 | `backend/src/racket/platform/http*`, `backend/tests/` | no |
| ST-078e | `s05/st-078e` | fe | 2 | SEC-5 | `web/src/`, `web/tests/`, `web/e2e/sprint-05/logout*` | no |
| ST-079 | `s05/st-079` | fe | 1 | BA-5 | `web/e2e/helpers/projects.ts`, `scripts/measure/browser_matrix.py` | no |
| ST-080 | `s05/st-080` | qa | 1 | BA-5, COACH-5 | `web/e2e/sprint-05/fix-call-taps.spec.ts` | no |
| ST-081a | `s05/st-081a` | be | 1 | COACH-5 | `backend/src/racket/coaching/coverage*`, `tests/features/` | no |
| ST-081b | `s05/st-081b` | coach | 0 | ST-081a | `content/drills/` | no |
| ST-082 | `s05/st-082` | sre | 1 | PE-5b, PM-5, COACH-5 | `docs/releases/`, `scripts/ops/rollback_drill.py` | no |
| ST-083 | `s05/st-083` | pd | 0 | PD-5, COACH-5, SEC-5 | `docs/design/usability-test-kit-r1.md` | no |
| ST-084a | `s05/st-084a` | ml | 0 | — | `docs/decisions/0060-*` | no |
| ST-084b | `s05/st-084b` | ml | 1 | ST-084a | `backend/src/racket/dataset/rally_f1.py` | no |
| ST-085 | `s05/st-085` | fe | 1 | — | `web/src/` SW and dialogs, `web/tests/` | no |
| QA-PIN-05 | `s05/qa-pin-05` | qa | 1 | ST-074, ST-075c, ST-076c | `infra/tests/` pins | no |
| EM-CLOSE-CHECKS | `s05/em-close-checks` | em | 1 | QA-FLOW-METRICS | `docs/sprints/05/close-checks/` | no |
| VERIFY-05 | `s05/verify-05-r1` | qa | 0 | all build tickets | `docs/sprints/05/decisions/VERIFY-05.md`, scorecard | no |
| SMOKE-05 | `s05/smoke-05` | sre | 0 | VERIFY-05 | `docs/sprints/05/smoke.md` | no |
| RETRO-05 | `s05/retro-05` | em | 0 | SMOKE-05, EM-CLOSE-CHECKS | status files, report, retro | no |

ADR numbers 0057-0060 are reserved in this order; a ticket that merges out of order takes the next free number and notes it in its decisions file.
