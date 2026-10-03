# Review Log: adversarial review of docs/ and .claude/agents/

- **Date:** 2026-10-03
- **Reviewer:** principal-engineer (adversarial, fresh context), using the senior-qa-engineer lens
- **Scope:** everything under `docs/` and `.claude/agents/`.
- **Checks run:**
  - Requirements that cannot be measured or tested.
  - FRs and NFRs missing from the traceability matrix or sprint plan.
  - Sprint 0-2 overcommitment and sequencing.
  - Rules scenarios checked against `docs/research/domain-pickleball-cv.md` G1.
  - Citations to source IDs that do not exist or are unverified.
  - ADR evidence.
  - Agent definitions that contradict the process docs.
- **Severity labels:** Blocking (fixed in place) and Non-blocking (recorded only), per working-agreement §6 [EP/ENG-06].

## Checks that found no defect

These were checked and are recorded with evidence, so nobody needs to redo them.

| Check | Method and evidence | Result |
|---|---|---|
| Citation IDs exist | A script matched every `EP/`, `AQS/`, `DPA/` and `DOM/` citation (ranges included) in `docs/**` and `.claude/agents/**` against the ID registers of the four research files | 0 unknown IDs |
| Unverified sources cited as evidence | The same script listed every citation of DOM/DOMAIN-01..08, which the research file marks "no" | 17 citations, all explicitly labelled "unverified" or used only to ask for the source. None is cited as evidence |
| FR/NFR coverage in the matrix | Compared the `#### FR-nnn` headings and NFR table IDs with the IDs in `traceability-matrix.md` | All 83 FRs and 82 NFRs are present, and none is orphaned. Every FR has a Gherkin block. No R1 Must FR or R1-gate NFR is scheduled after S5 |
| Rules tables vs DOM G1 R2-R6 | Hand-checked SOD-01..16, F-01..06, the SOS rows, SOD-13..15 (declared starts), the FR-041..046 scenarios and properties P1-P9 against R2 (only the serving side scores; 11, win by 2), R3 (rally-scoring game point), R4 (two-bounce), R5 (NVZ) and R6 (0-0-2 start, three-number call, right court when even) | No contradiction. Every row is tagged `@needs-verification` or is mechanics under ADR 0009. Note that R2-R6 are themselves UNVERIFIED [DOM G1] |
| Sprint 0-2 capacity | Re-added the sized stories per lane (XS 0.5, S 1, M 2, L 4) | S0: BE 8, FE 4, QA 5, SRE 8, ML 3. S1: BE 12, FE 12, QA 4, SRE 2, ML 2. S2: BE 12.5, FE 12.5, QA 4, SRE 1, ML 2. These match the plans and stay within the ADR 0010 capacity (11.2 / 12.8 per lane) |
| CV work in Sprints 0-2 | Reviewed sprint-00..02 | No sprint builds on CV accuracy. ML work is the probe stage, licences, fixtures and the label schema only |
| ADR evidence | Every ADR 0001-0010 has an Evidence table with typed claims | Present. Unverified domain claims are typed as such (ADR 0003) |

## Blocking findings and fixes

### RL-01. FR-040 used a federation-named preset that ADR 0009 forbids

- **Issue:** FR-040's Gherkin asserted that a match "was scored under `USAP-2026`".
  - ADR 0009 rule 4 says no preset may be named after a federation until every row it relies on is verified.
  - NFR-003 requires the same before any official `rules_version` is claimed.
  - Sprint 1's scenario already uses `PROVISIONAL-UNVERIFIED`. The requirement and its test therefore disagreed.
- **Evidence:**
  - `functional-requirements.md` FR-040.
  - ADR 0009 "Rules for applying it" item 4.
  - `sprint-01.md` §7.7.
  - [DOM G1]: no rule is verified.
- **Fix:**
  - The FR-040 scenario now uses `PROVISIONAL-UNVERIFIED`.
  - The FR-040 description says `USAP-2026` may ship only after verification.
  - The coach agent's "pin the edition" line now says the same.

