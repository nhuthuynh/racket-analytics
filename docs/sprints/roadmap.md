# Delivery Roadmap: racket-analytics

- **Status:** Planned. Sprint 0 is committed. Sprints 1+ depend on the human product owner ratifying ADR 0002 (release slicing, OQ-02) and ADR 0007 (sequencing) at the Sprint 0 review on 2026-10-16.
- **Date:** 2026-10-03
- **Owner:** engineering-manager, with principal-engineer (technical sequencing) and senior-qa-engineer (test readiness)
- **Inputs:** spec `docs/specs/2026-10-02-racket-analytics-design.md`; `docs/requirements/functional-requirements.md`, `non-functional-requirements.md`, `open-questions.md`, `traceability-matrix.md`; brainstorms (PROD §11, ENG §8-§9, DES, QD §7-§9); process docs; ADRs 0001-0010.
- **Decisions behind this roadmap:** ADR 0007 (sequencing), ADR 0008 (stack), ADR 0009 (rules-engine readiness split), ADR 0010 (estimation and capacity).
- **Detail level:** Sprints 0-2 are planned in detail in `sprint-00.md`, `sprint-01.md`, `sprint-02.md`. Later sprints have a goal and a backlog outline only; they are planned just in time at their own sprint planning, once the stories meet the Definition of Ready [EP/ENG-15].
- **Citations:** `<file>/<ID>` per working-agreement §0. Anything not sourced is **(judgment)**.

## 1. Principles

1. **Every sprint ends with something demonstrable**, shown against a bullet-list sprint goal at the review [EP/ENG-15].
2. **Sprint 0 builds the foundations and a walking skeleton**: repo, CI, hooks, test harness and one thin end-to-end path (ADR 0007) [EP/ENG-28, AQS/OPS-05].
3. **R1 closes the value chain without computer vision** (upload → Quick Tag → score sheet → stats → rules-only plan). Vision then replaces manual effort in R2 (ADR 0002).
4. **TDD, DDD, SDLC.** Each story goes discover → requirements → design → TDD implement → review → test → release → retro (working-agreement §2). Each sprint has unit, integration and Gherkin scenario tests, and a retrospective [EP/ENG-18, EP/ENG-20, DPA/PROD-01].
5. **Spikes before commitments.** CV work for R2 is committed only after its spike ends in an ADR with data (ENG §8).
6. **Unverified rules are never presented as official** (FR-055, ADR 0009). Real users wait for the legal gate (NFR-070).

## 2. Calendar

All sprints are 2 weeks (working-agreement §3, judgment). Planning is on the first Monday. Review and retrospective are on the last Friday. Retro files are `docs/retros/<date>-sprint-<nn>.md` from `docs/retros/TEMPLATE.md`.

| Sprint | Dates | Review and retro | Release |
|---|---|---|---|
| S0 | 2026-10-05 → 2026-10-16 | 2026-10-16 | R1 (foundations) |
| S1 | 2026-10-19 → 2026-10-30 | 2026-10-30 | R1 |
| S2 | 2026-11-02 → 2026-11-13 | 2026-11-13 | R1 |
| S3 | 2026-11-16 → 2026-11-27 | 2026-11-27 | R1 |
| S4 | 2026-11-30 → 2026-12-11 | 2026-12-11 | R1 |
| S5 | 2026-12-14 → 2026-12-22 (shortened, 7 working days, judgment) | 2026-12-22 | **R1 release candidate** |
| — | 2026-12-23 → 2027-01-01 | holiday break (judgment; PO availability assumed low) | — |
| S6 | 2027-01-04 → 2027-01-15 | 2027-01-15 | R2 |
| S7 | 2027-01-18 → 2027-01-29 | 2027-01-29 | R2 |
| S8 | 2027-02-01 → 2027-02-12 | 2027-02-12 | R2 |
| S9 | 2027-02-15 → 2027-02-26 | 2027-02-26 | **R2 release candidate** (MVP = R1 + R2) |
| S10-S12 | 2027-03-01 → 2027-04-09 | each last Friday | R3 (post-MVP), outline only |

## 3. Capacity assumptions for the agent team (ADR 0010, all judgment)

| Item | Assumption |
|---|---|
| Implementation lanes | senior-backend-engineer (BE), senior-frontend-engineer (FE), senior-ml-cv-engineer (ML), senior-qa-engineer (QA), sre-devops-engineer (SRE) |
| Docs-only roles | engineering-manager, product-manager, business-analyst, principal-engineer, principal-designer, security-privacy-engineer (read-only reviewer), pickleball-domain-coach. They carry dated tasks, not units |
| Sizes | XS 0.5 · S 1 · M 2 · L 4 units; XL must be split. 1 unit ≈ 2 PRs of about 100 lines, including tests and the review loop [EP/ENG-04] |
| Streams | ≤ 2 parallel streams per lane, only in disjoint modules or contexts; one story at a time per stream [EP/ENG-28, EP/ENG-26] |
| Nominal capacity | 8 units per stream per sprint → 16 per lane |
| Load factor | S0 70%; S1 80%; from S2 the lower of 85% and the measured median completion ratio of the last two sprints |
| Review loop | Every code PR: senior-qa-engineer + one engineer peer or principal-engineer, plus specialist reviewers (working-agreement §6). ≤ 3 fix iterations, then escalation (§7) |
| Token cost | Fan out to parallel agents only where streams are independent; multi-agent work costs about 15x chat tokens [DPA/AI-02, EP/ENG-26] |
| Human product owner | About 2 h per sprint review plus answers to escalations within 3 business days (assumption, to confirm at S0 planning). Human-only actions: rulebook supply, consent, legal review, spend, recruiting testers, release sign-off |
| Holidays | S5 shortened; no sprint 2026-12-23 → 2027-01-01 |

