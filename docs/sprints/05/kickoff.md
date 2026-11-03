# Sprint 5 kickoff: feedback from every role and the EM's decisions

- **Held:** 2026-11-03 (working-agreement §3 planning step 1), read-only inputs from all 12 roles at `origin/main` `04c6a826`, after PRs #183-#185 merged (the PO's condition "start Sprint 5 once the PRs merge" is met).
- **Recorded by:** engineering-manager (ticket PLAN-05). Each role's full text is summarised here; "keep" and "lessons" items are listed by theme, every "change" item is listed with a decision: **Accepted → ticket/rule**, **Accepted (rule)**, **Deferred** (with owner and when) or **Rejected** (with a reason).
- **Not PO decisions.** Everything below is team text (ADR 0047). Items that need the PO are routed to EM-ESC-05.

## 1. What every role wants to keep (consolidated)

| Theme | Raised by | Kept as |
|---|---|---|
| Merge only through `merge_ready.py`, one at a time; 74 of 74 Sprint 4 PRs met the review rule (ADR 0050) | EM, PE, QA, SRE, ML, BE | sprint-05 §8 gate 1 |
| Gate tickets first (PE-4, SEC-4, COACH-4, PM-4 within 3 h; PD-4 before UI) | EM, PM, BA, PE, PD, ML, SEC, COACH | Wave 1 in sprint-05 §3.6 |
| Red-first as a separate commit, enforced by the `Red:` check (C4-RED) | EM, PE, BE, ML, SRE, QA | §5 TDD plan; DoD |
| CI FIRST with one root-cause ticket per incident | EM, SRE, SEC | CI-NOTICE-CANCELLED first |
| Evidence PRs always merged; verifier re-runs every method; observations to owners, not edits | EM, PM, QA, PE | scorecard §3 |
| Live dry-run of each method by its author (ADR 0055 rule 2) | all | scorecard §6, one row per metric |
| Per-ticket `decisions/<ID>.md`; no edits to shared status files | EM, BE | sprint-05 header |
| Human-only items as "not met: waiting on P-n" (P12 b) | PM, PD, ML, QA, COACH, SEC | scorecard §5 |
| Small fix-wave PRs (median 49 production lines, 1 CHANGES REQUESTED in 12) | PM, PE, BE, FE | ≈ 100-line slices in §3 |
| Test immutability and TCR rows decided by QA | QA, PE, FE | DoD |
| Threat rows as acceptance criteria; BOLA matrix; fail-closed controls | SEC, BE | SEC-5, ST-078d |
| Executable doc gates shown red first (check_flows.py, check_threat_notes.py, weakness_example.py) | PD, SEC, COACH | CI-DOC-CHECK reuses them |
| Shared E2E helpers, Gherkin-to-Playwright binding, root-cause fixes for WebKit | FE | ST-079, ST-078e |
| Evals as CI tests; pure deterministic domain core | ML, BE | G05-10 |
| `@needs-verification`, "unofficial scoring", "coach-reviewed" labels | PM, PD, COACH | FR-055.R1 |
| Delivery metrics reported, never targets [ASB/AGL-02] | EM | G05-11 |

## 2. Change items and decisions

### engineering-manager
| # | Change | Decision |
|---|---|---|
| EM-1 | Close the sprint once; RETRO only after VERIFY met the goal or every miss has a merged fix and dated re-measure | **Accepted → EM-CLOSE-CHECKS** (`retro_ready.py`, PRC-6.1) is RETRO-05's precondition. A second close triggers the ADR promised in retro 4 §12 |
| EM-2 | No VERIFY before the last build merge | **Accepted (rule)**: VERIFY-05 `depends_on` every build ticket (§15) |
| EM-3 | Dry-run every scorecard method live at planning, rc in §6 | **Accepted**: §6 has one row per metric, filled by the method's ticket; two planning dry-runs logged now. Methods for tools not yet built cannot be dry-run at planning; their row is a merge condition of the ticket that builds them |
| EM-4 | Every §8 gate gets a ticket | **Accepted**: SLO alerts ST-075c, 50 RPS ST-074, restore ST-076c, browser matrix ST-079, tiers CI-TIERS-a/b, doc-check CI-DOC-CHECK |
| EM-5 | CI-RECON-ON-PR in wave 1 | **Accepted → CI-RECON-ON-PR** (EM spec in the ticket, SRE code) |
| EM-6 | Apply WIP limits and record stage counts | **Accepted (rule)**: limits 4/3/2/1 (in-progress 4 per this sprint's brief, under §3's 5) |
| EM-7 | Cost per PR from the first ticket | **Accepted (rule)**: cost table in every decisions file (sprint-05 §9); QA-FLOW-METRICS checks completeness (PRC-5.5) |
| EM-8 | Tier ticket first; interim rule until it merges | **Accepted**: CI-TIERS-a/b in wave 1, depends only on CI-DOC-CHECK |
| EM-9 | Cut size-waivers by slicing at planning (~100 production lines) | **Accepted**: every ticket in §3 sized ≤ 400, most ≤ 150 production lines |
| EM-10 | Close checklist with set-difference and open-cause checks | **Accepted → EM-CLOSE-CHECKS** (PRC-6.2, PRC-6.3) |
| EM-11 | Fix the EM role file's "short bullet list" wording | **Deferred** to the PO answer on audit item 15 (EM-ESC-05); the plan follows working-agreement §3 (one sentence + bullet scorecard) |

