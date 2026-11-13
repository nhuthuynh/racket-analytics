# PM-6 decisions

Per-ticket decision file (working-agreement §3, "Daily sync"). Ticket: PM-6, "Product Goal re-scope, pattern priority waves A/B/C, out-of-scope list, product metrics the slice can fail" (`docs/sprints/sprint-06.md` §3.2, wave 1 gates). Owner: product-manager. Review tier 0 (ADR 0056). Everything here is team text (ADR 0047); items that need the PO are marked **PO** and go to EM-ESC-06.

**TDD does not apply:** the ticket changes text and decisions only (`docs/sprints/roadmap.md` §"Product Goal", this file); there is no executable behaviour to drive with a failing test. The product metrics in §4 are measured by existing scorecard rows whose tickets write the red tests (ST-170a, ST-172a/b, ST-173a, ST-174b). Doc checks run instead (PR description, "Test evidence").

## 1. Decisions

| Date | Role | Decision | Evidence | Reason |
|---|---|---|---|---|
| 2026-11-13 | product-manager | **Product Goal re-scoped** in `docs/sprints/roadmap.md` §"Product Goal" for the video-analysis slice: own play vs a versioned, cited reference set; gaps with n and an interval; drills with a cited Why | `docs/sprints/sprint-06.md` §1 draft; kickoff PM-2 (accepted → PM-6); PO instruction 2026-11-12 (`docs/requirements/po-input-2026-10-05.md`, addendum "Video analysis (PO 2026-11-12)") | Role file: keep the Product Goal current at each sprint planning |
| 2026-11-13 | product-manager | **The R1 Product Goal is kept, not replaced**, as an open goal until P18; its measures table moves verbatim to §5 | roadmap §4 R1 exit criterion; PM-5 | R1 is not signed off; dropping its measures would hide P9, P7, P16, P18 (judgment) |
| 2026-11-13 | product-manager | **No milestone "Done when" changes; §2, §4 and §7 are not renumbered.** The S6/S7 order is P21; the renumbering waits for the answer | sprint-06 §0 ("not a PO decision"); kickoff PM-2 | A change to a milestone's "Done when" is a PO decision (role file, escalation list) |
| 2026-11-13 | product-manager | **Pattern priority waves A/B/C** (§2) | sprint-06 §3.3 priorities; requirements-breakdown data-source axis | Value first from data that exists today (judgment); NFR-006 and roadmap §7.1 for wave C |
| 2026-11-13 | product-manager | **Out-of-scope list** confirmed (§3) | sprint-06 §1 "Out of scope"; PLAN-06 brainstorm "Parked" | — |
| 2026-11-13 | product-manager | **Three product metrics the slice can fail** (§4), each mapped to a G06 row; no new scorecard row | `docs/sprints/06/goal-scorecard.md` G06-01, G06-03, G06-04 | The scorecard changes only through its own rule; the metrics already have methods and planted failures |

## 2. Pattern priority waves

