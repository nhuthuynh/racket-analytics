# PM-5 decisions

Per-ticket decision file (working-agreement §3, "Daily sync"). Ticket: PM-5, "Roadmap 'Product Goal' section; S5 priorities, out-of-scope, FR-162 recommendation" (`docs/sprints/sprint-05.md` §3). Owner: product-manager. Review tier 0 (ADR 0056). Gates ST-082 and EM-ESC-05. Everything here is team text (ADR 0047); items that need the PO are marked **PO** and routed to EM-ESC-05.

**TDD does not apply:** the ticket changes text and decisions only (`docs/sprints/roadmap.md`, this file); there is no executable behaviour to drive with a failing test. Doc checks run instead (PR description, "Test evidence").

## 1. Decisions

| Date | Role | Decision | Evidence | Reason |
|---|---|---|---|---|
| 2026-11-03 | product-manager | **Product Goal written** into `docs/sprints/roadmap.md` §"Product Goal" (unnumbered, before §1 so no section is renumbered): R1 = upload → plan in ≤ 15 min median, every number and drill traceable, PO sign-off. Measures table names the agent-measurable and the human-only (P9, P7, P16, P18) measures | `docs/sprints/sprint-05.md` §1 draft; roadmap §4 R1 exit criterion; NFR-036 (c), (d); FR-055, FR-101, FR-103, FR-122 | Role file: "`docs/sprints/roadmap.md` has no Product Goal yet: create a 'Product Goal' section there in your first planning ticket" (kickoff PM-1) |
| 2026-11-03 | product-manager | **The Product Goal restates, it does not change, the R1 exit criterion.** The S5 "Done when" change stays a PO question in EM-ESC-05 | kickoff PM-2 decision | A scope cut that changes a milestone's "Done when" is a PO decision (role file, escalation list) |
| 2026-11-03 | product-manager | **Story priorities confirmed** as planned in sprint-05 §3.5, with the order inside each band in §2 below | §2 | Stable priorities inside a sprint [EP/ENG-22] |
| 2026-11-03 | product-manager | **Out-of-scope list confirmed** (§3) and the roadmap S5 outline marked as replaced by `sprint-05.md` (same form as the S4 note) | roadmap §6 S5 | The outline still listed FR-162 as stretch and the R2 spikes as in scope |
| 2026-11-03 | product-manager | **FR-162 recommendation: option A** (§4). Roadmap §5 S5 row and §6 S5 outline no longer list FR-162 as stretch | §4 | — |

## 2. Story priorities (sprint-05 §3.5, "PM-5 confirms")

P0 = the gate for everything else; P1 = an R1 release-candidate gate; P2 = R2 readiness or a known coverage gap. Order inside a band is the order to protect when capacity runs short (judgment).

| Order | Story | Priority | Confirmed | Product reason (judgment unless cited) |
|---|---|---|---|---|
| 1 | PRC-05 Process rules enforced by checks | P0 | yes | CI FIRST (PO 2026-10-08); the tiers relieve review load for every later ticket. Capped at ≤ 40 % of units (kickoff PM-3; planned 29 %) |
| 2 | ST-082 R1 can be released and rolled back | P1 | yes, **release-notes part first** | P18 sign-off needs the release notes (REL-1.1) and the "unofficial scoring" notice (FR-055.R1). The rollback drill (REL-1.2) is the part that may slip (sprint-05 §2), the notes may not |
| 3 | ST-083 The usability test can run the day testers arrive | P1 | yes | The only Product Goal measure that decides R1 (NFR-036 c) waits on P9; the kit must be ready so P9 is the only wait |
| 4 | ST-080 Fixing a call is quick | P1 | yes | NFR-036 d is the one effort measure agents can prove |
| 5 | ST-077 Every stored datum has a class | P1 | yes | Privacy by default (spec §8); input to P16 |
| 6 | ST-078 R1 passes an ASVS L2 review | P1 | yes | Input to P19 and P18 |
| 7 | ST-076 Nothing a player corrected is lost | P1 | yes | A lost correction breaks trust in the score sheet |
| 8 | ST-075 We know when R1 is unhealthy | P1 | yes | Input to P17 |
| 9 | ST-079 R1 works on the phones players use | P1 | yes | Real devices wait on P20; emulation is the agent part |
| 10 | ST-074 R1 reads stay fast under load | P1 | yes | NFR-010 gate |
| 11 | ST-081 "Not for me" never dead-ends | P2 | yes, **first P2** | A dead end on the plan screen hits the last step of the value chain; it is small (0.5 BE + ≤ 6 drills) |
| 12 | ST-085 Offline and focus behaviour is tested | P2 | yes | Coverage gap, no new user value; slips first (sprint-05 §0.6) |
| 13 | ST-084 R2 entry is measurable | P2 | yes | R2 readiness; ST-084b slips before ST-084a (sprint-05 §0.6) |