### product-manager
| # | Change | Decision |
|---|---|---|
| PM-1 | Create the roadmap "Product Goal" section | **Accepted → PM-5** |
| PM-2 | Agent-measurable goal; human items as P12 rows; escalate the S5 "Done when" change | **Accepted**: goal in sprint-05 §1; the "Done when" change goes to the PO in EM-ESC-05 (not decided by the team) |
| PM-3 | Explicit process budget (about 40 % process, ≤ 60 % release readiness) | **Accepted**: 11 of 46 tickets are process (§2 capacity table: 5 CI-*, 4 QA, 2 EM-*); FR-162 out |
| PM-4 | PM/BA cells for other roles become tickets | **Accepted (rule)**: no "left to other roles" rows; BA-5, PM-5, COACH-5 own their follow-ups |
| PM-5 | Every product metric must be one the product can fail; dry-run before acceptance | **Accepted**: planted-failure column in scorecard §6 |
| PM-6 | Re-send the PO list with need-by dates and defaults | **Accepted → EM-ESC-05** (with PM-5) |

### business-analyst
| # | Change | Decision |
|---|---|---|
| BA-1 | No "Ready on condition"; Ready only when conditions merged | **Accepted (rule)**: §3.8 states "Not Ready: waiting on <ticket>" until the gate merges |
| BA-2 | Verification method is part of the requirement, linked to the §6 dry-run row | **Accepted**: `requirements-breakdown.md` names the method per item; BA-5 adds the matrix links |
| BA-3 | Constraint axes in acceptance criteria | **Accepted**: FR-124/FR-141 rules model players × equipment × weakness count |
| BA-4 | BA follow-up cells as dated tickets | **Accepted → BA-5** |
| BA-5 | Traceability updated inside each story, not at RETRO | **Accepted (rule)**: each ticket PR adds its matrix rows (DoD item) |

### principal-engineer
| # | Change | Decision |
|---|---|---|
| PE-1 | Apply tiers for real; hold Tier 0 reviews to correctness until enforced | **Accepted**: CI-TIERS-a/b first; interim rule in §8 |
| PE-2 | Review checklist adds config wiring, every flag on, method-to-CI-step | **Accepted (rule)**: in sprint-05 §8 reviewer checklist |
| PE-3 | Nits never flip a verdict | **Accepted (rule)** (working-agreement §6 labels) |
| PE-4 | Author-found gaps are findings; support E3 | **Accepted → CI-RECON-ON-PR** (PRC-4.2) |
| PE-5 | Every §8 gate has a ticket | **Accepted** (EM-4) |
| PE-6 | Cost per PR | **Accepted** (EM-7) |

### principal-designer
| # | Change | Decision |
|---|---|---|
| PD-1 | Gate = "DR held", not "flows merged"; close DR-04 | **Accepted → PD-DR04** (collect the 5 cells or a PO waiver); DR-05 cells are scheduled tasks in PD-5 with dates |
| PD-2 | `check_flows.py --decider` in CI | **Accepted → CI-DOC-CHECK** (PRC-3.4) |
| PD-3 | Chair re-reads all pending decider cells (DR-01..04) before the RC | **Accepted → PD-DR04** scope |
| PD-4 | Narrower, complete WCAG claim; rows for SC 3.2.6 and 3.3.7 | **Accepted → PD-5** (per-SC gap list); no WCAG conformance claim in the release notes |
| PD-5 | principal-designer verdict required on `web/src/app/**` | **Accepted as data in CI-TIERS-a** (UI path → required `principal-designer` verdict flag); enforcement in CI-TIERS-b only if it fits ≤ 400 lines, else a follow-up ticket (judgment) |
| PD-6 | Design PRs < 400 lines, one flows section per family | **Accepted (rule)** |