### RL-02. FR-050 required behaviour that R1 cannot provide, and disagreed with the Sprint 2 test

- **Issue:** FR-050 (R1, Must) said: "the video moves to where rally 8 starts".
  - R1 has no automatic rally segmentation (that is FR-087, R2), so the step cannot be tested in R1.
  - Sprint 2's executable scenario already asserted something else: "the video continues from the end of rally 7".
  - The question was left as an open "BA clarification".
- **Evidence:**
  - FR-050 Gherkin.
  - `sprint-02.md` §3.1 ST-027 and §7 (line "the video continues from the end of rally 7").
  - The roadmap places FR-087 in S8.
- **Fix:**
  - FR-050 now states the R1 behaviour and points to FR-087 for R2.
  - `sprint-02.md` refers to this fix. The BA task is now "confirm with the PO" instead of "clarify".

### RL-03. CV stories could be committed on accuracy that had not been validated

- **Issue:** the thresholds disagreed.
  - NFR-006 sets the R2-entry ball F1 at ≥ 80%.
  - The roadmap's SPIKE-02 and RM-08 escalated only below 70%.
  - So with a measured F1 of 70-80%, S7 would commit FR-084..086 without meeting NFR-006, and nothing said what to do.
- **Further gaps:**
  - There was no explicit gate at S6 planning for calibration (SPIKE-07) or for tracking HOTA.
  - There was no rule for S8 when rally F1 is below 90%. Rally boundaries could be pre-filled as fact before the target is met.
- **Evidence:**
  - NFR-006.
  - `roadmap.md` §7 SPIKE-02 and §9 RM-08.
  - ENG §5.4 CV-T01..T09 and §8 SPIKE-02.
  - Make clear how well the system can do what it does [DPA/DESIGN-11] G2.
- **Fix:**
  - Added `roadmap.md` §7.1, "CV go/no-go gates", with pass, partial and fail paths per sprint, all tied to NFR-006 values and a committed eval report.
  - Aligned SPIKE-02 and RM-08 with it.
  - The fail cut-offs other than ENG's 70% are labelled (judgment).

### RL-04. NFR-001's "8 M rows" were not planned anywhere, and ADR 0009's Sprint 1 count could not be reached

- **Issue 1:** the M rows.
  - NFR-001 requires 100% of ≥ 46 rows, including 8 match-level (M) rows.
  - QD §2.2 described the M rows only in prose.
  - `sprint-01.md` §7.10 had 3 scenarios, and no later sprint added more.
  - The "8 M" part of an R1 gate therefore had no test.
- **Issue 2:** the count in ADR 0009.
  - ADR 0009 expected "≥ 30" provisional rows in the Sprint 1 report.
  - Sprint 1 actually holds SOD-01..12, SOD-16 and F-01..06, which is 19 rows, because SOD-13..15 moved to Sprint 2.
  - ST-023 still said "SOD-01..16".
- **Evidence:**
  - NFR-001.
  - QD §2.2 "Match level".
  - `sprint-01.md` §3, §7.8, §7.10.
  - `sprint-02.md` ST-041.
  - ADR 0009 "Confirmation".
- **Fix:**
  - Enumerated M-01..M-08 in QD §2.2.
  - Rewrote `sprint-01.md` §7.10 as `Scenario Outline`s covering all 8 rows.
  - Corrected the ST-023 row ranges.
  - Corrected the ADR 0009 confirmation count. That ADR is Proposed, so it can still be edited.
  - Added FR-045 and `match_structure.feature` to the matrix row for ST-023.
- **Judgment:** the M rows take format, first server and end switch as explicit inputs, so they are classed as ADR 0009 part (a) mechanics.

### RL-05. The testing strategy contradicted the requirements on BOLA responses and on M2/M3 accuracy

- **Issue 1: BOLA responses.**
  - testing-strategy §5 accepted "403/404" for another user's resource.
  - FR-002 and NFR-051 require exactly 404, the same as for a missing resource. A 403 leaks that the resource exists.