Planned load per sprint (units; capacity in brackets is lanes × 16 × load factor for the lanes used):

| Sprint | BE | FE | QA | SRE | ML | Total |
|---|---|---|---|---|---|---|
| S0 | 8 | 4 | 5 | 8 | 3 | 28 (cap 11.2 per lane) |
| S1 | 12 | 12 (+1 stretch) | 4 | 2 | 2 | 32 (cap 12.8 per lane) |
| S2 | 12.5 (+1.5) | 12.5 (+1.5) | 4 | 1 | 2 | 32 (planned at 12.8 per lane) |
| S3+ | set at planning from `status.json` | | | | | |

## 4. Release map

| Release | Sprints | Spec milestones | Increment the user gets | Exit criterion |
|---|---|---|---|---|
| **R1 MVP-1 "Walking skeleton"** | S0-S5 | M0 + subsets of M4 and M5 | Sign in, upload a match, Quick Tag it, get a score sheet (unofficial until OQ-01), starter stats with sample sizes and evidence links, and a rules-only 2-week training plan | PROD §11: a real user uploads, Quick Tags and gets score sheet, starter stats and a plan, median effort ≤ 15 min (NFR-036). Release-level DoD. **Real users only after NFR-070** |
| **R2 MVP-2 "First automation"** | S6-S9 | M1, M2, M5 (LLM "why" and efficacy) | Court calibration, player tracking and heatmaps, automatic rally boundaries, a review queue with confidence bands, LLM-written explanations behind validation, plan efficacy, trends | Rally segmentation F1 ≥ 90% on the frozen gold set (NFR-006, ADR 0004); Quick Tag effort −50% (PROD §11); coaching evals pass (NFR-005) |
| R3 "Automatic scoring" | S10-S12 (outline) | M3, M4 | Automatic rally outcomes with confirmation, shot facets, full analytics, clips | NFR-007 (ADR 0004) |
| Later | — | M6, M7, spec §9 | Opponent scouting, live mode, coach view | per spec |

## 5. Sprint list

"(a)" marks the engine-mechanics part of a rules FR that is Ready now; the preset values wait for OQ-01 (ADR 0009). "partial" means the FR is started and completed in a later sprint shown in the traceability matrix.