### senior-backend-engineer
| # | Change | Decision |
|---|---|---|
| BE-1 | Exported error-envelope schema plus contract test for harness stubs | **Deferred** to Sprint 6 (Go port contract tests) — the port re-states contracts anyway (judgment); ST-078d asserts `error.code` from the exported model where it touches errors |
| BE-2 | Flags-on pytest parametrisation fixture | **Accepted in QA-VERIFY04R5-01** (fixture lands with the flag-on demo fix) |
| BE-3 | Mutation gate per new domain module in the same PR | **Accepted (rule)**: DoD item; applies to the rally-F1 matcher (ST-084b) |
| BE-4 | Slice backend at ~100 lines; contract/schema separate | **Accepted**: ST-076b, ST-077, ST-078d are separate tier-2 slices |
| BE-5 | Known gaps as parseable id rows | **Accepted** (PRC-4.2) |
| BE-6 | Cost per PR | **Accepted** (EM-7) |

### senior-frontend-engineer
| # | Change | Decision |
|---|---|---|
| FE-1 | `android-chrome` Playwright project | **Accepted → ST-079** |
| FE-2 | Write down what emulation cannot prove for NFR-024 | **Accepted**: NFR-024.4/.5 are P20 rows |
| FE-3 | Opt-in WebKit run on draft PRs touching `web/` | **Deferred**: CI evidence of record stays the ready-PR run; the SRE assesses a `workflow_dispatch` in RETRO-05 if WebKit rounds repeat (owner sre-devops-engineer) |
| FE-4 | Split E2E-only work by journey at planning | **Accepted (rule)** |
| FE-5 | All flags on and all states in each FE ticket's DoD | **Accepted (rule)**: reviewer checklist line |
| FE-6 | Tier 2 includes senior-frontend-engineer for client security and auth UI | **Accepted as data in CI-TIERS-a** (`web/src/**/auth*`, service worker, CSP paths → specialist senior-frontend-engineer) |

### senior-ml-cv-engineer
| # | Change | Decision |
|---|---|---|
| ML-1 | Re-scope "R2 spikes have reported" to a P11/P8 row | **Accepted**: S5-P11, S5-P8 rows; escalated |
| ML-2 | ML gates get tickets (tolerance ADR, CI wiring) | **Accepted → ST-084a**; CI wiring of a regression eval waits for a model (S7) |
| ML-3 | ML tickets ≤ 400 production lines | **Accepted**: ST-084b is one metric |
| ML-4 | Dry-run eval methods on a real fixture | **Accepted (rule)**; matcher dry-run on the synthetic fixture now, real clip after P11 |
| ML-5 | Cost per PR | **Accepted** |
| ML-6 | Route `worker/`, `dataset/`, eval PRs to the ML reviewer in tier 1 | **Accepted as data in CI-TIERS-a** (specialist flag); review routing by the orchestrator |

### senior-qa-engineer
| # | Change | Decision |
|---|---|---|
| QA-1 | Tier tests: tier 1 without QA on head fails; tier 0 passes with one reviewer + doc-check | **Accepted → CI-TIERS-b** (PRC-2.4, PRC-2.5); QA writes the acceptance scenarios first (writer/reviewer split) |
| QA-2 | Close findings on the PR that fixes them | **Accepted → CI-RECON-ON-PR** |
| QA-3 | Parseable finding ids in every brief | **Accepted** (PRC-4.3; scorecard §3 rule 4) |
| QA-4 | rc 0 dry-run per method before acceptance | **Accepted** (EM-3) |
| QA-5 | "Configurations exercised" line in every verdict | **Accepted (rule)**: §8 reviewer checklist |
| QA-6 | One verdict per head; no CHANGES REQUESTED over wording | **Accepted (rule)** |
| QA-7 | TCR rows decided within one working day; none Pending at a close | **Accepted → QA-TCR-04** first; close check item |

### security-privacy-engineer
| # | Change | Decision |
|---|---|---|
| SEC-1 | Tier 2 by changed paths, security APPROVE required on the head | **Accepted → CI-TIERS-a/b** (PRC-2.3, PRC-2.6); tier label owned by the PR-policy step, never the author |
| SEC-2 | Security review has a slot in the orchestrator's fan-out | **Accepted (rule)**: tier 2 brief lists the security reviewer by name |
| SEC-3 | "Accepted residual" stays open until a human ADR covers it | **Accepted → SEC-5** (check_threat_notes.py requires an ADR id) and P19 |
| SEC-4 | ASVS checklist as a living artifact | **Accepted → ST-078a-c** (per-chapter assessment) and DoD line "name the ASVS rows a security ticket moves" |
| SEC-5 | Security reviewer checks config parity and flag-on runs | **Accepted (rule)** |