The waves order patterns, not tickets (the sprint's work waves 0-3 are a separate thing, sprint-06 §3.6). Order inside a wave is the order to protect when capacity runs short (judgment).

| Wave | Pattern | Data source | Tickets | Product reason (judgment unless cited) |
|---|---|---|---|---|
| A | AN-04 unforced errors per game | Quick Tag | ST-171a, COACH-6c | Every R1 match already has it; the demo works even without Full Tag |
| A | AN-05 serve fault % | Quick Tag | ST-171a, COACH-6c | Simple, high-count proportion; Wilson interval narrows fast (FR-171.R1) |
| A | AN-07 rally-ending mix | Quick Tag | ST-171a, COACH-6c | Links to the existing ADR 0003 rallies-lost ranking the player already sees (FR-172.R5) |
| B | AN-09 third-shot drop vs drive share | Full Tag (`trajectory` facet) | ST-171b, COACH-6b, ST-173c | The first "pro pattern" from the PO's list; needs Full Tag labels, which only the team makes today (A3) |
| B | AN-13 dink-rally tolerance | Full Tag | ST-171c, COACH-6b, ST-173c | Second pattern from the PO's list; min_n ≥ 6 makes it rankable less often (FR-171.R4) |
| stretch | AN-08 return depth | Full Tag (`court_xy_m`) | ST-171d (P2) | Slips first; outside waves A and B |
| C | Kitchen-line arrival and transition; partner spacing and stacking; serve and return depth from ball tracking; any pose-derived pattern | Computer vision | none Ready; ST-176a/b prepare the eval and spike plans | Waits on the roadmap §7.1 gates measured on footage (P11); pose is personal data (tier 2, P16) |

**Rule:** a wave B pattern is not shown before wave A works end to end on the demo stack; a wave C pattern is not planned before its §7.1 gate passes on a committed eval report.

## 3. Out of scope for the video-analysis slice (Sprint 6)

| Item | Why | Waits on / goes to |
|---|---|---|
| Automatic CV in the user path (calibration, tracking, ball, pose) | No accuracy measured; no CV story is Ready (roadmap §7.1, NFR-006) | P11 footage → spikes → §7.1 gate |
| Scraped pro footage (broadcast, YouTube or any video without a licence) | No rights; FR-174.R1 refuses an asset without a provenance record | P11 (licensed footage) |
| LLM-written Why | The Why is template text from cited fields (FR-173.R2); the coaching AI is a workflow over a curated library [DPA/AI-01, AQS/AI-01] | R2 (roadmap §6 S11) |
| Opponent scouting | Not in the PO's 2026-11-12 instruction; a separate job (functional-requirements §J) | later backlog |
| Pose tracking on real people | Personal data; spike plans only (ST-176b) | P11, P16 |
| A player-facing Full Tag | Needs a new FR (A3) | **PO**, EM-ESC-06 |
| n-gram patterns (FR-108) | Parked at PLAN-06 brainstorm | later backlog |
| The Go port | S7 if P21 confirms | **PO**, P21 |
| Any real-user exposure | NFR-070 legal gate; flags default-off | P16 |
| Payments, pricing fake door (FR-162) | PM-5 option A (R2) | after P16 |

## 4. Product metrics the slice can fail

Each metric is agent-measurable on the live local stack and has a planted failure in its G06 method. A metric below target means the Product Goal is not met for this slice, whatever else passes.

| ID | Metric | Target | G06 row | Fails when (planted case) |
|---|---|---|---|---|
| PM6-M1 | Reference values with provenance (source_type, resolvable source id, status, version) | 100 % of entries; 0 "pro" labels without a pro source | G06-01 | an entry with no source or an unresolved citation passes the lint |
| PM6-M2 | Listed gaps with n and an interval | 100 % of listed patterns; 0 ranked with n < min_n or overlapping intervals | G06-03 | a low-n or overlap fixture is ranked as a weakness |
| PM6-M3 | Recommended drills with a cited Why (pattern id, value, n, interval, reference id, version, status) | 100 % of recommended drills | G06-04 | a Why without the reference version is accepted |

```gherkin
Feature: The video-analysis slice is honest about what it knows
  Scenario: Every value a player sees can be traced
    Given the demo stack with reference set v1 and demo player A
    When player A opens the weakness view and the plan
    Then every reference value shows its provenance label, status and version
    And every listed pattern shows n and an interval or a "not enough data" state
    And every recommended drill's Why cites the pattern, the player's value and the reference
```

The scenario is executed by ST-174b (@critical journey); this ticket writes no test.

## 5. R1 measures (moved verbatim from the roadmap, PM-5)

| Measure | Target | Method | Who can measure it |
|---|---|---|---|
| Median effort, upload → plan, 3-game match (NFR-036 c) | ≤ 15 min | Moderated usability test, ≥ 5 players on their own phones | Human: waits on **P9** (scorecard row S5-P9) |
| Taps or keys to fix any call from where it is seen (NFR-036 d) | ≤ 2 | E2E | Agent (G05-05) |
| Every metric shows n, an uncertainty band and its evidence rallies (FR-101, FR-103) | 100 % of metric cards | E2E and integration tests | Agent |
| Every drill in a plan says why, with a linked metric (FR-122) | 100 % of plan drills | Plan eval at pass^3 = 100 % (NFR-005a) | Agent |
| Score sheet says "unofficial scoring" until the rulebook is verified (FR-055) | label present while OQ-01 is open | E2E; release notes check (ST-082) | Agent; official scoring waits on **P7** |
| Real users only after the legal review (NFR-070) | no real-user exposure before the ADR | flags default-off | Human: **P16** |
| R1 release-candidate sign-off (release-level DoD) | PO accepts | PM readiness recommendation after VERIFY-05 | Human: **P18** |

## 6. Open product questions (owner)

| Question | Owner | Where |
|---|---|---|
| Confirm S6 = video analysis, Go port in S7; then renumber roadmap §2, §4, §7 | PO (P21); product-manager and engineering-manager renumber after the answer | EM-ESC-06 |
| Licensed pro footage and consented training footage | PO (P11) | EM-ESC-06 |
| Coach verification of reference values (`verified`) | PO (P15) | EM-ESC-06 |
| Player-facing Full Tag (A3), which would let wave B reach real players | PO | EM-ESC-06 |
| Accept this Product Goal wording | PO | EM-ESC-06 |

## Cost per PR (ADR 0056 decision 1)

| Round | wall_time_min | total_cost_usd | Note |
|---|---|---|---|
| Author build | not measured | not measured | the session does not expose per-ticket wall time or cost to the agent |