- **Issue 2: M2/M3 accuracy.**
  - testing-strategy §6 used the spec's untestable wording: "≥ 90% … segmented correctly" and "≤ 1 correction per game".
  - The DoD release example did the same.
  - NFR-006, NFR-007 and ADR 0004 define measurable versions.
- **Evidence:**
  - FR-002.
  - NFR-051 ("responses other than 404 for user B: 0").
  - [AQS/SEC-09].
  - ADR 0004.
  - NFR-006 and NFR-007.
- **Fix:**
  - Section 5 now says 404 only.
  - The §6 rows and the DoD example now point to the NFR-006 and NFR-007 definitions. They are marked as pending ratification of ADR 0004 (OQ-09).

### RL-06. Performance tooling contradicted Accepted ADR 0008

- **Issue:**
  - ADR 0008 (Accepted) chose Locust because k6's licence file is AGPL-3.0. It also states that testing-strategy §2 "is amended … to Locust".
  - testing-strategy §2 still said "k6/Locust".
  - NFR-010 (R1 gate) said "P (k6)", and so did the matrix.
  - The NFR test-level key said "k6/Locust".
- **Evidence:**
  - ADR 0008, decision D and its Evidence table (fetched licence files).
  - NFR-062: no AGPL component without an ADR.
- **Fix:** replaced k6 with "Locust (ADR 0008)" in testing-strategy §2, in the NFR register (the key and NFR-010) and in the matrix row for NFR-010.

### RL-07. The ADR index was incomplete

- **Issue:** the index in `docs/decisions/README.md` listed only ADR 0001. ADRs 0002-0010 exist. The EM is accountable for a complete decision log (working-agreement §4, §9).
- **Fix:**
  - Added rows for 0002-0010 with their current statuses.
  - Linked this review log from the README.

### RL-08. Agent definitions contradicted the process docs

- **Issue 1: the BA agent.**
  - It said every pickleball-rules requirement is "BLOCKED".
  - But Sprint 0 tasks the BA with writing (a)/(b) split rules stories under ADR 0009.
- **Issue 2: the domain coach.**
  - Its DoD had no exception for part-(a) stories.
  - It used `USAP-2026` as the example `rules_version`.
- **Issue 3: plan file paths.**
  - The EM and PM agents named `docs/sprints/<nn>/plan.md` as the sprint plan.
  - The real plans are `docs/sprints/sprint-<nn>.md` (roadmap §11). Following the agent files would have produced duplicate plans.
- **Evidence:**
  - `business-analyst.md` responsibilities.
  - `pickleball-domain-coach.md` DoD.
  - `engineering-manager.md` and `product-manager.md` outputs.
  - `sprint-00.md` §4.
  - ADR 0009.
- **Fix:**
  - BA and coach: added the ADR 0009 conditional. Part (a) is allowed only once ADR 0009 is ratified, and there is no federation-named preset before verification.
  - EM and PM: corrected the plan path.

## Non-blocking (recorded, not changed)

- **Sprint 5 is overloaded (judgment).** It is shortened to 7 working days and carries the usability test, SLOs and alerts, the restore drill, performance gates, the ASVS L2 review, the legal gate, five R2 spike ADRs and a frozen gold set. Re-plan it at S4 planning. It is outside the Sprint 0-2 scope of this review.
- **The DoD "Domain" item still reads literally.** It says every rule used must be verified, and ADR 0009 interprets it. When ADR 0009 is ratified, append a dated note to the DoD.
- **ADR 0001's status is internally contradictory.** It reads "Accepted (pending ratification …)". The PO ratifies it at the S0 review; the status should then be set plainly.
- **QA load in Sprint 1 and Sprint 2 is only 4 units.** The QA agent also writes acceptance scenarios for every story first, and that work is not sized. Track it in `status.json` and recalibrate at retro 0 (ADR 0010).
- **The NFR-034 success criteria (SC 2.1.1, 1.4.1, 1.4.10, 4.1.3) are still unfetched.** They are already labelled (judgment) in the NFR register. QA must check the W3C text before these become gates.