### sre-devops-engineer
| # | Change | Decision |
|---|---|---|
| SRE-1 | Cancelled or timed-out scheduled run = red | **Accepted → CI-NOTICE-CANCELLED**, `ci_fix`, first |
| SRE-2 | Flow metrics through REST; fix working-agreement §10's GraphQL command | **Accepted → QA-FLOW-METRICS** (QA owns `scripts/measure`); the one-line §10 fix rides in that PR |
| SRE-3 | CI-RECON-ON-PR in week 1 | **Accepted** |
| SRE-4 | Every §8 gate has a ticket | **Accepted** |
| SRE-5 | Warning at 80 % of each CI budget | **Deferred**: folded into `run_with_budget.py` only if CI-NOTICE-CANCELLED's root cause is a budget creep; otherwise a Sprint 6 ticket (owner sre-devops-engineer, decided at RETRO-05) |
| SRE-6 | Doc-check before or with the tier change | **Accepted**: CI-TIERS-b depends on CI-DOC-CHECK |
| SRE-7 | Stack creator owns teardown; `df -h /` in decisions | **Accepted (rule)** |

### pickleball-domain-coach
| # | Change | Decision |
|---|---|---|
| COACH-1 | The single-weakness / 3+-drill "Not for me" gap is a finding with a ticket | **Accepted → ST-081a/b**; ledger row `COACH-S5-01` written by COACH-5 |
| COACH-2 | Domain verdict enforceable in tiers | **Accepted as data in CI-TIERS-a** (`content/drills/**`, `docs/domain/**`, rules engine, coaching copy → specialist pickleball-domain-coach) |
| COACH-3 | How drill JSON counts for PR size | **Accepted (rule)**: drill tickets sliced at ≤ 6 drills per PR (ST-081b); a change to ADR 0054's exclusions is a PO question, listed in EM-ESC-05 |
| COACH-4 | Escalate P7 and P15 with explicit fallback | **Accepted → EM-ESC-05** (COACH-5 drafts the fallback request) |
| COACH-5 | Track the FR-120 wording note from COACH-4 | **Accepted → BA-5** (closes it or opens a row) |
| COACH-6 | Coach dry-runs every domain-content method | **Accepted** (only G05-09's notice check touches domain content this sprint) |

## 3. Lessons stated at kickoff (one per role; each maps to a ticket or rule)

| Role | Lesson | Maps to |
|---|---|---|
| engineering-manager | A task with no slot in the workflow does not run | Every gate/cell is a ticket (§3) |
| product-manager | A known gap is a product decision at that moment | ST-081, PRC-4.2 |
| business-analyst | An NFR's "how measured" is part of the requirement | `requirements-breakdown.md` |
| principal-engineer | Stubs must come from the real contract | DoD line; BE-1 deferred |
| principal-designer | A design gate is "merged AND held" | PD-DR04, PD-5 |
| senior-backend-engineer | A setting is done only when wired to Compose and run | DoD parity line |
| senior-frontend-engineer | Test SW logic at unit level; E2E only what the browser can show | ST-078e, ST-085 |
| senior-ml-cv-engineer | A passing eval does not prove strong tests | mutation rule for ST-084b |
| senior-qa-engineer | I am late on TCR rows 11 and 14 | QA-TCR-04 first |
| security-privacy-engineer | A security test never seen failing proves nothing | planted-failure column |
| sre-devops-engineer | Anything that must happen without a session belongs in a workflow | CI-NOTICE-CANCELLED |
| pickleball-domain-coach | Coverage rules must list every filter axis | FR-141.R1 |

## 4. Risks raised (consolidated) → sprint-05 §10.

## 5. Open PO questions carried into EM-ESC-05

Audit items 12 (which skills: default (a), the installed product-management skills, used at this planning), 13 (deny rules and a merge hook; QA by name in `merge_ready.py` — CI-TIERS-b implements the QA-by-name part as ADR 0056 decision 2 already requires), 14 (commands-only CLAUDE.md), 15 (goal format); the S5 "Done when" change; P6, P7, P8, P9, P10, P11, P15, P16, setting 6; new P17-P20; drill JSON in the size count.