| Sprint | Goal (short) | Demonstrable increment | FRs | NFRs |
|---|---|---|---|---|
| **S0** | Foundations and walking skeleton | Compose up; CI gates block a bad PR; hooks block a secret write; create match → upload fixture via tus → worker probe → facts on screen; one trace API → queue → worker | FR-002 (match), FR-022 (tus core), FR-025 (facts), FR-080 (queue base), FR-081 (probe), FR-151 (manifest check) — all partial | NFR-015, 024 (matrix skeleton), 025 (fixtures), 026 (core), 027, 029 (tokens), 046, 047, 050 (checklist skeleton), 051, 052, 054, 056, 058, 061, 062, 064, 065 (review checklist), 069, 071, 073, 074, 076, 077, 078, 080, 081 |
| **S1** | Sign in, set up a match, upload safely; scoring engine test-first | Magic-link sign-in; capture guide; setup flow with nicknames; 3 GB upload survives a dropped connection; invalid files refused; engine mechanics green, provisional SOD/F/M tables reported `@needs-verification`; nightly differential oracle | FR-001, 004, 005, 011, 020, 021, 022, 023, 040 (a), 041 (a), 044 (a), 045 (a); stretch FR-025 | NFR-001 (provisional rows), 002, 016, 025, 026, 028, 030, 031, 032, 033, 034, 035, 037, 041 (SLI), 042 (SLI), 053, 054, 055, 057, 060, 067, 072 (baseline), 079 |
| **S2** | Quick Tag → score sheet (spec M0 "Done when", unofficial) | Tag a match by touch or keyboard; score sheet with "unofficial scoring" label; corrections re-score, conflicts kept, undo; mid-game start; singles; rally row opens the video | FR-024, 027, 042 (a), 046 (a), 048, 049, 050, 051, 052, 053 (a), 055; stretch FR-047, FR-054 | NFR-001 (≥ 46 rows), 010 (baseline), 012, 013, 014, 017 (baseline), 055, 066 (d), 072 (gate), 075 |
| **S3** | Starter stats with uncertainty and evidence; deletion; labelling tools | Stats dashboard for AN-01..AN-07 with n, Wilson interval and low-sample flag; "Show me" opens the rallies; delete a match or account; internal Full Tag tool; drill schema lint in CI | FR-006, 007, 100, 101, 102, 103, 109, 140, 150, 151; stretch FR-047 if not done | NFR-004, 011, 038, 039, 066 (a, b), 078 (gold sets) |
| **S4** | Rules-only training plan; drill library; R1 privacy and quotas | Weakness ranking by rallies lost (serve/receive); 2-week plan within time, players and equipment, every drill citing metric, value, n and rallies; ≥ 20 coach-reviewed drills; age gate; retention and consent settings; rate limits; E2E journey complete | FR-003, 008, 009, 120, 121, 122, 123, 124, 141, 160 | NFR-005 (a), 019 (rules-only), 022 (R1 alerts), 023, 066 (c) |
| **S5** | R1 hardening and release readiness (shortened) | Moderated usability test with ≥ 5 players; SLOs and alerts; restore drill; ASVS L2 review; performance gates; browser matrix; R1 release candidate for PO sign-off; R2 spike ADRs | stretch FR-162 | NFR-010 (gate), 024 (gate), 036, 041, 042, 045, 049, 050, 063, 070 (human gate) |
| **S6** | M1: court calibration, player tracking, identity, heatmaps | Calibration by tap or keys (no drag); 4 players tracked on a multi-court video; "who is who" with one-tap swap fix; position heatmaps with printed values (spec M1 "Done when") | FR-025 (court visibility), 031 (Could), 059, 080 (full lifecycle), 081 (normalise), 082, 083, 105, 106 | NFR-006 (calibration, HOTA), 009 (positioning), 025 (normalise), 030 (calibration), 062 (CV licences) |
| **S7** | M2 part 1: ball, audio, hits, bounces; analysis levels | Ball track with "ball hidden" gaps; hits fused from audio and video; bounce landing spots; explicit analysis level; "analysis ready" notification; GPU-s per match-minute on a dashboard | FR-026, 029, 084, 085, 086, 090 (start) | NFR-006 (ball, hit, bounce), 008 (start), 018, 020, 022 (GPU alerts), 043, 044, 048 |
| **S8** | M2 part 2: rally segmentation, review queue, confidence, re-processing | Rally boundaries pre-filled in Quick Tag; "Needs your eyes" queue ordered by score impact; calibrated bands; re-run on a new pipeline version keeps corrections (spec M2 "Done when" with ADR 0004's F1) | FR-056, 057, 060, 087, 089, 090 | NFR-006 (rally F1 gate), 008 |
| **S9** | LLM-written explanations, efficacy, trends → R2 release candidate | Validated LLM plan with fallback; AI-text label and off switch; "improved / not enough data" follow-up; trends over 5 matches; monthly analysis quota; export | FR-010, 043 (if verified), 104, 125, 126, 127, 161 | NFR-005 (b, c), 019 (LLM), 021, 059, 068, 082 |
| S10-S12 | R3 outline | see §6 | FR-030, 058, 061, 088, 107, 108 | NFR-007, 009 (shot-level), 040 |
| Later | — | — | FR-012, 110, 128; live mode; coach view | — |
| Any sprint after OQ-01 | Official scoring | Coach records rule numbers; preset `USAP-2026` replaces `PROVISIONAL-UNVERIFIED`; hand-scored games match (QD-GD-02) | FR-040..046, 048, 049, 053 (b) | NFR-003 |

## 6. Backlog outlines for later sprints (planned just in time)

### S3: Starter stats, evidence, deletion, labelling tools (2026-11-16 → 2026-11-27)

**Goal:** a player sees the 7 starter stats for a tagged match, each with n, an uncertainty band and a low-sample flag, and can open the rallies behind every number. A player can delete a match or their account. The team can Full Tag consented footage.

Backlog outline:
- Metric dictionary with versioned, coach-reviewed entries AN-01..AN-07 (FR-102); users see only coach-reviewed metrics.
- Starter stats computation from Quick Tag (FR-100), recomputed on `RallyScored`/`ScoreCorrected` (ddd-guidelines §3); attribution conservation invariant (FR-109, ADR 0003).
- Wilson intervals, low-sample rule from config (FR-101, ADR 0005); QD-TR-08 fixtures for every metric.
- Metric cards and "Show me" evidence with ≤ 10 rallies and "see all n" (FR-103, NFR-038 crawl).
- Golden matches QD-GD-03 (3 for R1): metric values equal the coach's hand count exactly (NFR-004).
- Match and account deletion: hidden ≤ 1 min, purged ≤ 7 days, integration test asserts empty storage and DB (FR-006, FR-007, NFR-066; ADR 0006 Proposed).
- Internal Full Tag tool for the labeller role, consented matches only (FR-150); gold-set manifests v1 (FR-151).
- Drill JSON Schema and CI lint (FR-140) so the coach can author drills during S3-S4.
- Spikes: SPIKE-04 GPU provider behaviour (needs OQ-13 spend approval).

### S4: Rules-only plan and drill library; R1 privacy and quotas (2026-11-30 → 2026-12-11)

**Goal:** a player gets a 2-week training plan built only from library drills, fitted to their time, partners and equipment, where every drill says why with a linked metric. The R1 value chain works end to end.

Backlog outline:
- Weakness ranking by rallies lost per game, split serve/receive (FR-120; needs OQ-08 and ADR 0003 acceptance; side-out part `@needs-verification`).
- Deterministic plan workflow: QD-PL-01..PL-04, PL-06 (FR-121, FR-122, FR-123); code-grader eval on rules-only plans at pass^3 = 100% (NFR-005a) [DPA/AI-05].
- Mark sessions done offline and "Not for me" swap (FR-124).
- Starter drill library: ≥ 20 coach-reviewed drills, coverage matrix check in CI (FR-141; content `needs-verification` [DOM G2]).
- Age confirmation and footage notice (FR-003; OQ-05), retention setting (FR-008; OQ-07), training-data consent (FR-009; OQ-06).
- Rate limits and storage quota (FR-160, NFR-023; OQ-13); billing alerts at 50/80/100% (NFR-022).
- E2E journey complete (QD §7): upload → Quick Tag → score sheet → stats → plan.
- Spikes: SPIKE-05 audio hit detection; SPIKE-03 GPU throughput (start); SPIKE-02 ball-tracking baseline (start, needs labelled frames from S3 Full Tag).

### S5: R1 hardening and release readiness (2026-12-14 → 2026-12-22, shortened)

**Goal:** R1 is a release candidate with evidence for every release-level DoD item, and the R2 spikes have reported.

Backlog outline:
- Moderated usability test, ≥ 5 players on their own phones (NFR-036; OQ-20 recruiting by the PO).
- SLOs and burn-rate alerts for API availability and upload completion (NFR-041, NFR-042) [AQS/REL-01, AQS/REL-02]; error-budget policy (NFR-049).
- Restore drill: RPO ≤ 24 h, RTO ≤ 4 h (NFR-045).
- Performance gates at 50 RPS (NFR-010) and the browser matrix (NFR-024; OQ-17).
- ASVS 5.0 L2 release review (NFR-050) [AQS/SEC-01]; data-classification map (NFR-063).
- Legal gate (NFR-070): a human-owned legal/privacy review recorded as an ADR before any real-user beta.
- Pricing fake door (FR-162, Could; OQ-14) as stretch.
- R2 readiness: SPIKE-01 (done in S0), SPIKE-02, SPIKE-03, SPIKE-05, SPIKE-07 ADRs; regression-tolerance ADR for model evals (testing-strategy §6, ADR 0004 follow-up); vision gold set QD-GD-04 v1 frozen.
- R1 release notes and rollback path; PO sign-off (release DoD).

### S6: M1 calibration, tracking, identity (2027-01-04 → 2027-01-15)

**Goal:** on real footage, the court is calibrated with taps or keys, the 4 on-court players are tracked and named once per match, and each player sees a position heatmap.

Backlog outline: analysis job lifecycle with stages and explicit degraded levels (FR-080, FR-026 groundwork); normalisation to CFR, 16 kHz audio and 720p review video (FR-081); court calibration proposal and no-drag adjust (FR-082, NFR-030) [DPA/DESIGN-05]; player detection and tracking with the licence posture from SPIKE-01 (FR-083, NFR-062) [DOM/CV-04, DOM/CV-05]; "who is who" with the 2-per-side constraint (FR-059) [DOM G4 P4]; team-relative frame (FR-105, `@needs-verification` end switching); heatmaps and partner spacing (FR-106); court-visibility estimate (FR-025); framing check (FR-031, Could). Model-quality layer: HOTA via TrackEval [DOM/CV-08], calibration success and reprojection error (NFR-006).

### S7: M2 part 1, ball, audio, hits, bounces (2027-01-18 → 2027-01-29)

**Goal:** a processed match shows the ball track with honest gaps, hits fused from audio and video, and bounce landing spots, with GPU cost measured per match-minute.

Backlog outline: ball tracking with visibility (FR-084) [DOM/CV-01]; audio onset plus visual fusion, never audio alone (FR-085) [DOM/CV-14]; bounce detection and landing positions (FR-086) [DOM/CV-12]; analysis level shown (FR-026); "analysis ready" notification (FR-029) [AQS/STACK-04]; confidence exposed on every value (FR-090 start); GPU-s per match-minute ≤ 120 at R2 entry with alerts (NFR-020); time-to-results gate p90 ≤ 2.0x (NFR-018); analysis SLOs (NFR-043, NFR-044); bounded retries (NFR-048).

### S8: M2 part 2, rally segmentation, review queue, re-processing (2027-02-01 → 2027-02-12)

**Goal:** Quick Tag opens with rally boundaries already set, low-confidence calls are queued by score impact, and re-processing never overwrites a user's correction.

Backlog outline: automatic rally segmentation pre-filling Quick Tag (FR-087), gated at F1 ≥ 90% with ±1.0 s matching (NFR-006, ADR 0004); "Needs your eyes" queue (FR-057) [DPA/DESIGN-11]; confidence word bands backed by gold-set accuracy (FR-090, NFR-008; OQ-10); corrections survive re-processing (FR-056); re-processing with a "what changed" summary (FR-089); correction reason (FR-060, Could). Spike: SPIKE-08 rally-outcome inference (prepares R3).

### S9: LLM explanations, efficacy, trends; R2 release candidate (2027-02-15 → 2027-02-26)

**Goal:** plans gain clear, validated, AI-written explanations (with an off switch), follow-ups never over-claim, and R2 is ready for sign-off.

Backlog outline: coaching eval set of 30 cases from real tagged matches built in S5-S8 (QD-GD-05) [DPA/AI-05]; LLM ordering and "why" with validator, single retry and rules-only fallback (FR-125, NFR-059) [AQS/SEC-08, DPA/AI-01]; minimal data to the LLM (NFR-068); AI-text label and control (FR-126) [DPA/DESIGN-11]; efficacy with Wilson non-overlap (FR-127, ADR 0005); trends (FR-104); monthly analysis quota (FR-161; OQ-13, OQ-14); export (FR-010, Could); rally scoring if verified (FR-043); stub second sport contract test (NFR-082); token budget per plan (NFR-021); model-grader and coach agreement (NFR-005 b, c).

### S10-S12: R3 automatic scoring (outline only)

Shot facets in coarse-first order, after the taxonomy ADR and κ ≥ 0.7 agreement (FR-088, QD-TX-03/04) [DOM/CV-18]; automatic rally outcomes with confirmations (FR-058, NFR-007 per ADR 0004); full rally timeline (FR-061); shot-level analytics and patterns (FR-107, FR-108, NFR-009); evidence clips (FR-030); review effort (NFR-040).

## 7. Spikes

Each spike is time-boxed and ends in an ADR with data (ENG §8). Spike numbers come from ENG §8.

| Spike | Question | Lane | Sprint | Timebox (judgment) | Needs | Feeds |
|---|---|---|---|---|---|---|
| SPIKE-01 | MIT/Apache-only CV stack vs Ultralytics Enterprise | ML + principal-engineer | S0 | 2 days | — | OQ-12; S6 Ready [DOM/CV-05, DOM/CV-07] |
| SPIKE-09 | Postgres queue vs Redis under fan-out | BE + principal-engineer | S0 (inside ST-007) | 2 days | — | ADR 0008 part B |
| SPIKE-06 | Upload behaviour on phone browsers, 8 GB file | FE | S1 | 3 days | test devices | OQ-18; FR-022 copy |
| SPIKE-04 | Serverless GPU provider: cold start, preemption, concurrency, egress cost | ML + SRE | S3 | 3 days | OQ-13 spend approval | S7; NFR-020 |
| SPIKE-05 | Audio hit detection on real recordings, multi-court | ML | S4 | 3 days | consented footage (OQ-06) | FR-085 [DOM/CV-14] |
| SPIKE-03 | GPU-seconds per match-minute per stage, batching, 2 GPU types | ML | S4-S5 | 1 week | SPIKE-04 | NFR-020; S7 commit |
| SPIKE-02 | Ball tracking: TrackNetV3 zero-shot and fine-tuned on ~3,000 labelled frames from ≥ 5 venues | ML | S4-S5 | 1 sprint | Full Tag (S3), consented footage | FR-084; go/no-go per §7.1 (NFR-006 ball F1 ≥ 80%; escalate below 70%) [DOM/CV-01] |
| SPIKE-07 | Auto court calibration on ≥ 30 amateur videos | ML | S5 | 1 week | footage | FR-082; S6 commit [DOM/CV-12] |
| SPIKE-08 | Rally-outcome inference with calibrated confidence | ML | S8-S9 | 1 sprint | R2 gold set | R3 (FR-058) |

### 7.1 CV go/no-go gates (added by principal-engineer review, 2026-10-03; review-log RL-03)

No R2 vision story is Ready on an accuracy that has not been measured. At the planning of the sprint that would commit it, the spike's measured result on the frozen, venue-split gold set (QD-GD-04) is compared with the NFR-006 R2-entry targets (ENG §5.4 CV-T01..T09):

| Sprint commit | Evidence required at planning | Pass (commit at `full` level) | Partial | Fail |
|---|---|---|---|---|
| S6 calibration (FR-082) | SPIKE-07 on ≥ 30 videos | auto-calibration ≥ 70% without fallback **and** reprojection ≤ 15 cm RMS | below either target: commit the tap/keys manual calibration path as the default; auto-proposal stays a capability eval | no usable calibration on ≥ 50% of videos (judgment): escalate scope to the PO (working-agreement §8) |
| S6 tracking (FR-083) | SPIKE-01 licence ADR accepted; HOTA measured on the R2 gold set (or on SportsMOT, evaluation only [DOM/CV-09]) | HOTA ≥ 65 | HOTA < 65: commit with the "who is who" confirmation (FR-059) mandatory on every match | no licence posture accepted: S6 does not start tracking work |
| S7 ball, hits, bounces (FR-084..086) | SPIKE-02 fine-tuned F1; SPIKE-05 hit P/R; SPIKE-03 GPU-s per match-minute | ball F1 ≥ 80%, hit P/R ≥ 85%/85%, GPU ≤ 120 GPU-s per match-minute | ball F1 70-80% or hit P/R below target: commit with ball-derived outputs behind an explicit degraded analysis level (FR-026) and a model-improvement story; the ball-dependent NFR-006 targets are re-baselined only through a superseding ADR approved by the PO | ball F1 < 70% or GPU > 120: escalate scope (degrade to "Rally and score only" for MVP, ENG §8; RM-07, RM-08) |
| S8 rally segmentation gate (FR-087) | S7 outputs on the gold set | rally F1 ≥ 90% | below 90%: rally boundaries are offered as suggestions only, never pre-filled as fact; R2 release gate (NFR-006) not met | — |

Thresholds are the NFR-006 values; the "Fail" cut-offs other than ball F1 < 70% (ENG SPIKE-02) are (judgment). The evidence is a committed eval report (DoD "Vision and ML").

## 8. Dependencies

### 8.1 Human product owner decisions (need-by dates)

| Item | Need by | Blocks if late | Fallback |
|---|---|---|---|
| OQ-02 / ADR 0002, ADR 0007 ratified | S0 review, 2026-10-16 | Sprint 1+ scope | Platform-only work in S1; re-plan |
| ADR 0009 ratified | S0 review, 2026-10-16 | Rules engine in S1-S2 | Engine waits for OQ-01; S1 adds platform stretch |
| ADR 0010 PO-time assumption confirmed | S0 planning | All reviews | EM adjusts review cadence |
| OQ-01 rulebook PDFs | S3 planning (2026-11-16) for official scoring in R1 | NFR-003; official preset | R1 ships "unofficial scoring" (FR-055) |
| OQ-06 footage consent | S1 planning | Real fixture and gold footage (ST-025, ST-040, SPIKE-02/05/07) | Synthetic and empty-court clips; R2 spikes slip |
| OQ-17 reference device and browsers | S1 planning | NFR-011, NFR-014, NFR-024 targets | Use the OQ-17 recommendation as a working assumption |
| OQ-12 CV licence posture | S1 review | S6 Ready | MIT/Apache-only default (NFR-062) |
| OQ-13 spend ceiling and quotas | S2 review | SPIKE-04 (S3), FR-160 (S4) | Spike runs on a capped trial budget only if the PO approves |
| OQ-05 age and minors | S4 planning | FR-003 | Interim wording behind a flag; no real users anyway |
| OQ-07 retention windows (ADR 0006) | S3 planning | FR-006, FR-008, NFR-066 | Build to ADR 0006 values as configuration |
| OQ-08 weakness unit (ADR 0003) | S4 planning | FR-120 | Rallies-lost unit behind config; label "provisional" |
| OQ-20 testers, interviews, second coach | S3 planning | NFR-036 usability test (S5), QD-AN-03 | R1 review without the usability gate; release blocked |
| OQ-14 monetisation test | S5 planning | FR-162 (Could) | Drop the fake door |
| NFR-070 legal review | Before any real-user beta (after S5) | R1 real-user release | Internal and team-only use |
| OQ-10, OQ-11 | S6 planning | FR-090, FR-082 | DES recommendations as working assumptions |

### 8.2 Internal dependencies (critical path)

```
S0 platform (ST-001..ST-012)
  ├─> S1 auth, setup, upload ──────────────┐
  └─> S1 scoring engine (a) ──> S2 Quick Tag + score sheet ──> S3 stats + evidence ──> S4 plan ──> S5 R1 RC
                                     │                              │
                                     └─> S3 Full Tag + gold manifests ──> S4-S5 SPIKE-02/03/05/07 ──> S6 M1 ──> S7 M2a ──> S8 M2b ──> S9 LLM + R2 RC
S3 metric dictionary + drill schema ──> S4 drill library (coach) ──> S9 coaching evals (QD-GD-05 from S5-S8 real tags)
```

- Design docs land one sprint ahead: `Match` aggregate (S1 for S2), Analytics design (S2 for S3), Coaching workflow (S3 for S4), Vision pipeline contracts (S5 for S6) [DPA/DESIGN-15].
- Stories are written by the BA one sprint ahead and must meet the DoR at planning.

## 9. Risks

| # | Risk | Likelihood / impact (judgment) | Mitigation | Trigger to act |
|---|---|---|---|---|
| RM-01 | Rulebook never supplied; score sheets stay unofficial | Medium / High | ADR 0009 split; FR-055 label; engine parameterised | OQ-01 unanswered at S3 planning → PO told R1 ships unofficial |
| RM-02 | OQ-02 not ratified or changed | Low / High | Sprint 0 valid for every option (ADR 0007) | PO rejects ADR 0002 → re-plan S1+ |
| RM-03 | Agent capacity estimates wrong | High / Medium | Low load factors in S0-S1; recalibrate from `status.json` (ADR 0010) | Completion ratio < 70% → re-plan next sprint |
| RM-04 | Review loop is the bottleneck | Medium / Medium | Reviewers flag only correctness and requirement gaps [EP/ENG-24]; small PRs [EP/ENG-04] | PR time-to-merge > 1 day [EP/ENG-02] |
| RM-05 | AI-written code lowers stability | Medium / High | Hooks, CI gates, small batches, change-failure rate weighted heavily [EP/ENG-22] | Change-failure rate rises two sprints running |
| RM-06 | No consented footage for gold sets | Medium / High | Capture protocol (ST-040); team recordings; OQ-06 early | No footage by S4 planning → R2 spikes slip; S6 re-planned |
| RM-07 | GPU cost over budget | High / High (ENG RISK-02) | SPIKE-03/04 before S7; frame-rate plan; alerts (NFR-020) | SPIKE-03 > 120 GPU-s per match-minute → scope ADR to PO |
| RM-08 | Ball-tracking domain gap | High / High (ENG RISK-03) | SPIKE-02; §7.1 go/no-go; degrade to "Rally and score only" (FR-026) | Fine-tuned F1 < 80% (NFR-006) → partial path in §7.1; < 70% → escalate scope (ENG §8) |
| RM-09 | AGPL contamination | Medium / High | NFR-062 licence gate; SPIKE-01 [DOM/CV-05, DOM/CV-07] | Any AGPL package in the shipped graph → CI red |
| RM-10 | Legal review not available | Medium / High | NFR-070 gate; internal use only | No legal ADR by S5 → R1 stays internal |
| RM-11 | Quick Tag effort too high (> 15 min per match) | Medium / High | Keyboard map, design iteration, usability test in S5 | NFR-036 fails → R1 iteration sprint before R2 |
| RM-12 | Holiday period reduces PO availability | High / Low | S5 shortened; escalations sent by 2026-12-16 | — |
| RM-13 | Testers and second coach not recruited (OQ-20) | Medium / Medium | Ask at S0; S5 usability test needs them | No recruits by S3 planning → R1 exit criterion at risk |

## 10. Quality gates by release

- **Every PR:** per `sprint-00.md` §8, extended in each sprint file (working-agreement §7).
- **Every sprint:** sprint-level DoD (`definition-of-done.md`); nightly differential oracle 0 disagreements (QD-QG-S1); mutation ≥ 85% on rules (from S2); flaky rate < 1%; test report and `status.json` up to date; retro with owned, dated actions [EP/ENG-15].
- **R1 release (S5):** release-level DoD; E2E journey green ≥ 5 consecutive nightly runs (QD-QG-S4); NFR-036 usability result; every R1-gate NFR in `non-functional-requirements.md` passing or covered by an accepted-risk ADR; zero `@needs-verification` rows in the scoring path **or** the "unofficial scoring" label (QD-QG-R3); PO sign-off; NFR-070 for real users.
- **R2 release (S9):** NFR-006 rally F1 ≥ 90%; NFR-008 band calibration; NFR-020 GPU cost; NFR-005 b, c coaching evals; model regression suites within the tolerances ADR; PO sign-off.

## 11. Re-planning rules

- Priorities stay stable inside a sprint; changes go through the PO [EP/ENG-22].
- A sprint that misses its goal is analysed with 5 Whys at the retro; the next sprint's load factor follows ADR 0010.
- If an external dependency in §8.1 misses its need-by date, the EM applies the fallback and records it as a dated note on ADR 0007, or a superseding ADR if the order changes.
- Each later sprint gets its own `sprint-NN.md` at planning, with the same sections as Sprints 0-2: goal, backlog with FR/NFR IDs and estimates, task breakdown per agent, TDD plan, integration tests, Gherkin scenarios, quality gates, DoD, demo script and retro link.

## 12. Actuals (updated at each sprint close)

The plan above is not rewritten; actuals are added here (engineering-manager). Sprints 0 and 1 both ran in compressed agent sessions on 2026-10-05, ahead of their calendar dates, so the calendar in §2 is still the review cadence with the PO.

| Sprint | Planned units | Implemented | DoD-done | Goal | Evidence |
|---|---|---|---|---|---|
| S0 | 28 | 19 (0.68) | 0 | Partly: walking skeleton local; no green CI | `docs/sprints/00/`, retro 0 |
| S1 | 32 (+1 stretch) | 29 (0.906) + 1 stretch | 0 | **Not met** (PO standing rule): scorecard round 3 met 10 of 12; G01-05 invalid below the disk floor, G01-11 17 open blocker/major | `docs/sprints/01/sprint-report.md` §1; `goal-scorecard.md` §8 |
| S2 | 46 (+8 stretch) | 45 (0.978) + 1 stretch (ST-028b) | 0 (nothing merged to `main`) | **Not met** (PO standing rule): verifier round 3 met 11 of 12 live; G02-11 open: verifier 2, close recount 14 (review-round-3 rows written at close) | `docs/sprints/02/sprint-report.md` §1; `goal-scorecard.md` §9; retro `docs/retros/2026-11-13-sprint-02.md` |
| S3 | 43 (+5 stretch stories) | 38.5 (0.895); stretch 0 | 0 (no Sprint 3 ticket PR; Sprint 1 + 2 reached `main` by PR #2 on 2026-10-06) | **Not met** (PO standing rule): verifier round 3 met 10 of 12 live at `fb920bc`; every player promise ran 5/5 in real time. G03-09 (c) no CI at the head; G03-12 open: verifier 3, close recount 8 (review round 3 reconciled at close) | `docs/sprints/03/sprint-report.md` §1; `goal-scorecard.md` §9; retro `docs/retros/2026-11-27-sprint-03.md` |

**Effect on the plan (judgment, for the PO at the 2026-10-30 review; changes go through the PO, §11):**
- **S2** starts with a carry-over of about 12 units: `sprint-02.md` §3 rows C-01..C-38, plus ST-013b, ST-042 and DR-01. At load factor 0.8 this takes about 1 lane-week out of the Quick Tag scope. The fallback, if the PO keeps the S2 scope, is to move the stretch stories ST-033 and ST-036 to S3.
- **Gates before any non-dev deployment** (staging, beta): ST-013b, ST-042, ST-038, S1-F2 and the ADR 0031 decision. They must be in place by the S5 R1 release candidate (2026-12-14). They are on the R1 critical path (§8.2).
- **External dependencies are unchanged:** OQ-01 rulebook PDFs need-by 2026-11-16 (S3 planning); OQ-05 legal review (US + AU) before any real-user beta; real phone clips for ST-025 before S2 planning (2026-11-02).
- **CI cadence:** run 37372059078 is the first run that includes the S1 fixes. Until D1 is decided, every sprint's DoD depends on the PO pushing and dispatching (retro 1 A1).

**Effect of Sprint 2 on the plan (engineering-manager, 2026-10-06, judgment; for the PO at the 2026-11-13 review, §11):**
- **S3 starts with a carry-over of about 5 units** (`docs/sprints/02/sprint-report.md` §8): the agent-owned blockers and majors QA-RV3-02, PE-S2-R3-01/-02/-03 and QA-RV3-04 first; the design reviews DR-01/DR-02 as scheduled decider-role tasks (ADR 0037); minors in the review-loop reserve; the stretch stories ST-034, ST-035, ST-038, ST-033 and ST-036 compete with S3 scope. ST-038 and ST-042 stay on the R1 critical path before any non-dev deployment.
- **Go port (PO decision 2026-10-06; ADR 0023 note):** **S6 becomes the Go port** of the whole product, tooling and tests, directly after the R1 release candidate (S5). Release 2 moves by one sprint: the outlines in §6 for S6-S9 now apply to **S7-S10**, and the R3 outline moves to S11-S13. The calendar in §2 is not rewritten; S6 planning updates it with the port ADR (principal-engineer).
- **External dependencies:** OQ-01 rulebook (P7) need-by stays S3 planning, 2026-11-16; P6 screen-reader tester 2026-11-13; new P10 (repository visibility: GitHub reports public) and P11 (private footage bucket provider, needed before any ST-040 recording).
- **Merge cadence:** S1 and S2 are both unmerged (PR #1 open), so DoD-done is 0 for two sprints. The merge chain (`sprint-02` → `sprint-01` → `main`) is retro 2 action A4, due 2026-11-13.

**Effect of Sprint 3 on the plan (engineering-manager, 2026-10-08, judgment; for the PO at the 2026-11-27 review, §11):**
- **S4 starts with a gate day and a carry-over of about 6 units** (`docs/sprints/03/sprint-report.md` §8): the Sprint 3 ticket PRs and their reviews (C4-PR, no build units but about one lane-day of review), CI green at the Sprint 3 head (C4-CI), the chair's DR-01/02/03 outcomes (C4-DR), the ADR 0045 security ITs (C4-SEC), the SRE remainder (Locust on stats/evidence, close smoke) and the minors. ADR 0047 makes the gate tasks (contract, design, threat notes, decider cells, BA-1 DoR check) day 1 of S4, before any build lane.
- **R1 critical path:** ST-038 and ST-042 are now implemented; together with deletion (ST-050/051) they still need to reach `main` as reviewed ticket PRs before any non-dev deployment. The R1 release candidate stays S5 (2026-12-14) if the S3 ticket PRs merge before S4's build starts (judgment).
- **External dependencies:** P7 rulebook (OQ-01) is still the only route out of "unofficial" stats; P11 footage bucket gates Full Tag on real matches; P10 visibility and P6 tester stay sprint-DoD rows (P12 b); P13 (start of the ticket-PR rule) is unanswered, so ADR 0039 applies.

