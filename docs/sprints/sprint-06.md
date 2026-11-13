# Sprint 6: first video-analysis slice, from cited reference patterns to the exercises that close a player's measured gaps

- **Dates (calendar of record):** Mon 2027-01-04 → Fri 2027-01-15 (10 working days; roadmap §2). **Re-baselined working dates:** the sprint runs as a compressed agent session from **2026-11-13**, like Sprints 1-5; the in-session due dates below (2026-11-14 … 2026-11-26) are the ones the EM status step checks. The 2027-01-15 review and retro keep the PO cadence.
- **Planning:** 2026-11-13 by the engineering-manager with the product-manager, principal-engineer, business-analyst and senior-qa-engineer (ticket PLAN-06, branch `s06/plan` from `origin/main` at `e7ed7d9d`). Kickoff input from all 12 roles: [`06/kickoff.md`](06/kickoff.md).
- **Why this sprint is video analysis and not the Go port:** the PO's instruction of 2026-11-12 orders the work as local stack, then CI/CD, then video analysis (quoted verbatim in `docs/requirements/po-input-2026-10-05.md`, addendum "Video analysis (PO 2026-11-12)"). **Moving the Go port to Sprint 7 is an orchestrator note confirmed at the kickoff by the team, not a PO decision.** It conflicts with the standing PO decision "Port the product to Go (PO decision 2026-10-06)", whose timing reads "before any computer-vision work". The plan therefore (a) asks the PO to confirm in EM-ESC-06 (P21) and (b) keeps the slice tag-based and CV-optional, so most of it survives either answer (§10, PE kickoff risk 1).
- **Retro file:** `docs/retros/2027-01-15-sprint-06.md` (planned), Start / Stop / Continue plus the all-role reflection (PO 2026-10-31). Focus: **did the Sprint 5 drain and the WIP gate hold, did every reference value keep its provenance, and what did each PR cost (ADR 0056 decision 1)?**
- **Delivery:** every ticket is its own branch `s06/<ticket-id-lowercase>` and its own **draft** PR into `main` (ADR 0039, ADR 0052), marked ready only when local checks pass. No sprint branch. Merges only through `merge_ready.py`, one at a time, by the gated merge step (ADR 0050).
- **Goal scorecard:** [`06/goal-scorecard.md`](06/goal-scorecard.md), 11 metrics G06-01..G06-11, each measured live on the local stack; human-only items in its §5.
- **Atomic requirements:** [`06/requirements-breakdown.md`](06/requirements-breakdown.md) (atomic item → story → ticket → test).
- **Shared sprint files:** `docs/sprints/06/review-rounds.md` (planned) (findings ledger), `test-change-requests.md`, `blockers.md`, `decision-log.md`, `status.json`, `progress.md`. **Ticket PRs never edit** `status.json`, `progress.md`, `decision-log.md` or `blockers.md`; each ticket writes `docs/sprints/06/decisions/<TICKET-ID>.md`. Only RETRO-06 consolidates. Ticket PRs may add ledger rows to `review-rounds.md` and their own §6 row to the scorecard.
- **Related ADRs:** 0003 (rallies-lost ranking), 0005 (uncertainty, non-overlap), 0006 (retention windows), 0010 (capacity), 0014 (fail closed), 0015 (CV licence posture, reviews still pending), 0044 (content status ladder), 0047 (gates first), 0050, 0052, 0054, 0055, **0056**, 0058, 0059 (R-05, R-11 "G-S6 (fix)"), 0060 (model regression tolerances). New this sprint: **0061** (PE-6a, reference patterns and player-vs-reference comparison) and **0062** (PE-6b, footage provenance, pose-data classification, ADR 0015 review closure). A ticket that merges out of order takes the next free number and notes it.

## 0. Planning record (2026-11-13)

### 0.1 Preconditions