No priority changes against the plan, so no re-plan is needed.

## 3. Out of scope for Sprint 5 (confirmed)

| Item | Why | Waits on / goes to |
|---|---|---|
| FR-162 pricing fake door (OQ-14) | §4 | **PO**: option A, R2 |
| SPIKE-02, SPIKE-03, SPIKE-05, SPIKE-07 | No footage bucket or GPU budget | P11, P8 |
| QD-GD-04 v1 vision gold-set freeze | No consented footage | P11 |
| Client-side usability instrumentation | The moderated test uses observation sheets (ST-083); instrumentation without testers yields no data | after P9 |
| The Go port | Its own sprint | S6 |
| Any real-user exposure (beta, testers' footage kept beyond the session) | NFR-070 legal gate | P16 |
| Official scoring presets | Rulebook not supplied | P7; R1 ships "unofficial scoring" (FR-055) |

## 4. FR-162 recommendation (pricing fake door)

- **Question (PO):** FR-162 is a Could for R1 (`docs/requirements/traceability-matrix.md`, "S5 (Could, stretch)"). OQ-14 was accepted on 2026-10-05 (ADR 0023): test freemium with a fake door, choose the model after MA-1/MA-2 data. Should the fake door ship in R1?
- **Evidence:** a fake door produces data only when real users click it. Real users wait on the NFR-070 legal review (P16), which is after S5 (roadmap §8.1). The "paid" side of the freemium split is automatic analysis, which first exists in R2 (roadmap §4). Sprint 5 SRE lane is at capacity (sprint-05 §2: 10 of 9.6 units).

| Option | What | Cost | Value | Risk |
|---|---|---|---|---|
| **A (recommended)** | Move FR-162 to R2: keep it Could, plan it in the first sprint where real users can reach the app (after P16) and automatic analysis exists to put behind the paid tier | none in S5 | data from real clicks, against a paid tier that exists | MA-1 signal comes later (judgment) |
| B | Build it in S5 as stretch behind a default-off flag | about 1 FE unit plus E2E (judgment), in a lane with 1.8 units of headroom | none until P16; the page would advertise a paid tier for a feature that does not exist yet | spends the review-loop buffer on a page no one can see |
| C | Drop FR-162 (Won't for MVP) | none | none | loses the cheapest monetisation signal (PROD MA-1); reopens OQ-14 |

- **Recommendation:** A. **Default if the PO does not answer by 2026-11-10:** A (nothing is built; the Could stays in the backlog). The PO may override with B or C.
- **What changes if A is accepted:** the BA moves FR-162 "Release: R1" to R2 in `functional-requirements.md` and the traceability matrix (BA ticket in the next planning); this ticket only changes the roadmap rows that listed it as S5 stretch.

## 5. Open product questions (owner)

| Question | Owner | Where |
|---|---|---|
| Accept the Product Goal wording (it restates the R1 exit criterion) | PO | EM-ESC-05 |
| FR-162: option A, B or C | PO | EM-ESC-05, §4 |
| S5 "Done when" change (human gates out of the sprint goal) | PO | EM-ESC-05 (kickoff PM-2) |
| R1 readiness recommendation for P18 | product-manager | RETRO-05, after VERIFY-05 |
| OQ-14 model choice after MA-1/MA-2 data | PO | open since 2026-10-05 |