| Precondition | Status at planning | Consequence |
|---|---|---|
| **CI on `main` green (CI FIRST)** | **Push: green.** `gh api 'repos/nhuthuynh/racket-analytics/actions/runs?branch=main&per_page=60'`: 43334586810 at `e7ed7d9d` → success (2026-11-13 00:08Z); 43281846173 at `1c3b648c` → failure (2026-11-12 18:37Z), fixed by the next merge (43297649333 `b4161068` success). **Scheduled:** `…/actions/runs?event=schedule`: CI 43206773425 at `2f947974` → success (2026-11-12); CI 43007950254 at `b7bf0b7f` → **failure** (2026-11-11, Locust 50 RPS verdict: stats p95 310 ms, evidence p99 1200 ms); Nightly quality 43198871753 → success | `main` is green now, so no new `ci_fix` pre-empts planning. The 2026-11-11 red is the cause of **CI-NIGHTLY-PERF (#232, open)**; the red-run notice only ran as `skipped` on push events, so **CI-SCHEDULED-RED** (`ci_fix`) is wave 0 |
| **Sprint 5 not closed** | `git show origin/main:docs/sprints/05/sprint-report.md` → "does not exist"; no VERIFY-05, no RETRO-05, no `docs/sprints/05/status.json` (planned). 13 PRs open: `gh api 'repos/nhuthuynh/racket-analytics/pulls?state=open'` → #201, #218, #220, #224, #226, #230, #231, #232, #234 (draft), #235, #236, #238, #239 | **Entry condition E1** (§3.6): the Sprint 5 drain wave (these PRs, then VERIFY-05, SMOKE-05, RETRO-05) runs first. Sprint 6 gate tickets (docs) may run in parallel inside the WIP limits; **no Sprint 6 build ticket starts until E1 holds** |
| WIP | 12 PRs ready for review against "in review 3" (working-agreement §3) | breach logged (`decisions/PLAN-06.md`); **QA-WIP-GATE** makes the limit a refusal, not a record |
| Sprint 5 ledger | `python3 scripts/measure/open_defects.py docs/sprints/05/review-rounds.md` → `open 5`, rc 1 (blockers SEC-S5-TM-01, SEC-S5-TM-02; majors COACH-S5-01, COACH-S5-05; 1 more) | reconciled inside the Sprint 5 drain before VERIFY-05 (QA, SEC kickoff); not a Sprint 6 ticket |
| Footage | `git ls-tree -r origin/main` has no `.mp4/.mov/.webm` with people; only synthetic golden JSON and phone fixtures; P11/OQ-06 open since S3 | no CV story is Ready (roadmap §7.1, NFR-006); the slice runs on Quick Tag and Full Tag data |
| Disk | `df -h /` → 14 GB free (below the 16 GB build floor); 25 worktrees under `/home/user/wt` | **OPS-DISK-06** in wave 0; every build runs `bash scripts/disk-precheck.sh` first; each agent removes its own worktree at done |
| ADR 0056 required tickets | merge_ready tiers (CI-TIERS-a/b) and doc-check (CI-DOC-CHECK) exist since Sprint 5 | extended for the new paths: **CI-TIERS-06** (a) and **CI-DOC-CHECK-06** (b) |

### 0.2 Product-owner decisions applied (quoted in `docs/requirements/po-input-2026-10-05.md`)

- **2026-11-12, verbatim:** "resume sprint 5, please try to finish the local docker running and start local prototype first, then fix the CI/CD then adding analyse the videos from training, pro matches, ... getting best practices and patterns, then work out any weaknesses and provide or recommend the exercises to fix those weaknesses". Status on 2026-11-13: the local stack and prototype run (`make up` + `make demo` verified 2026-11-12); the CI/CD fixes are the Sprint 5 tickets CI-FFMPEG (#230) and CI-NIGHTLY-PERF (#232), still open, so they are in wave 0; video analysis is this sprint's goal.
- **"start Sprint 5 once the PRs merge"** (2026-11-03) and "resume sprint 5" (2026-11-12): the Sprint 5 close comes first (E1).
- **Way of working (2026-10-31)** and **audit decisions (2026-11-03, ADR 0056):** kickoff with feedback (`06/kickoff.md`); work split by role fit (§4); plan and brainstorm skills (§0.6); FR/NFR to atomic level (`06/requirements-breakdown.md`); goal with stories and tickets, complex stories split (§3); one PR per ticket with unit + integration tests, green CI, principal-engineer review and a QA test before merge (§8, §9); all-role reflection (RETRO-06); 12 roles with cost per PR (§9, G06-10); tiered review (§8); sprints with WIP limits and flow metrics (§2.1, G06-10).
- **Footage rules (brief, binding):** pro-match video only where we hold the rights; no scraping of broadcast or YouTube content without a licence; training video only with the players' consent; pose or body tracking is personal data (tier 2 with the security-privacy-engineer); NFR-062 MIT/Apache only, no AGPL in the shipped graph.
- **Not a PO decision (orchestrator note):** "Sprint 6 becomes the first video-analysis sprint and the Go port moves to Sprint 7". Confirmed by the team at kickoff (all 12 roles; the PE and SEC confirm only with the conditions in `06/kickoff.md` §2), recorded in po-input under its own "not a PO decision" heading, and asked as **P21** in EM-ESC-06.

### 0.3 Sprint 5 carry-over, open findings and retro actions applied

| Item | Source | Where |
|---|---|---|
| 13 open Sprint 5 PRs incl. CI-FFMPEG #230, CI-NIGHTLY-PERF #232, CI-DOMAIN-BUDGET #235/#236, CI-TIERS-a-R3 #231 | GitHub REST, 2026-11-13 | wave 0 drain (Sprint 5 tickets, not re-ticketed) |
| VERIFY-05, SMOKE-05, single RETRO-05 (`retro_ready.py`, EM-CLOSE-CHECKS #240) | sprint-05 §3.6 item 5; retro 4 F1 | wave 0 drain, before any Sprint 6 build ticket |
| Approved-but-conflicted PRs (#218 dirty since 2026-11-05; #226 PR-policy red) | FE kickoff | rule §3.6 item 3: the author merges `origin/main` the same day, reviewers re-verdict |
| Ledger open 5 (SEC-S5-TM-01/02 blockers, COACH-S5-01/05 majors) | QA, SEC kickoff | reconciled in the drain (closing rows with evidence, or carried with an owner) |
| Scheduled CI red not noticed on push events | SRE kickoff; run 43007950254 | CI-SCHEDULED-RED |
| Disk 14 GB < 16 GB floor; 25 stale worktrees (retro 4 M9) | EM, SRE kickoff | OPS-DISK-06 |
| WIP 12 in review vs limit 3 | EM kickoff | QA-WIP-GATE |
| ADR 0059 "G-S6 (fix)": R-05 magic-link TTL, R-11 sha1 in tus checksums | SEC kickoff | SEC-R05, SEC-R11 (P2) |
| ADR 0015 PE and SEC reviews pending since 2026-10-03 | PE, ML kickoff | PE-6b |
| DR-04 hold-or-waiver, PD-DR04-01..03 open | PD kickoff | routed to EM-ESC-06 (PO question); PD-5 #201 in the drain |
| Cost tables: 9 of 39 merged Sprint 5 tickets (`flow_metrics.py`, 2026-11-13) | QA, SRE kickoff | §9 DoD row; **PRC-11.3** pr-policy check in CI-DOC-CHECK-06 |
| Retro 4 M2/M10/M12 (methods never dry-run) | all roles | scorecard §6 planning dry-runs; every method's author row before VERIFY-06 |
| Retro 4 M3 (author-found gap) | PM, BA, PE, COACH | FR-173.R1/R3 coverage axis; PRC-4.2 grep stays in pr-policy |

### 0.4 Goal items that depend on a human input (ADR 0037 rule 3; PO P12 option b)

Not goal metrics. Each is a row in `goal-scorecard.md` §5 ("not met: waiting on P-n") from day 1. Human-gated work is **not a ticket**; the table says what the team prepares.

| Item | Waits on | Need-by (asked in EM-ESC-06) | What the team prepares |
|---|---|---|---|
| Confirm Sprint 6 = video analysis and the Go port in Sprint 7 (conflicts with the PO decision of 2026-10-06) | **P21** (new) | 2026-11-17; default: proceed with the tag-based slice, Go port S7 | PE options with cost (port first / slice first / strangler); a slice with no new framework and pure domain functions |
| Licensed pro-match footage and consented training footage (OQ-06) | **P11** | before S8 planning (CV spikes) | FR-174 provenance gate (ST-175a), licence gate (ST-175b), eval harness (ST-176a), spike plans (ST-176b), footage spec and rights/consent checklist (COACH-6a, SEC-6) |
| Human coach verification of reference patterns and drills (`verified`) | **P15** | 2026-11-24; default: everything stays `coach-reviewed` with the UI notice | COACH-6a/6c entries with citations; the copy register |
| Legal review covering training-video consent, pose data and statistics derived from licensed footage (NFR-070, US + AU) | **P16** | before any real-user exposure | SEC-6 question list; flags default-off |
| May the reference library cite published secondary statistics? | **P22** (new) | 2026-11-17; default: yes, only when the citation resolves, labelled "published source" | `docs/domain/sources.md` (planned) register with resolve checks |
| Rulebook (OQ-01) | **P7** | re-asked (2026-11-10 need-by passed, no answer); default "unofficial scoring" | COACH-6a maps patterns that depend on rules to rule ids |
| Usability of the weakness view with players | **P9** | with the R1 session | usability tasks added to the ST-083 kit by PD-6 |
| Residual-risk ADR 0059 acceptance | **P19** | re-asked (2026-11-12 passed); until answered no deployment beyond localhost | SEC-6 re-ask text |
| GPU spend for CV (OQ-13) | **P8** | before S8 | CPU-only spike plans |
| DR-04 hold or waiver | **D1** (Sprint 5 escalation) | 2026-11-17 | PD-DR04 record |

### 0.5 Kickoff

All 12 roles gave keep / change / lessons / risks / work-I-fit / breakdown advice. Every "change" item has a decision in [`06/kickoff.md`](06/kickoff.md) §2 (69 items from 12 roles: 65 accepted as a ticket or a rule, 5 of them also carrying a PO question routed through EM-ESC-06; 3 deferred with an owner and a date; 1 rejected for this sprint with a reason).

### 0.6 Planning method and skills used (PO 2026-10-31)

| Step | Skill / input | Output summary |
|---|---|---|
| 1. Explore | `product-management:brainstorm` (installed skill) | Framed the problem as "the PO wants video analysis, but nothing visual is measured and no footage with rights exists". Options: **(A)** a tag-first vertical slice (coach-authored, cited reference set → pattern measures from Quick Tag and Full Tag → gap ranking with n and intervals → drills with a cited Why) plus footage-ready preparation (provenance gate, licence gate, eval harness, spike plans); **(B)** CV first (pose or calibration spike), blocked by P11 and roadmap §7.1; **(C)** a pro-footage labelling pipeline first, blocked by P11 rights; **(D)** Go port first, per the 2026-10-06 decision, which contradicts the order of the 2026-11-12 instruction. **Chosen: A**, because it is the only option that ends in a demo on `make up` + `make demo` without breaking §7.1, and it survives either answer to P21. **Riskiest assumption:** a coach-authored, cited reference (not measured from pro matches) is honest enough to rank a player against. Mitigation: provenance on every value, the status ladder, the "coach judgment, not measured from pro matches" label and the non-overlap rule (FR-170.R5, FR-172.R1). **Parked:** player-facing Full Tag (needs a new FR, A3), n-gram patterns (FR-108), CV-derived kitchen arrival and partner spacing, LLM-written Why, competitor positioning. |
| 2. Scope | `product-management:sprint-planning` (installed skill) | One-sentence goal (§1); capacity at load factor 0.85 over 10 days with 25 % reserved for the Sprint 5 drain (§2); P0 = drain, CI, gates, the reference → measure → gap → exercise chain and the demo; P1 = reference browser UI, footage and licence gates, eval harness; P2 = AN-08 return depth, SEC-R05, SEC-R11 (first to slip). Process share 22 % of tickets (§2). |
| 3. Atomic breakdown | business-analyst kickoff advice applied by the EM; BA-6 re-checks | `06/requirements-breakdown.md`: 25 FR rules (FR-170..FR-174), 23 NFR items, 4 demo items, 8 process items, 3 spike items, human items marked; `check_atomic_breakdown.py` → "0 problem(s)" |
| 4. Stories → tickets | EM with the principal-engineer's and backend's slicing advice (one rule per ticket, ≈ 100 production lines) | 9 stories, 45 tickets (§3), each ≤ 400 production lines |
| 5. Owners by role fit | kickoff "work_i_fit" answers | §3 owner column; §4 per role |

## 1. Sprint goal

**On the local stack (`make up` + `make demo`) a player sees a versioned, cited reference pattern set, their own measured gaps against it ranked with n and uncertainty, and drills chosen to close the top gaps, each drill citing the metric and the reference pattern; and every value says where it came from.**

Scorecard bullets (each a G06 row): reference-set integrity (G06-01); pattern computation correctness (G06-02); honest gap ranking (G06-03); cited exercise recommendations with coverage (G06-04); the demo slice end to end (G06-05); weakness-view latency and read cost (G06-06); accessibility of the new screens (G06-07); provenance, privacy and licence gates (G06-08); test strength and security fixes (G06-09); flow and cost per PR (G06-10); CI, merge discipline, Sprint 5 closed, one close (G06-11).

**What the sprint does not claim:** it does not analyse video pixels. "Analyse the videos" in this sprint means analysing **tagged** video (Quick Tag and Full Tag events of a filmed match). Reference values are coach-authored and cited, **not measured from pro matches**, until P11 footage with rights exists. The UI says so on every reference value (FR-170.R5).

**Product Goal (PM-6 rewrites roadmap §"Product Goal"; draft, judgment):** a player sees how their own play differs from a cited reference pattern set and gets drills that close the largest measured gap, each gap with n and uncertainty.

**Out of scope:** automatic CV in the user path; scraped pro footage; pose tracking on real people (spike plans only); LLM-written Why; n-gram patterns (FR-108); opponent scouting; a player-facing Full Tag (A3); the Go port (S7, pending P21); any real-user exposure (P16).

## 2. Capacity (ADR 0010)

- **Load factor 0.85** (S5 kept it; the S5 completion ratio is not measured yet because S5 is open). Full sprint: 10 working days → 8 units per stream × 0.85 = **6.8 units per stream**, minus **25 % reserved for the Sprint 5 drain and review loops** → **5.1 units per stream** for Sprint 6 tickets. Sizes: XS 0.5 · S 1 (≈ 100-150 production lines) · M 2 (≤ 400). Nothing larger than M.
- **Lanes:** BE 2 streams, SRE 1 stream (its second stream is the drain: #230, #232, #235, ST-076c, SMOKE-05), QA 2 streams (one is VERIFY-05 and the PR test gate), FE 1, ML 1. Docs and gate roles carry dated tickets without units.

| Lane | Tickets (units) | Planned | Capacity |
|---|---|---|---|
| SRE | CI-SCHEDULED-RED 0.5, OPS-DISK-06 0.5, CI-TIERS-06 1, CI-DOC-CHECK-06 1, ST-175b 1, SMOKE-06 0.5 | 4.5 | 5.1 |
| BE | ST-170a 1, ST-170b 1, ST-171a 1, ST-171e 1, ST-172a 1, ST-172b 1, ST-173a 1, ST-173b 0.5, ST-174a 1, ST-175a 1, SEC-R05 0.5, SEC-R11 0.5 | 10.5 | 10.2 (SEC-R05/R11 slip first) |
| ML | ST-171b 1, ST-171c 1, ST-171d 1, ST-176a 1 | 4 | 5.1 |
| FE | ST-170c 1, ST-172c 1, ST-173d 1 | 3 | 5.1 (plus #218, #226 in the drain) |
| QA | QA-WIP-GATE 0.5, QA-REF-GOLD 1, ST-174b 1, QA-PIN-06 1, VERIFY-06 1 | 4.5 | 5.1 (second stream: VERIFY-05 and the test gate) |
| Docs/gates | PM-6, BA-6, PE-6a, PE-6b, SEC-6, PD-6, DR-06, COACH-6a, COACH-6b, COACH-6c, ST-173c, ML-6, ST-176b, EM-ESC-06, RETRO-06 | dated | — |
| **Total** | 45 tickets (PLAN-06 is this PR) | **26.5 units** | 30.6 |

**Process share:** 10 of 45 tickets (CI-SCHEDULED-RED, OPS-DISK-06, CI-TIERS-06, CI-DOC-CHECK-06, QA-WIP-GATE, EM-ESC-06, QA-PIN-06, VERIFY-06, SMOKE-06, RETRO-06) = 22 %, 6.5 of 26.5 units = 25 %, under Sprint 5's 29 % and close to the EM's 20 % cap (the two ADR 0056 required tickets and the WIP gate are the excess). The video-analysis slice and its gates are 33 of 45 tickets (73 %), over the PM's 60 % floor.

### 2.1 WIP limits and flow (working-agreement §3; ADR 0056 decision 3)

| Stage | Limit this sprint | Rule |
|---|---|---|
| In progress | **4** (sprint brief) | no new ticket starts while 4 are in progress; **QA-WIP-GATE**'s `wip_gate.py` refuses the start once it merges |
| In review | 3 | full → the next agent turn reviews |
| Awaiting QA | 2 | full → QA tests before anyone starts |
| Awaiting merge | 1 | merges run one at a time (ADR 0050) |

The drain starts **in breach** (12 in review); while it lasts, every agent turn goes to review, QA or fixes, and the breach reason is logged in each EM status record. The EM status step (working-agreement §7 3c) records the four counts, the age of every open ticket, `open_defects.py`, the `merged_verdict.py` audit, the decisions-file grep for "can only|not covered|known gap|no reference|not measurable" and the worktree list (OPS-DISK-06). Flow metrics (cycle time, throughput, work item age, breaches) and cost per PR (agent wall time per ticket) are reported by RETRO-06 from `flow_metrics.py` (G06-10), never as targets [ASB/AGL-02].

## 3. Committed backlog

Ticket fields: id, title, story, owner (role fit), tier (ADR 0056: 0 docs/process, 1 ordinary code, 2 security / personal data / schema / API contract), specialists (tier 2, working-agreement §6), depends_on, size, atomic items, priority. Full scope per ticket in §3.7. Every code ticket: Gherkin scenario + integration test + unit tests first, seen failing, red output recorded in its decisions file (`Red:` line); principal-engineer review; senior-qa-engineer test of the PR head.

### 3.1 Wave 0: Sprint 5 drain and CI first

Sprint 5 PRs merge first in this order (CI FIRST): #230 CI-FFMPEG, #232 CI-NIGHTLY-PERF, #235 + #236 CI-DOMAIN-BUDGET, #231 CI-TIERS-a-R3, then #239, #238, #218, #226, #224, #220, #201, #234; then VERIFY-05, SMOKE-05, RETRO-05. These are Sprint 5 tickets and keep their Sprint 5 ids and owners.

| ID | Title | Owner | Tier | Depends on | Size | Items | ci_fix |
|---|---|---|---|---|---|---|---|
| CI-SCHEDULED-RED | Scheduled CI and Nightly reds on `main` reach the status record and block `merge_ready.py` | sre-devops-engineer | 1 | — | XS | PRC-9.1 | **yes** |
| OPS-DISK-06 | Disk precheck before every Compose build target; worktree report; prune runbook for footage and weights | sre-devops-engineer | 1 | — | XS | PRC-13.1 | no |

### 3.2 Wave 1: gate and process tickets (ADR 0047 rule 2: before any build ticket that depends on them)

| ID | Title | Owner | Tier | Specialists | Depends on | Size | Items |
|---|---|---|---|---|---|---|---|
| EM-ESC-06 | PO escalation: P21 (S6/S7 order), P22 (secondary statistics), the "..." question, P11/P15/P16/P7/P19 re-asks with dated defaults, D1, Full Tag for players (A3) | engineering-manager | 0 | — | — | docs | A-Q1, A-Q2, A3, A5 |
| PM-6 | Product Goal re-scope; pattern priority waves A/B/C; out-of-scope list; product metrics the slice can fail | product-manager | 0 | — | — | docs | — |
| BA-6 | Register rows FR-170..FR-174 with verbatim source; traceability rows; glossary terms in ddd-guidelines; DoR verdicts with PR numbers | business-analyst | 0 | — | — | docs | all FR-17x |
| PE-6a | ADR 0061: reference patterns and player-vs-reference comparison (context placement, PatternDefinition, ReferenceSet, PlayerPatternMeasure, gap rule, relation to ADR 0003, drill linkage, context map and canvases; one owner for references: sport-plugin content that Coaching reads through the ACL, not a Coaching aggregate (PE-PLAN06-05); separate keys for the measure snapshot (subject, pattern id, match version, rules_version, definition version) and the gap result (measure key + reference_version) (PE-PLAN06-04)) | principal-engineer | 0 | — | — | docs | A1, A4 |
| PE-6b | ADR 0062: footage provenance (rights basis, permitted uses, fail closed), pose-data classification and retention; closes the ADR 0015 PE and SEC reviews | principal-engineer | 0 | — | — | docs | FR-174, NFR-062, NFR-063.4 |
| SEC-6 | Threat notes Sprint 6: T6-FT, T6-PO, T6-PL, T6-WK, T6-MD, T6-LC; DC-4 and DC-1 decisions; P16 question list; P19 re-ask text | security-privacy-engineer | 0 | — | — | docs | NFR-050.10, NFR-069.2 |
| COACH-6a | Pattern catalogue v0.1 (`docs/domain/pattern-catalogue.md` (planned)) and sources register (`docs/domain/sources.md`): operational definitions, numerator, denominator, exclusions, min_n, interval and interval_method, better_direction (`higher` / `lower` / `inside_band`), level bands, data source, `@needs-verification`; for AN-13 either a justification of the error-ended sample or a switch to a censored estimate, since won dink rallies are right-censored (PE-PLAN06-03) | pickleball-domain-coach | 0 | — | — | docs | FR-171.R2-R7, A2, A6 |
| COACH-6b | Gold fixture GS-PAT-1 (hand-counted, team-made Full Tag) and `docs/domain/tools/pattern_example.py --check` | pickleball-domain-coach | 1 | — | COACH-6a | S | FR-171.R2-R4 |
| PD-6 | `docs/design/flows-sprint-06.md` (planned): families V (reference browser), W (weakness view), E (exercise Why), C (consent and provenance); state tables incl. "not measured", "not enough data", "no clear gap", "no reference yet"; provenance component; HAX and WCAG 2.2 AA rows; copy register with a source column | principal-designer | 0 | — | COACH-6a | docs | FR-170.R5, FR-172.R5, NFR-027.10-.14 |
| DR-06 | Design review DR-06: one dated decider step per role (coach, ML, SEC, FE, BA, PM), each cell carried by that decider's review on the PD-6 PR; `check_flows.py --decider` rc 0 | principal-designer | 0 | — | PD-6 | docs | — |
| ML-6 | Pattern-source matrix (`docs/data/pattern-sources.md` (planned)) with the coach: which patterns are QT, FT or CV, and the §7.1 evidence each CV one needs | senior-ml-cv-engineer | 0 | — | COACH-6a | docs | SPK-1.1 |
| CI-TIERS-06 | ADR 0056 required ticket (a), extended: `merge_ready.py` / `review_tiers.py` learn the Sprint 6 paths (footage, provenance, pose, consent, pattern snapshot → tier 2; `content/references/**` → tier 1 with the coach flag); QA APPROVE on tier 1-2 kept | sre-devops-engineer | 2 | security-privacy-engineer | — (after #231 merges in wave 0) | S | PRC-10.1, PRC-10.2 |
| CI-DOC-CHECK-06 | ADR 0056 required ticket (b), extended: reference citation ids resolve to `docs/domain/sources.md` (planned) rows; `check_threat_notes.py` on the newest threat notes; cost table required in ticket decisions files | sre-devops-engineer | 1 | — | COACH-6a | S | PRC-11.1-11.3 |
| QA-WIP-GATE | `scripts/measure/wip_gate.py` (planned): refuses a ticket start at a full stage, from REST counts | senior-qa-engineer | 1 | — | — | XS | PRC-12.1 |

### 3.3 Wave 2: build (each starts only when E1 holds and its gates merged; §3.8)

| ID | Title | Story | Owner | Tier | Specialists | Depends on | Size | Items | Prio |
|---|---|---|---|---|---|---|---|---|---|
| ST-170a | Reference-set schema, loader, lint (`racket-reference-lint`) and lock; fail closed on missing provenance | ST-170 | senior-backend-engineer | 2 | security-privacy-engineer, pickleball-domain-coach | PE-6a, COACH-6a, SEC-6, CI-TIERS-06 | S | FR-170.R1-R3 | P0 |
| COACH-6c | Reference set v1 content: one entry per wave A/B pattern and level band, each cited, `coach-reviewed` | ST-170 | pickleball-domain-coach | 1 | — | ST-170a, CI-DOC-CHECK-06 | S | FR-170.R1 | P0 |
| QA-REF-GOLD | Frozen expected values for reference set v1 × GS-PAT-1 (writer/reviewer split: written before the extractors); integrity test (hash, no edit without ADR) | ST-170 | senior-qa-engineer | 1 | — | ST-170a, COACH-6b | S | FR-171.R2-R4, FR-172.R1 | P0 |
| ST-170b | Reference read API (`GET /reference-sets/current`), coach-reviewed and verified only; BOLA and no-store rows | ST-170 | senior-backend-engineer | 2 | security-privacy-engineer | ST-170a | S | FR-170.R4, NFR-050.10 | P0 |
| ST-170c | Reference browser UI (read-only): definition, version, provenance label, n, interval | ST-170 | senior-frontend-engineer | 1 | — | ST-170b, DR-06 | S | FR-170.R5 | P1 |
| ST-171a | PatternMeasure value object and the Quick Tag adapter over AN-01..AN-07 (value, n, interval, low_sample, unavailable reasons) | ST-171 | senior-backend-engineer | 1 | — | PE-6a, COACH-6a | S | FR-171.R1, R5, R6 | P0 |
| ST-171b | AN-09 third-shot drop vs drive share from Full Tag labels | ST-171 | senior-ml-cv-engineer | 1 | — | ST-171a, COACH-6b | S | FR-171.R2, R3 | P0 |
| ST-171c | AN-13 dink-rally tolerance from Full Tag labels | ST-171 | senior-ml-cv-engineer | 1 | — | ST-171a, COACH-6b | S | FR-171.R4 | P0 |
| ST-171d | AN-08 return depth from labelled bounce `court_xy_m` (stretch) | ST-171 | senior-ml-cv-engineer | 1 | — | ST-171a, COACH-6b | S | FR-171.R7 | P2 |
| ST-171e | Pattern-measure snapshot keyed on (subject, pattern id, match version, rules_version, definition version); gap results keyed on that key + reference_version (ADR 0061); migration; classification rows; deletion cascade | ST-171 | senior-backend-engineer | 2 | security-privacy-engineer | ST-171a, SEC-6, PE-6a | S | NFR-063.3, NFR-066.10, NFR-075.1 | P0 |
| ST-172a | Gap rule in `coaching/weakness`: non-overlap, not enough data, no reference yet, ordering and tie-break, relation to ADR 0003 | ST-172 | senior-backend-engineer | 1 | — | PE-6a, ST-171a, ST-170a | S | FR-172.R1-R4 | P0 |
| ST-172b | Weakness-vs-reference read API (`GET /me/weaknesses`), contract test, BOLA rows, statement-count IT, Locust task | ST-172 | senior-backend-engineer | 2 | security-privacy-engineer | ST-172a, ST-171e, ST-170b | S | FR-172.R6, NFR-010.10-.12, NFR-050.10, NFR-069.2, NFR-075.2 | P0 |
| ST-172c | Weakness view UI: states, gap chart with printed values and a data table, provenance component | ST-172 | senior-frontend-engineer | 1 | — | ST-172b, DR-06 | S | FR-172.R5, NFR-027.11, .12, .14 | P0 |
| ST-173a | Plan hook: gap → drills via `target_metrics`; Why validator (pattern id, value, n, interval, reference id, version, status, label); no_alternative per gap; new eval cases | ST-173 | senior-backend-engineer | 1 | — | ST-172a | S | FR-173.R1, R2, R4 | P0 |
| ST-173b | Coverage check gains the pattern × level × players × equipment axis for the new targets | ST-173 | senior-backend-engineer | 1 | — | COACH-6a | XS | FR-173.R3 | P0 |
| ST-173c | Up to 6 drills targeting AN-09 and AN-13 that close the cells ST-173b reports, `coach-reviewed`, safety-classed | ST-173 | pickleball-domain-coach | 1 | — | ST-173b | S | FR-173.R1, R3 | P0 |
| ST-173d | Plan view: the Why cites the reference (version, status, provenance label); "no exercise yet for this gap" state | ST-173 | senior-frontend-engineer | 1 | — | ST-173a, DR-06 | S | FR-173.R2 | P0 |
| ST-174a | `make demo` seeds reference set v1, two demo players with Quick Tag and Full Tag matches; FEATURE_REFERENCE_PATTERNS wired to Compose and `env.example` (parity test) | ST-174 | senior-backend-engineer | 1 | — | ST-172b, ST-173a, COACH-6c | S | DEMO-6.1 | P0 |
| ST-174b | @critical E2E journey: reference browser → weakness view → exercises; two players differ; planted reference change; flags off; axe and target-size scans | ST-174 | senior-qa-engineer | 1 | — | ST-174a, ST-172c, ST-173d | S | DEMO-6.2-6.4, NFR-027.10, .13 | P0 |
| ST-175a | Footage provenance record and the fail-closed job-creation gate; consent per filmed person; classification rows | ST-175 | senior-backend-engineer | 2 | security-privacy-engineer | PE-6b, SEC-6 | S | FR-174.R1-R3, NFR-063.4 | P1 |
| ST-175b | Licence gate over the worker image SBOM and `models/manifest.json` (weights: licence + SHA-256); no runtime model download | ST-175 | sre-devops-engineer | 2 | security-privacy-engineer | PE-6b | S | NFR-062.1-.3 | P1 |
| ST-176a | Eval harness and `docs/evals/` (planned) report template (ADR 0060 rows); dry-run on phone fixtures | ST-176 | senior-ml-cv-engineer | 1 | — | ML-6 | S | NFR-006.7, SPK-1.2 | P1 |
| ST-176b | CPU-only spike plans: SPIKE-07 calibration and pose feasibility (RTMPose ONNX), cut-offs written before; licence rows per artefact | ST-176 | senior-ml-cv-engineer | 0 | — | ML-6, PE-6b | docs | NFR-006.8, SPK-1.3 | P1 |
| SEC-R05 | `MAGIC_LINK_TTL_SECONDS` = 600 (ADR 0059 R-05) | SEC-R | senior-backend-engineer | 2 | security-privacy-engineer | SEC-6 | XS | NFR-050.11 | P2 |
| SEC-R11 | Drop `sha1` from the tus checksum algorithms (ADR 0059 R-11; contract change) | SEC-R | senior-backend-engineer | 2 | security-privacy-engineer | SEC-6 | XS | NFR-050.12 | P2 |

### 3.4 Wave 3: measurement pinning and close

| ID | Title | Owner | Tier | Depends on | Size |
|---|---|---|---|---|---|
| QA-PIN-06 | Pin every timed or thresholded G06 method to its CI step or command | senior-qa-engineer | 1 | ST-172b, ST-174b | S |
| VERIFY-06 | Live verification of G06-01..G06-11 on a fresh worktree, own Compose projects | senior-qa-engineer | 0 | every wave 2 ticket, QA-PIN-06 | S |
| SMOKE-06 | Close-head smoke, stacks pruned, worktrees removed | sre-devops-engineer | 0 | VERIFY-06 | XS |
| RETRO-06 | One close: sprint report, retro with all-role reflection, cost-per-PR report, status files | engineering-manager | 0 | SMOKE-06 | docs |

### 3.5 Stories

| Story | Goal slice | Tickets |
|---|---|---|
| ST-170 Reference pattern set | a versioned, cited, provenance-labelled reference | ST-170a/b/c, COACH-6c, QA-REF-GOLD |
| ST-171 Player pattern measures | the same patterns measured in the player's tagged matches | ST-171a..e |
| ST-172 Weakness view | gaps ranked honestly, with n and intervals | ST-172a/b/c |
| ST-173 Exercises | drills that close the gaps, with a cited Why | ST-173a..d |
| ST-174 Demo slice | `make up` + `make demo` show it end to end | ST-174a/b |
| ST-175 Footage-ready gates | provenance and licence gates before any footage arrives | ST-175a/b |
| ST-176 CV readiness | eval harness and spike plans, no Ready CV story | ST-176a/b |
| SEC-R | ADR 0059 G-S6 fixes | SEC-R05, SEC-R11 |
| PRC-06 | CI, WIP, disk, tiers, doc-check, pinning, close | CI-SCHEDULED-RED, OPS-DISK-06, CI-TIERS-06, CI-DOC-CHECK-06, QA-WIP-GATE, QA-PIN-06, VERIFY-06, SMOKE-06, RETRO-06 |

### 3.6 Order of work and CI-first rule

1. **Wave 0 (from 2026-11-13; merge-by 2026-11-16):** the Sprint 5 drain in the §3.1 order, CI-SCHEDULED-RED and OPS-DISK-06. If `main` turns red at any point, the next ticket is a `ci_fix` ticket that pre-empts everything (CI FIRST).
2. **Entry condition E1 for every wave 2 ticket:** the 13 Sprint 5 PRs merged or closed with a reason; VERIFY-05 merged; `retro_ready.py` rc 0 and RETRO-05 merged; the latest push and scheduled CI runs on `main` green. Wave 1 docs tickets may run in parallel with the drain, inside the WIP limits.
3. **Approved but conflicted (FE kickoff):** when an approved PR goes `dirty`, its author merges `origin/main` into the branch the same day (no rebase, no force-push) and the reviewers re-verdict the new head. The author owns the PR until `merge_ready.py` exits 0 on its head.
4. **Wave 1 (gates; merge-by 2026-11-17):** EM-ESC-06 sent first (by 2026-11-14); COACH-6a and PE-6a first among the gates (most build tickets wait on them); SEC-6, PE-6b, PD-6 → DR-06 (each decider is its own scheduled step, PD kickoff), ML-6, COACH-6b, PM-6, BA-6; CI-TIERS-06 after #231; CI-DOC-CHECK-06 after COACH-6a; QA-WIP-GATE first in QA.
5. **Wave 2 (build; merge-by 2026-11-24):** a story starts only when BA-6 marks it Ready with gate PR numbers (§3.8). BE runs two streams (ST-170a → ST-170b → ST-172b → ST-174a / ST-171a → ST-171e → ST-172a → ST-173a → ST-173b); ML one (ST-171b → ST-171c → ST-176a → ST-171d); FE one (ST-172c → ST-173d → ST-170c); QA one (QA-REF-GOLD → ST-174b).
6. **Shared files:** `.github/workflows/ci.yml`: CI-SCHEDULED-RED → CI-DOC-CHECK-06 → ST-175b; `scripts/ci/review_tiers.py`: CI-TIERS-06 only; `infra/compose.yaml` and `infra/env.example`: ST-174a only; `scripts/demo/seed_demo.py`: ST-174a only; `content/drills/library.lock`: ST-173c only; `backend/src/racket/coaching/weakness/`: ST-172a, then ST-173a. The later PR merges `origin/main` and re-runs its checks before asking for review.
7. **Wave 3:** QA-PIN-06; then VERIFY-06 (2026-11-25) only when every wave 2 ticket is merged and every scorecard §6 row has rc 0; misses go to `FIX-06-<n>` tickets and a dated re-measure; SMOKE-06; RETRO-06 (2026-11-26) only when `retro_ready.py` exits 0.

### 3.7 Ticket specifications

Each block: story · atomic items · acceptance · tests carried (Gherkin / IT / unit) · QA test plan · bounded context · directories. "Red first" means the listed negative test is committed and seen failing before any implementation. Docs tickets state why TDD does not apply and run the doc checks (paths exist, citations resolve, front matter parses, `check_atomic_breakdown.py`, `check_flows.py --decider`, `check_threat_notes.py`).

#### CI-SCHEDULED-RED (ci_fix)
PRC-06 · PRC-9.1 · **Acceptance:** a scheduled CI or Nightly quality run on `main` with conclusion failure, cancelled or timed_out is reported by `scripts/measure/scheduled_red.py` (planned) with its run id; `merge_ready.py` refuses while the latest scheduled CI run on `main` is red, naming it; a green scheduled run clears it. · **Tests:** `infra/tests/test_scheduled_red.py` (red first: the recorded payload of run 43007950254 → expects a red line, today nothing); `tests/features/scheduled_red.feature`. · **QA:** replay of 43007950254 and 43206773425 payloads; a stubbed open PR refused then allowed. · **Context:** platform/CI. · **Dirs:** `scripts/measure/`, `scripts/ci/merge_ready.py`, `infra/tests/`.

#### OPS-DISK-06
PRC-06 · PRC-13.1 · **Acceptance:** every Makefile target that builds images calls `bash scripts/disk-precheck.sh` first; `scripts/ops/worktree_report.py` (planned) lists `/home/user/wt/*` with branch and PR state; `docs/ops/disk-and-prune.md` gains a footage and weights section (outside the repo and image layers, read-only mounts, size cap). · **Tests:** `infra/tests/test_makefile_disk_precheck.py` (red first: `make -n up` shows no precheck), report unit test on a stubbed REST. · **QA:** run the report; a merged branch's worktree is listed "remove". · **Dirs:** `Makefile`, `scripts/ops/`, `docs/ops/`, `infra/tests/`.

#### EM-ESC-06, PM-6, BA-6, PE-6a, PE-6b, SEC-6, COACH-6a, PD-6, DR-06, ML-6, ST-176b (docs, tier 0)
Acceptance per the §3.2 titles. EM-ESC-06 asks each question once with options, a default, a need-by date and the cost of each option (the PE's port-first / slice-first / strangler costs for P21). PE-6a fixes the bounded context (patterns and references owned by the sport plugin as versioned content, measures in Analytics, gaps in Coaching/weakness behind the ACL), the ADR 0003 relation (A4) and updates `docs/architecture/context-map.md`. PE-6b closes ADR 0015's pending reviews with the security-privacy-engineer. COACH-6a writes each pattern as a rule with one happy and one negative worked example, reproduced against the code that exists, and the sources register with a resolve status per citation. PD-6 stays ≤ 400 lines per family. DR-06's cells are carried by each decider's own review on the PD-6 PR; the chair never writes a decider's cell (ADR 0037 rule 2). Doc checks as above; no red test (no executable behaviour).

#### COACH-6b
ST-171 · FR-171.R2-R4 · **Acceptance:** `docs/domain/hand-counts/GS-PAT-1-v1.json` (planned) (team-made Full Tag fixture, no real people) with hand-counted AN-09, AN-13 (and AN-08 if labelled) per side; `docs/domain/tools/pattern_example.py --check` prints 0 differences against the catalogue's worked tables. · **Tests:** red first: `--check` before the tables exist → rc 1 naming each missing table. · **QA:** QA recounts one match by hand. · **Dirs:** `docs/domain/hand-counts/`, `docs/domain/tools/`.

#### CI-TIERS-06 (tier 2) — ADR 0056 required ticket (a)
PRC-06 · PRC-10.1-10.2 · **Acceptance:** tier 2 globs for `backend/src/racket/**/provenance*`, `backend/src/racket/**/pose*`, `backend/src/racket/analytics/patterns/snapshot*`, `models/**`, footage and consent paths; `content/references/**` tier 1 with the pickleball-domain-coach flag; QA APPROVE by name still required on tier 1-2; new globs that match nothing yet are `PENDING_GLOBS` naming ST-171e, ST-175a, ST-175b. · **Tests:** `infra/tests/test_review_tiers.py` Scenario Outline rows (red first), glob liveness. · **QA:** QA writes the path matrix before the code. · **Dirs:** `scripts/ci/review_tiers.py`, `infra/tests/`.

#### CI-DOC-CHECK-06 — ADR 0056 required ticket (b)
PRC-06 · PRC-11.1-11.3 · **Acceptance:** `check_docs.py` fails when a `content/references/**` entry's `source.citation_id` names no row of `docs/domain/sources.md` (planned); the job runs `check_threat_notes.py` on the newest threat notes; `pr-policy` fails a ready ticket PR whose decisions file has no cost-per-PR table. Existing rules (paths, `[ASB/<ID>]` citations, `.claude/agents` front matter, decider cells, atomic breakdown) stay. · **Tests:** `infra/tests/test_doc_check.py` planted cases (red first). · **Dirs:** `scripts/ci/check_docs.py`, `.github/workflows/ci.yml` (doc-check job), `infra/tests/`.

#### QA-WIP-GATE
PRC-06 · PRC-12.1 · **Acceptance:** `scripts/measure/wip_gate.py --stage start` (planned) exits 1 naming the full stage; counts from REST (open ticket PRs by draft state, review verdicts on the head, QA verdict, merge-ready); the orchestrator calls it before every "start ticket" step and logs the refusal. · **Tests:** unit with stubbed REST (red first: 3 in review → start allowed today). · **Dirs:** `scripts/measure/`, `infra/tests/`.

#### ST-170a (tier 2)
ST-170 · FR-170.R1-R3 · **Acceptance:** `content/references/<set>/vN.json` schema (pattern id `AN-nn`, definition version, better_direction `higher` / `lower` / `inside_band` (must equal the catalogue's), value or band (a band is required for `inside_band`), n, interval, level band, format, source_type, source {citation_id | footage_id + rights record id}, status, version); `racket-reference-lint` fails closed on any missing field, an unresolved citation, a measured entry whose footage does not permit "reference-library", a duplicate (pattern, band, format, version) and an edited published version (lock hash). · **Tests:** `tests/features/reference_set.feature` (planned) (FR-170.R1-R3); IT-06-01; unit per refusal (red first: a missing source passes today because nothing checks it). · **QA:** planted fixture per refusal. · **Context:** sport plugin content + Coaching/reference. · **Dirs:** `backend/src/racket/coaching/reference/`, `content/references/`, `backend/tests/`.

#### COACH-6c
ST-170 · FR-170.R1 · **Acceptance:** reference set v1 with entries for AN-04, AN-05, AN-07 (wave A, QT) and AN-09, AN-13 (wave B, FT) per level band and format, each `coach-reviewed`, `source_type` `published` (citation resolves) or `judgment` (labelled), lint rc 0. No value says "pro" unless its source does. · **Tests:** lint in CI (no new code). · **Dirs:** `content/references/` (planned).

#### QA-REF-GOLD
ST-170 · **Acceptance:** `backend/tests/regression/golden_patterns/` (planned) expected values for reference v1 × GS-PAT-1 (measures, states, ordering) written before ST-171b/c and ST-172a; a hash test refuses edits without an ADR. · **Tests:** the golden test is red until the extractors exist (recorded). · **Dirs:** `backend/tests/regression/`.

#### ST-170b (tier 2)
ST-170 · FR-170.R4, NFR-050.10 · **Acceptance:** `GET /reference-sets/current` and `GET /reference-sets/{version}/entries/{id}`; signed-in only; draft entries never returned (404); `Cache-Control: no-store`; no write route. · **Tests:** IT-06-02, BOLA rows, contract test `web/tests/contract/reference-set.contract.test.ts` (planned) (planted). · **Dirs:** `backend/src/racket/coaching/`, `backend/tests/`, `web/tests/contract/`.

#### ST-170c
ST-170 · FR-170.R5 · **Acceptance:** read-only list with definition, version, provenance label, n, interval, "needs verification" badge; five UI states. · **Tests:** component tests per state (red first: provenance label absent fails); E2E in ST-174b. · **Dirs:** `web/src/app/references/` (planned), `web/src/components/`, `web/tests/unit/`.

#### ST-171a
ST-171 · FR-171.R1, R5, R6 · **Acceptance:** `PatternMeasure` (pattern id, value, n, interval, interval_method (`wilson` for proportions, `order_statistic_median` for AN-13; the Why citation names it), low_sample, rankable, unavailable_reason, n_excluded, definition version); a Quick Tag adapter that reuses `analytics/starter_stats.py` and `uncertainty.py` unchanged. · **Tests:** IT-06-03 (equivalence with starter stats on GS-AN-1); unit (red first: unavailable reported as 0). Mutation ≥ 0.80; module joins `DOMAIN_TEST_PATHS` and the nightly mutation list. · **Dirs:** `backend/src/racket/analytics/patterns/` (planned).

#### ST-171b, ST-171c, ST-171d
ST-171 · FR-171.R2-R4, R7 · **Acceptance:** pure functions over validated Full Tag label documents (`dataset/labels.py` vocabulary through the ACL), standard library only; every rally counted once (counted ∪ excluded = all). · **Tests:** table-driven unit + Hypothesis property tests in the serial property step (not the 10 s domain budget, BE kickoff); `pattern_example.py --check` and QA-REF-GOLD green. Red first: a 2-hit rally counted as a third shot. Mutation ≥ 0.80. · **Dirs:** `backend/src/racket/analytics/patterns/` (planned).

#### ST-171e (tier 2)
ST-171 · NFR-063.3, NFR-066.10, NFR-075.1 · **Acceptance:** measure snapshot table keyed on (subject, pattern id, match version, rules_version, definition version) and gap results on that key + reference_version (PE-PLAN06-04); Alembic migration with downgrade; classification rows; deletion cascade with matches. · **Tests:** IT-05-05 extended (red first: unclassified column), IT-06-04 deletion, migration round-trip. · **Dirs:** `backend/src/racket/analytics/patterns/` (planned), `backend/src/racket/migrations/versions/`, `docs/security/data-classification.md`.

#### ST-172a
ST-172 · FR-172.R1-R4 · **Acceptance:** `coaching/weakness/reference_gap.py` (planned) pure; states weakness (with side: below / above, from the pattern's better_direction) / no clear gap / not enough data / no reference yet; ordering by gap in band widths (interval width for a point reference), ties by rallies lost (ADR 0003 cell), then catalogue order. · **Tests:** `tests/features/reference_gap.feature`; unit (red first: overlap ranked); property (deterministic, permutation-stable). Mutation ≥ 0.80. · **Dirs:** `backend/src/racket/coaching/weakness/`.

#### ST-172b (tier 2)
ST-172 · FR-172.R6, NFR-010.10-.12, NFR-050.10, NFR-069.2, NFR-075.2 · **Acceptance:** `GET /me/weaknesses?match=<id>` returns every pattern with state, player value, n, interval, reference id, version, status, provenance label and rank; owner-scoped (404 foreign, 401 anonymous); `no-store`; ≤ 4 statements per read of an unchanged match; Locust `weakness-view` task. · **Tests:** IT-06-05 (statement count), IT-06-06 (golden replay), BOLA rows, contract test, NFR-069.2 planted-value grep. · **Dirs:** `backend/src/racket/coaching/`, `backend/tests/`, `backend/tests/perf/`, `web/tests/contract/`.

#### ST-172c
ST-172 · FR-172.R5, NFR-027.11/.12/.14 · **Acceptance:** `/weaknesses` page: states from PD-6, gap chart with printed values and a data table, text labels per state, provenance component, "Show me" to the player's own rallies (EvidencePanel). · **Tests:** component per state and the table-equals-chart test (red first); contrast check on the chart tokens. · **Dirs:** `web/src/app/weaknesses/` (planned), `web/src/components/`, `web/tests/unit/`.

#### ST-173a
ST-173 · FR-173.R1, R2, R4 · **Acceptance:** the plan generator receives ranked gaps through the weakness ACL and picks drills with the gap's AN id in `target_metrics` under the existing players, equipment, level, time and safety filters; the Why validator rejects a line missing any cited part; no fitting drill → "no exercise yet" and a coverage finding. · **Tests:** IT-06-07 (plan API), unit for the validator (red first), eval cases in `coaching/evals` at pass^3 = 100 %. · **Dirs:** `backend/src/racket/coaching/plan/`, `backend/src/racket/coaching/evals/`.

#### ST-173b
ST-173 · FR-173.R3 · **Acceptance:** `coaching/drills/coverage.py` enumerates the rankable new patterns × level × players × equipment; rc 1 naming the cell. · **Tests:** unit (red first: a gap fixture passes today). · **Dirs:** `backend/src/racket/coaching/drills/`.

#### ST-173c
ST-173 · FR-173.R1, R3 · **Acceptance:** ≤ 6 drills (`content/drills/`), each `coach-reviewed`, safety-classed, reviewed against `docs/domain/drill-review-checklist.md`; drill lint, lock and coverage rc 0. · **Dirs:** `content/drills/`.

#### ST-173d
ST-173 · FR-173.R2 · **Acceptance:** PlanView and PlanViewWords render the reference citation and label; "no exercise yet for this gap" state. · **Tests:** component (red first). · **Dirs:** `web/src/components/plan/`, `web/tests/unit/`.

#### ST-174a
ST-174 · DEMO-6.1 · **Acceptance:** `scripts/demo/seed_demo.py` seeds reference v1, demo players "demo-a" and "demo-b" (Quick Tag + team-made Full Tag), and prints the three URLs; idempotent twice; `FEATURE_REFERENCE_PATTERNS` in `infra/compose.yaml` and `infra/env.example` (parity test). · **Tests:** `infra/tests/test_seed_demo_plan.py` extended (red first), env parity test. · **Dirs:** `scripts/demo/`, `infra/`, `infra/tests/`.

#### ST-174b
ST-174 · DEMO-6.2-6.4, NFR-027.10/.13 · **Acceptance:** `web/e2e/sprint-06/reference-slice.spec.ts` (planted) tagged `@critical`: both demo players, different top gaps and drills; reference v2 planted → Why changes; flags-off project unchanged; axe 0 and target-size scan. · **Tests:** the spec itself (red first against the current stack). TCR row in the first push if any accepted spec is touched. · **Dirs:** `web/e2e/sprint-06/` (planned).

#### ST-175a (tier 2)
ST-175 · FR-174.R1-R3, NFR-063.4 · **Acceptance:** provenance record (source, rights holder, rights basis owned/licensed/consented, permitted uses, expiry, consent reference per filmed person); job creation refuses without it (422, nothing decoded); revocation hook for the reference lint. · **Tests:** IT-06-08 (red first: a job without a record is created today), unit per refusal. · **Dirs:** `backend/src/racket/video_ingest/` or `dataset/manifest.py` per PE-6b, migration, `docs/security/data-classification.md`.

#### ST-175b (tier 2)
ST-175 · NFR-062.1-.3 · **Acceptance:** the SBOM licence job covers the worker image and `models/manifest.json` (planted, empty today); AGPL, SSPL, non-commercial or unknown fail; network-denied test of the worker. · **Tests:** `infra/tests/test_licence_gate.py` with a planted AGPL package and a weights row without licence (red first). · **Dirs:** `.github/workflows/ci.yml` (licence job), `scripts/ci/`, `models/` (planned), `infra/tests/`.

#### ST-176a
ST-176 · NFR-006.7, SPK-1.2 · **Acceptance:** `scripts/eval/run_eval.py` (planned) and `docs/evals/TEMPLATE.md` (planned) with the ADR 0060 columns; dry-run on phone fixtures commits one report; a planted regression → rc 1. · **Tests:** unit (red first), dry-run row in scorecard §6 under G06-09. · **Dirs:** `scripts/eval/`, `docs/evals/`.

#### SEC-R05, SEC-R11 (tier 2)
SEC-R · NFR-050.11, NFR-050.12 · **Acceptance:** per ADR 0059 R-05 and R-11; ASVS rows move from Fail to Pass with evidence. · **Tests:** IT (red first: a 601 s old link accepted; sha1 accepted). · **Dirs:** `backend/src/racket/platform/settings.py` (R-05), `backend/src/racket/video_ingest/domain/extensions.py` and `backend/src/racket/video_ingest/api.py` (R-11), `docs/security/asvs-l2-checklist.md`.

#### QA-PIN-06, VERIFY-06, SMOKE-06, RETRO-06
As Sprint 5 (scorecard §3); RETRO-06 also writes the cost-per-PR report and the all-role reflection.

### 3.8 Definition of Ready check (business-analyst with engineering-manager, 2026-11-13)

`06/requirements-breakdown.md` §7. Every wave 2 story is **Not Ready** at planning, waiting on named gate tickets and E1. Per BA-1, "Ready" means its gate tickets are merged with PR numbers; the orchestrator does not route a "Not Ready" story (working-agreement §7 3e). Any item still marked [NEEDS CLARIFICATION] keeps its story out (A5 affects only COACH-6c citations of secondary statistics: default applies until P22 is answered).

## 4. Task breakdown per role agent

| Role | Tickets |
|---|---|
| engineering-manager | PLAN-06, EM-ESC-06, RETRO-06; drain sequencing and status steps (stage counts, breaches, worktree list); RETRO-05 (Sprint 5 ticket) |
| product-manager | PM-6; release-readiness view at the review |
| business-analyst | BA-6; Three Amigos per story with coach, ML and QA |
| principal-engineer | PE-6a, PE-6b; review of every tier 1-2 PR |
| principal-designer | PD-6, DR-06; UI reviewer |
| security-privacy-engineer | SEC-6; tier 2 reviewer (ST-170a/b, ST-171e, ST-172b, ST-175a/b, SEC-R05/R11, CI-TIERS-06) |
| pickleball-domain-coach | COACH-6a, COACH-6b, COACH-6c, ST-173c; domain reviewer |
| senior-backend-engineer | ST-170a, ST-170b, ST-171a, ST-171e, ST-172a, ST-172b, ST-173a, ST-173b, ST-174a, ST-175a, SEC-R05, SEC-R11 |
| senior-frontend-engineer | ST-170c, ST-172c, ST-173d; #218, #226 in the drain |
| senior-qa-engineer | QA-WIP-GATE, QA-REF-GOLD, ST-174b, QA-PIN-06, VERIFY-06; VERIFY-05 in the drain; tier 1-2 test review |
| sre-devops-engineer | CI-SCHEDULED-RED, OPS-DISK-06, CI-TIERS-06, CI-DOC-CHECK-06, ST-175b, SMOKE-06; #230, #232 and SMOKE-05 in the drain |
| senior-ml-cv-engineer | ML-6, ST-171b, ST-171c, ST-171d, ST-176a, ST-176b; reviewer of dataset/eval PRs |

## 5. TDD plan (negative case first) [EP/ENG-18]

Order in every code ticket: (1) Gherkin scenario committed, (2) integration test, (3) unit tests — all seen failing, the red output pasted in `decisions/<ID>.md` with a `Red:` line; (4) smallest implementation; (5) refactor in a separate commit. Negative case first:

| Ticket | First red test |
|---|---|
| CI-SCHEDULED-RED | payload of run 43007950254 → expects a red line; today none |
| OPS-DISK-06 | `make -n up` has no precheck line |
| CI-TIERS-06 | a `models/manifest.json` path → tier 2 (today: unmatched → 2 by fail-closed; the test asserts the named rule and the coach flag on `content/references/**`) |
| CI-DOC-CHECK-06 | a reference entry citing an unknown source id passes today; a ready PR with no cost table passes today |
| QA-WIP-GATE | a 4th start with 3 in review is allowed today |
| COACH-6b | `pattern_example.py --check` with no tables → rc 1 |
| ST-170a | an entry with no source id passes today |
| ST-170b | a draft entry fetched by id → expects 404 |
| ST-171a | AN-09 on a Quick Tag-only match must be unavailable, not 0 |
| ST-171b | a 2-hit rally must not count as a third shot |
| ST-171c | a won dink rally must not be a tolerance sample |
| ST-171e | unclassified snapshot column detected |
| ST-172a | overlapping intervals must give "no clear gap" |
| ST-172b | foreign id → 404; 5 statements per read must fail |
| ST-173a | a Why without the reference version must be rejected |
| ST-173b | a missing solo-wall AN-13 cell must fail |
| ST-174a | `make demo` must print the weakness-view URL |
| ST-174b | two players with identical output must fail |
| ST-175a | a job for an asset without provenance must be refused |
| ST-175b | a planted AGPL package must fail the job |
| ST-176a | a planted regression beyond tolerance must give rc 1 |
| SEC-R05 / SEC-R11 | a 601 s old link accepted; a sha1 checksum accepted |
| UI tickets | a reference value rendered without a provenance label must fail |

Mutation: `analytics/patterns` and `coaching/weakness/reference_gap` join the nightly mutation list (≥ 0.80) in their first PR. Hypothesis property tests run in the serial property step.

## 6. Integration tests (new ids)

| IT id | Ticket | Boundary | Asserts |
|---|---|---|---|
| IT-06-01 | ST-170a | reference loader + filesystem | v1 loads; each refusal names the entry and field |
| IT-06-02 | ST-170b | API | coach-reviewed entries only; draft 404; `no-store` |
| IT-06-03 | ST-171a | analytics service | Quick Tag measures equal starter stats on GS-AN-1 |
| IT-06-04 | ST-171e | Postgres + deletion | snapshot rows purged with the match; keys present |
| IT-06-05 | ST-172b | API + DB | ≤ 4 statements per read of an unchanged match |
| IT-06-06 | ST-172b | API | golden replay byte-identical at a fixed reference version |
| IT-06-07 | ST-173a | plan API | every Why carries all cited parts; no_alternative per gap |
| IT-06-08 | ST-175a | job creation | asset without provenance → 422, nothing decoded |
| IT-05-05 (extended) | ST-171e, ST-175a | ORM metadata | new columns classified |

Every earlier IT id keeps passing (G06-09); integration stays within the 600 s CI budget in its parallel form.

## 7. Gherkin scenarios

```gherkin
# tests/features/reference_set.feature (ST-170a)
Feature: A reference value always says where it came from
  Rule: FR-170.R1 An entry without a resolvable source is refused
    Example: complete coach-reviewed entry
      Given reference set "pb-reference" v1 with an AN-09 entry citing "SRC-0003"
      And "SRC-0003" is a row of the sources register
      When racket-reference-lint runs
      Then it exits 0
    Example: missing source
      Given the same entry without a source
      When racket-reference-lint runs
      Then it exits 1 naming the entry and "source"

# tests/features/reference_gap.feature (ST-172a)
Feature: A weakness is only shown when the evidence supports it
  Rule: FR-172.R1 No overlap, no weakness
    Example: clear gap
      Given the player's AN-09 is 0.20 with a 95% interval of 0.11 to 0.33 over 25 third shots
      And the reference band for level 3.0-3.5 doubles is 0.45 to 0.70
      Then AN-09 is ranked as a weakness
    Example: overlap
      Given the player's AN-09 interval is 0.30 to 0.55
      Then AN-09 shows "no clear gap" and is not ranked
    Example: above the band (AN-09 better_direction inside_band)
      Given the player's AN-09 interval is 0.80 to 0.92 over 25 third shots
      And the reference band for level 3.0-3.5 doubles is 0.45 to 0.70
      Then AN-09 is ranked as a weakness "above band"
  Rule: FR-172.R2 Too little data is said, not ranked
    Example: n below min_n
      Given 7 third shots and min_n 20
      Then AN-09 shows "not enough data (7 of 20)"

# tests/features/exercise_why.feature (ST-173a)
Feature: Every recommended drill cites the gap and the reference
  Rule: FR-173.R2 The Why names pattern, value, n, interval, reference id, version and status
    Example: complete Why
      Given AN-09 is ranked against REF-AN09-D35 v1
      When the plan is generated
      Then the drill's Why contains "AN-09", "n 25", "REF-AN09-D35 v1" and "coach-reviewed"
    Example: version missing
      Given a plan line whose Why has no reference version
      When the plan is validated
      Then the line is rejected

# tests/features/footage_provenance.feature (ST-175a)
Feature: No footage is analysed without a rights basis
  Rule: FR-174.R1 Fail closed at job creation
    Example: consented training clip
      Given a clip with a provenance record "consented" permitting "analysis"
      When an analysis job is requested
      Then the job is created
    Example: no record
      Given a clip with no provenance record
      When an analysis job is requested
      Then the answer is 422 "provenance_missing" and nothing is decoded
```

`scheduled_red.feature`, `wip_gate.feature`, `pattern_an09.feature` and `demo_slice.feature` follow the same Rule/Example shape in their tickets.

## 8. Quality gates

1. **Merge:** only via `merge_ready.py` on the exact head SHA, one at a time (ADR 0050), with the tier verdicts (tier 0: one fresh-context APPROVE + `doc-check`; tier 1: principal-engineer + `Reviewer: senior-qa-engineer`; tier 2: + `Reviewer: security-privacy-engineer` and flagged specialists). After CI-SCHEDULED-RED: refused while the latest scheduled CI on `main` is red.
2. **CI:** `ci-gate` green on the head (lint, types, unit, integration ≤ 600 s, E2E chromium + webkit, axe, BOLA, dependency, secret and licence scans, `Red:` check, test immutability, size, `doc-check` incl. atomic breakdown and decider cells, reconcile in pr-policy).
3. **Size:** ≤ 400 production lines (`check_pr_size.py`, ADR 0054); a waiver only while draft, by the PR-policy step.
4. **Content gates (tickets, retro 4 L15):** reference lint and lock (ST-170a); citation resolution (CI-DOC-CHECK-06); coverage with the new axis (ST-173b); plan eval pass^3 with new cases (ST-173a); pattern gold check (COACH-6b, QA-REF-GOLD); licence over weights (ST-175b); provenance gate (ST-175a); design gate DR-06 (`check_flows.py --decider`).
5. **Nightly:** `perf-r1` with the weakness-view task (G06-06), mutation incl. the new modules, browser matrix with the @critical slice journey.
6. **Reviewer checklist additions (kickoff):** every reference value has provenance and status; no "pro" claim without a source that says so; no CV-derived value shown as fact; "configurations exercised" and "data provenance" lines in every QA verdict; config wired end to end; author-found gaps raised as findings; one verdict per head SHA.

## 9. Definition of Done

Story level (`docs/process/definition-of-done.md`) plus, for this sprint:
- [ ] Gherkin + IT + unit tests first, seen failing, `Red:` output in the decisions file; docs tickets state why TDD does not apply and show the doc checks.
- [ ] Tier verdicts on the head SHA and the senior-qa-engineer test of the head (tier 1-2); `ci-gate` green.
- [ ] Atomic items listed in the decisions file; traceability rows added in the same PR.
- [ ] Every reference value carries source_type, source id, status and version; no unverified coaching fact without `@needs-verification`.
- [ ] Any new setting wired to Compose and `env.example` (parity test), exercised flags on and off.
- [ ] Author-found gaps (e.g. "pattern not measurable from tags", "no reference for level X", "no drill fixes gap Y") written as parseable finding ids with ledger rows (L13).
- [ ] **Cost per PR table** in `decisions/<ID>.md` from the first commit: one row per round (author build, each review, each fix, each CI round) with `wall_time_min` (agent wall time) and `total_cost_usd` or tokens when exposed, otherwise "not measured" — never estimated (ADR 0056 decision 1).
- [ ] The method's §6 dry-run row (rc 0 and planted-failure rc) for tickets that own a scorecard method.
- [ ] Stacks the ticket started are torn down; its worktree removed; `df -h /` at start and end.

### 9.1 Sprint-DoD rows for human-gated items (PO P12 option b)
Scorecard §5 rows S6-P21, S6-P11, S6-P15, S6-P16, S6-P22, S6-P7, S6-P9, S6-P19, S6-P8, S6-D1: each "not met: waiting on P-n" until the human supplies the input.

## 10. Risks for this sprint

| Risk | Raised by | Mitigation |
|---|---|---|
| The PO does not confirm the S6/S7 reorder (P21) and the 2026-10-06 Go-port decision stands | PE, EM, QA, BA | ask on day 1 with a default; slice is tag-based, CV-optional, pure functions, no new framework; spike code disposable |
| Sprint 5 drain eats the sprint (13 PRs, ledger open 5, WIP 12 vs 3) | all | E1 entry condition; 25 % capacity reserve; QA-WIP-GATE; turns routed to review |
| No footage with rights or consent (P11) | all | demo on team-made fixtures; FR-170.R5 label; P11 row lists the prepared gates and harness |
| Reference values read as "pro best practice" without a source | PM, BA, COACH, PD, QA | status ladder, sources register, citation lint, UI label; P15 row |
| Amateur vs pro comparison misleads; small n | COACH, PE, ML, QA | level bands; non-overlap rule; min_n; "not enough data"; property tests |
| Facets without κ ≥ 0.7 used as if validated | PE, COACH | facet-derived measures labelled "single-labeller, agreement not measured" until QD-TX-03/04 |
| Personal data and licences (pose, training video, AGPL weights) | SEC, ML, SRE | tier 2 with security; PE-6b; ST-175a/b; pose stays at spike-plan level |
| Design gate fails a fourth time | PD, FE | DR-06 decider steps scheduled one per role; UI tickets depend on DR-06 |
| Disk under the build floor | EM, SRE, FE | OPS-DISK-06; small fixtures; precheck |
| Measurement defects repeat (retro 4 M2, M10, M12) | all | §6 rc 0 + planted-failure rows; QA-PIN-06 |
| Two rankings (rallies lost vs reference gap) confuse the player | PE, COACH | ADR 0061 decides; A4 default |

## 11. Dependencies

Human: §0.4. Internal: §15 `depends_on` and entry condition E1. External tools: Locust 2.46.7, Playwright Chromium (preinstalled; never `playwright install`), Hypothesis, the existing SBOM tooling.

## 12. Demo script (sprint review, 2027-01-15)

1. On a fresh worktree, `export COMPOSE_PROJECT_NAME=racket-demo06 FEATURE_REFERENCE_PATTERNS=true`, then `make up`; `make demo` twice (DEMO-6.1).
2. Open the reference browser: each pattern shows its definition, version, provenance label ("coach judgment, not measured from pro matches" or "published source") and status `coach-reviewed` (FR-170.R5).
3. Sign in as demo-a: the weakness view lists every pattern with its state; AN-09 is a ranked weakness with n and interval beside the reference band; one pattern shows "not enough data"; the chart's data table shows the same values (FR-172, NFR-027.12).
4. Open the plan: each recommended drill's Why cites the pattern, value, n, interval, reference id, version and status (FR-173.R2).
5. Sign in as demo-b: different top gap, different drills (DEMO-6.2).
6. Swap reference v1 → v2 for AN-09 (planted fixture), regenerate: the Why changes (DEMO-6.3).
7. Restart with the flag off: the R1 journey is unchanged (DEMO-6.4).
8. Show a job request for an asset with no provenance refused (FR-174.R1) and the licence gate red on a planted AGPL row (NFR-062.1).
9. Show flow metrics and cost per PR (G06-10); the PO list with what waits on whom (§0.4).
10. `make down`.

## 13. Retrospective

`docs/retros/2027-01-15-sprint-06.md` (planned), written once by RETRO-06 after VERIFY-06. Start / Stop / Continue plus the all-role reflection (every role, owned and dated actions); reviews RETRO-05's actions first; reviews the WIP gate, the drain and the 12-role cost question with G06-10 data (ADR 0056).

## 14. Traceability

Atomic item → story → ticket → tests: `06/requirements-breakdown.md` §1-§5 and §3.7 above; scorecard rows in `06/goal-scorecard.md` §2. BA-6 adds the rows to `docs/requirements/traceability-matrix.md`.

## 15. Ticket map (ADR 0047 rule 4; branches `s06/<id-lowercase>` from current `main`)

| Ticket | Branch | Owner | Tier | Depends on | Files (shared files merge in the §3.6 item 6 order) | ci_fix |
|---|---|---|---|---|---|---|
| CI-SCHEDULED-RED | `s06/ci-scheduled-red` | sre | 1 | — | `scripts/measure/`, `scripts/ci/merge_ready.py`, `infra/tests/` | yes |
| OPS-DISK-06 | `s06/ops-disk-06` | sre | 1 | — | `Makefile`, `scripts/ops/`, `docs/ops/disk-and-prune.md` | no |
| EM-ESC-06 | `s06/em-esc-06` | em | 0 | — | `docs/sprints/06/po-escalations.md` (planned) | no |
| PM-6 | `s06/pm-6` | pm | 0 | — | `docs/sprints/roadmap.md` (Product Goal) | no |
| BA-6 | `s06/ba-6` | ba | 0 | — | `docs/requirements/`, `docs/process/ddd-guidelines.md`, `docs/sprints/06/requirements-breakdown.md` | no |
| PE-6a | `s06/pe-6a` | pe | 0 | — | `docs/decisions/` (ADR 0061), `docs/architecture/context-map.md` | no |
| PE-6b | `s06/pe-6b` | pe | 0 | — | `docs/decisions/` (ADR 0062, ADR 0015 status) | no |
| SEC-6 | `s06/sec-6` | sec | 0 | — | `docs/security/threat-notes-sprint-06.md` (planned) | no |
| COACH-6a | `s06/coach-6a` | coach | 0 | — | `docs/domain/pattern-catalogue.md` (planned), `docs/domain/sources.md` (planned) | no |
| COACH-6b | `s06/coach-6b` | coach | 1 | COACH-6a | `docs/domain/hand-counts/`, `docs/domain/tools/` | no |
| PD-6 | `s06/pd-6` | pd | 0 | COACH-6a | `docs/design/flows-sprint-06.md` (planned) | no |
| DR-06 | `s06/dr-06` | pd | 0 | PD-6 | `docs/design/flows-sprint-06.md` (planned) decider table | no |
| ML-6 | `s06/ml-6` | ml | 0 | COACH-6a | `docs/data/pattern-sources.md` (planned) | no |
| CI-TIERS-06 | `s06/ci-tiers-06` | sre | 2 | — | `scripts/ci/review_tiers.py`, `infra/tests/` | no |
| CI-DOC-CHECK-06 | `s06/ci-doc-check-06` | sre | 1 | COACH-6a | `scripts/ci/check_docs.py`, `.github/workflows/ci.yml`, `infra/tests/` | no |
| QA-WIP-GATE | `s06/qa-wip-gate` | qa | 1 | — | `scripts/measure/`, `infra/tests/` | no |
| ST-170a | `s06/st-170a` | be | 2 | PE-6a, COACH-6a, SEC-6, CI-TIERS-06 | `backend/src/racket/coaching/`, `content/`, `backend/tests/` | no |
| COACH-6c | `s06/coach-6c` | coach | 1 | ST-170a, CI-DOC-CHECK-06 | `content/references/` (planned) | no |
| QA-REF-GOLD | `s06/qa-ref-gold` | qa | 1 | ST-170a, COACH-6b | `backend/tests/regression/` | no |
| ST-170b | `s06/st-170b` | be | 2 | ST-170a | `backend/src/racket/coaching/`, `backend/tests/`, `web/tests/contract/` | no |
| ST-170c | `s06/st-170c` | fe | 1 | ST-170b, DR-06 | `web/src/`, `web/tests/unit/` | no |
| ST-171a | `s06/st-171a` | be | 1 | PE-6a, COACH-6a | `backend/src/racket/analytics/`, `backend/tests/` | no |
| ST-171b | `s06/st-171b` | ml | 1 | ST-171a, COACH-6b | `backend/src/racket/analytics/`, `backend/tests/` | no |
| ST-171c | `s06/st-171c` | ml | 1 | ST-171a, COACH-6b | `backend/src/racket/analytics/`, `backend/tests/` | no |
| ST-171d | `s06/st-171d` | ml | 1 | ST-171a, COACH-6b | `backend/src/racket/analytics/`, `backend/tests/` | no |
| ST-171e | `s06/st-171e` | be | 2 | ST-171a, SEC-6, PE-6a | `backend/src/racket/analytics/`, `backend/src/racket/migrations/versions/`, `docs/security/data-classification.md` | no |
| ST-172a | `s06/st-172a` | be | 1 | PE-6a, ST-171a, ST-170a | `backend/src/racket/coaching/weakness/` | no |
| ST-172b | `s06/st-172b` | be | 2 | ST-172a, ST-171e, ST-170b | `backend/src/racket/coaching/`, `backend/tests/`, `web/tests/contract/` | no |
| ST-172c | `s06/st-172c` | fe | 1 | ST-172b, DR-06 | `web/src/`, `web/tests/unit/` | no |
| ST-173a | `s06/st-173a` | be | 1 | ST-172a | `backend/src/racket/coaching/plan/`, `backend/src/racket/coaching/evals/` | no |
| ST-173b | `s06/st-173b` | be | 1 | COACH-6a | `backend/src/racket/coaching/drills/coverage.py` | no |
| ST-173c | `s06/st-173c` | coach | 1 | ST-173b | `content/drills/` | no |
| ST-173d | `s06/st-173d` | fe | 1 | ST-173a, DR-06 | `web/src/components/plan/`, `web/tests/unit/` | no |
| ST-174a | `s06/st-174a` | be | 1 | ST-172b, ST-173a, COACH-6c | `scripts/demo/seed_demo.py`, `infra/compose.yaml`, `infra/env.example`, `infra/tests/` | no |
| ST-174b | `s06/st-174b` | qa | 1 | ST-174a, ST-172c, ST-173d | `web/e2e/` | no |
| ST-175a | `s06/st-175a` | be | 2 | PE-6b, SEC-6 | `backend/src/racket/`, `backend/src/racket/migrations/versions/`, `docs/security/data-classification.md` | no |
| ST-175b | `s06/st-175b` | sre | 2 | PE-6b | `.github/workflows/ci.yml`, `scripts/ci/`, `infra/tests/` | no |
| ST-176a | `s06/st-176a` | ml | 1 | ML-6 | `scripts/`, `docs/` (evals template, planned) | no |
| ST-176b | `s06/st-176b` | ml | 0 | ML-6, PE-6b | `docs/data/` | no |
| SEC-R05 | `s06/sec-r05` | be | 2 | SEC-6 | `backend/src/racket/`, `docs/security/asvs-l2-checklist.md` | no |
| SEC-R11 | `s06/sec-r11` | be | 2 | SEC-6 | `backend/src/racket/`, `docs/security/asvs-l2-checklist.md` | no |
| QA-PIN-06 | `s06/qa-pin-06` | qa | 1 | ST-172b, ST-174b | `infra/tests/` | no |
| VERIFY-06 | `s06/verify-06-r1` | qa | 0 | all wave 2 tickets, QA-PIN-06 | `docs/sprints/06/decisions/`, `docs/sprints/06/goal-scorecard.md` | no |
| SMOKE-06 | `s06/smoke-06` | sre | 0 | VERIFY-06 | `docs/sprints/06/` smoke record | no |
| RETRO-06 | `s06/retro-06` | em | 0 | SMOKE-06 | status files, report, retro | no |

Machine-readable copy: `docs/sprints/06/ticket-owners.json` (`id`, `branch`, `owner` as a role file name; tier 2; the merge gate reads that file, never this table; the CI-TIERS-b drift test compares them). A change to an owner or branch edits both in one PR. Entry condition E1 (§3.6 item 2) applies to every wave 2 ticket in addition to its `depends_on`.
