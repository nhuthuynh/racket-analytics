# Sprint 6 kickoff: feedback from every role and the EM's decisions

- **Held:** 2026-11-13 (working-agreement §3 planning step 1), read-only inputs from all 12 roles at `origin/main` `e7ed7d9d` (merge of #240). Sprint 5 is **not closed** at kickoff: no `docs/sprints/05/sprint-report.md` (planned), no VERIFY-05, no RETRO-05, 13 open PRs. Every role used retros 3 and 4 as "the last two retros", plus the Sprint 5 ledger, scorecard and decisions files as the latest evidence.
- **Recorded by:** engineering-manager (ticket PLAN-06). "Keep" and "lessons" items are listed by theme; every "change" item is listed with a decision: **Accepted → ticket**, **Accepted (rule)**, **Routed to the PO** (EM-ESC-06), **Deferred** (owner and date) or **Rejected** (reason).
- **Not PO decisions.** Everything below is team text (ADR 0047). In particular, **the orchestrator note "Sprint 6 becomes the first video-analysis sprint and the Go port moves to Sprint 7" is confirmed here by the team, not by the PO.** All 12 roles accept it as the working plan; the principal-engineer and the business-analyst record that it conflicts with "Port the product to Go (PO decision 2026-10-06)" ("before any computer-vision work"), and the security-privacy-engineer accepts it only for synthetic, consented or rights-cleared footage with pose as High-class personal data. It goes to the PO as P21 in EM-ESC-06.

## 1. What every role wants to keep (consolidated)

| Theme | Raised by | Kept as |
|---|---|---|
| Merge only through `merge_ready.py` on the head SHA, one at a time; tiered verdicts (57 of 57 in retro 4) | EM, PE, QA, SRE, FE | sprint-06 §8 gate 1 |
| CI FIRST as a sequenced step; one root-cause ticket per incident, gates never loosened (#230, #232, #235) | EM, PM, BE, SRE | wave 0; CI-SCHEDULED-RED |
| Gate tickets first (COACH, SEC, PE, PD before builds) | EM, PE, PD, COACH, ML | wave 1 (§3.2) |
| Red-first checked by C4-RED; TCR rows decided by QA; no test weakened | EM, PE, BE, FE, QA | §5, DoD |
| Live dry-run of every method with a planted failure (ADR 0055 rule 2) | all | scorecard §6 |
| Human-only items as "not met: waiting on P-n" rows, never agent proxies | all | scorecard §5 |
| Per-ticket decisions file; no edits to shared status files | EM, BA | sprint-06 header |
| Atomic breakdown format of Sprint 5, enforced by QA-DOR-CHECK | PM, BA, PE, QA | `requirements-breakdown.md` (check rc 0) |
| Versioned, linted, locked content (drills) as the model for the reference library | PE, ML, COACH | ST-170a |
| Pure domain modules behind an ACL; coaching architecture rules → plan → validator | PE, BE, ML | ST-171a-c, ST-172a, ST-173a |
| Status ladder and labels (`@needs-verification`, `coach-reviewed`, "unofficial scoring") | PM, COACH | FR-170 status ladder |
| ADR 0015 licence posture, ADR 0060 eval contract, roadmap §7.1 gates | ML, SEC, QA | ST-175b, ST-176a, NFR-006 items |
| Data classification with an executable check (IT-05-05) | SEC, BE | NFR-063.3-.4 |
| Env-to-Compose parity test; `make up` + `make demo` as the acceptance surface | SRE, BE | ST-174a |
| State tables with low-sample and low-confidence states; FR-122 Why contract | PD, FE | PD-6, ST-172c, ST-173d |
| Small slices (fix-wave median 49 production lines) | PE, BE | ≈ 100-line tickets |

## 2. Change items and decisions

### engineering-manager
| # | Change | Decision |
|---|---|---|
| EM-1 | Close Sprint 5 first (drain wave, VERIFY-05, RETRO-05); PO to confirm the order | **Accepted (rule)**: entry condition E1 (sprint-06 §3.6 item 2); docs gates may run in parallel. The order matches "resume sprint 5"; EM-ESC-06 reports it to the PO, no decision needed |
| EM-2 | Enforce WIP limits instead of recording them | **Accepted → QA-WIP-GATE** (PRC-12.1) |
| EM-3 | Make the Go-port move explicit, quote verbatim, push old S7 to S8 | **Accepted**: po-input addendum "Video analysis (PO 2026-11-12)" with a separate "not a PO decision" note; roadmap §5/§6 re-planned in this PR; **P21** in EM-ESC-06 |
| EM-4 | Slice by data source (QT / FT / CV / UI) | **Accepted (rule)**: breakdown header "Data source axis"; stories ST-171 (QT, FT), ST-176 (CV prep), UI tickets separate |
| EM-5 | Disk and worktree owner step | **Accepted → OPS-DISK-06**; worktree removal in DoD |
| EM-6 | Cap process work at ≈ 20 % | **Accepted with a note**: 22 % of tickets, 25 % of units; the excess is the two ADR 0056 required tickets and the WIP gate (sprint-06 §2) |

### product-manager
| # | Change | Decision |
|---|---|---|
| PM-1 | Close Sprint 5 before committing capacity | **Accepted (rule)**: E1, 25 % capacity reserve |
| PM-2 | Rewrite the Product Goal and roadmap §5-§6; S6 "Done when" to the PO | **Accepted → PM-6** (Product Goal) and this PR (roadmap §5-§6, labelled orchestrator proposal); the "Done when" change is part of P21 |
| PM-3 | Name the pro reference honestly ("coach-authored, sources pending") | **Accepted (rule)**: FR-170.R5 label; scorecard honesty rule |
| PM-4 | Provenance axis on every pattern; no source → never reaches a user | **Accepted → ST-170a** (FR-170.R1, R4) |
| PM-5 | Escalations on day 1 with need-by and defaults; say that P7/P15 defaults apply | **Accepted → EM-ESC-06** (sent by 2026-11-14) |
| PM-6 | ≥ 60 % of the sprint on the slice | **Accepted**: 73 % of tickets (sprint-06 §2) |

### business-analyst
| # | Change | Decision |
|---|---|---|
| BA-1 | New FR group FR-170.., not stretching FR-107/108 | **Accepted → BA-6** (FR-170..FR-174) |
| BA-2 | Term mapping first; Exercise = drill assignment; context owner by ADR | **Accepted → BA-6** (glossary) and **PE-6a** (context); assumption A1 |
| BA-3 | Provenance in the requirement; reference_version stored (NFR-075) | **Accepted**: FR-170.R1, NFR-075.1-.2 |
| BA-4 | Split each pattern by data source; Ready only for QT or FT | **Accepted (rule)**: breakdown header |
| BA-5 | "Verification data" column so synthetic runs cannot count as pro evidence | **Accepted (rule)**: scorecard honesty rule and Evidence requirement |
| BA-6 | Reference the open Sprint 5 PRs; no Ready verdict on stories depending on #238/#239 before they merge | **Accepted (rule)**: E1 covers it |

### principal-engineer
| # | Change | Decision |
|---|---|---|
| PE-1 | Close Sprint 5 first; CI PRs first | **Accepted (rule)**: wave 0 order (§3.1) |
| PE-2 | S6/S7 reorder as a PO question, not a decision | **Accepted → EM-ESC-06** (P21) with the PE's options and costs |
| PE-3 | Every new gate a ticket (pattern lint, provenance, licence, eval report) | **Accepted**: ST-170a, ST-175a, ST-175b, ST-176a, CI-DOC-CHECK-06 |
| PE-4 | Close the pending ADR 0015 review | **Accepted → PE-6b** (with security-privacy-engineer) |
| PE-5 | Keep new code pure and portable; spike code disposable | **Accepted (rule)**: no new framework; spike code under a non-product path named in the port ADR |

### principal-designer
| # | Change | Decision |
|---|---|---|
| PD-1 | Decider cells as scheduled steps, or carried by each decider's review | **Accepted → DR-06**: one dated step per decider, the cell carried by that decider's review on the PD-6 PR |
| PD-2 | Make the design gate block in CI | **Deferred** to RETRO-06 with the sre-devops-engineer (judgment: one more gate on top of CI-TIERS-06 risks the WIP); the interim rule is that UI tickets `depends_on` DR-06 |
| PD-3 | Settle Sprint 5 design debt (PD-5 #201, D1, PD-DR04-01..03) | **Accepted**: #201 in the drain; D1 and the PD-DR04 tickets **routed to the PO** in EM-ESC-06 |
| PD-4 | Copy never claims more than measured; source column | **Accepted → PD-6** copy register; FR-170.R5 |
| PD-5 | A deferred design gets a ledger row and ticket the same day | **Accepted (rule)**: DoD author-found gaps row |

### senior-backend-engineer
| # | Change | Decision |
|---|---|---|
| BE-1 | Close Sprint 5 before features | **Accepted (rule)**: E1 |
| BE-2 | Contract ADR before pattern code; use AN ids | **Accepted → PE-6a**; FR-171 uses AN-08/09/13 |
| BE-3 | Full Tag first, coordinate patterns stay spikes | **Accepted**: ST-171b/c (FT), AN-11/12/16 in NFR-006.8 |
| BE-4 | One ticket per rule, ≈ 100 production lines | **Accepted (rule)**: §3.3 sizes |
| BE-5 | Follow-up cells (coach definition, SEC review) as dated tickets | **Accepted**: COACH-6a/6b, SEC-6, PE-6b |
| BE-6 | Read-cost IT from day one; snapshot not recompute | **Accepted**: NFR-010.12, ST-171e |

### senior-frontend-engineer
| # | Change | Decision |
|---|---|---|
| FE-1 | Finish #218 and #226 first | **Accepted (rule)**: in the drain |
| FE-2 | "Approved but conflicted" rule | **Accepted (rule)**: sprint-06 §3.6 item 3 |
| FE-3 | TCR row in the first push | **Accepted (rule)**: ST-174b acceptance; DoD |
| FE-4 | No weakness-view UI before PD-6 and DR-06 | **Accepted**: ST-170c, ST-172c, ST-173d depend on DR-06 |
| FE-5 | Contract test first, agreed with the backend | **Accepted**: contract tests in ST-170b and ST-172b, before the UI tickets |
| FE-6 | Run every E2E in each flag configuration it measures | **Accepted**: DEMO-6.4, G06-05 runs flags on and off |
| FE-7 | Document the local Playwright setup once in testing-strategy.md | **Deferred** to QA-PIN-06 (senior-qa-engineer, by 2026-11-24): one section, no new ticket |

### senior-ml-cv-engineer
| # | Change | Decision |
|---|---|---|
| ML-1 | Dry-run every eval and pattern method before claims | **Accepted (rule)**: scorecard §6 |
| ML-2 | `docs/evals/` (planned) and a report template | **Accepted → ST-176a** |
| ML-3 | Close ADR 0015 reviews | **Accepted → PE-6b** |
| ML-4 | Reference library as versioned, linted content with a CI check binding coach and ML | **Accepted → ST-170a**, COACH-6c, CI-DOC-CHECK-06 |
| ML-5 | "Computed correctly" vs "accurate on video" split | **Accepted (rule)**: FR-171 (computed) vs NFR-006.7-.9 (video) |
| ML-6 | Start the ML critical path on day 1 in parallel | **Accepted**: ML-6 in wave 1; ST-171b/c depend only on ST-171a and COACH-6b |

### senior-qa-engineer
| # | Change | Decision |
|---|---|---|
| QA-1 | Finish Sprint 5 first; reconcile the 2 blockers; the plan PR is not a Sprint 5 close | **Accepted (rule)**: E1; this PR closes nothing of Sprint 5 |
| QA-2 | Dry-run rows at planning | **Accepted in part**: three planning dry-runs logged (§6); rows for tools not yet built are merge conditions of their tickets (the plan cannot run a tool that does not exist) |
| QA-3 | Eval-set authorship separate from implementation | **Accepted → QA-REF-GOLD**, before ST-171b/c and ST-172a |
| QA-4 | "Configurations exercised" and "data provenance" lines in QA verdicts | **Accepted (rule)**: sprint-06 §8 item 6 |
| QA-5 | pr-policy fails when the cost table is missing | **Accepted → CI-DOC-CHECK-06** (PRC-11.3); dry-run evidence: 9 of 39 Sprint 5 tickets had one |

### security-privacy-engineer
| # | Change | Decision |
|---|---|---|
| SEC-1 | Threat notes before any build lane | **Accepted → SEC-6** (tier 0: docs only; the checker already exists) |
| SEC-2 | Footage provenance record as a DoR line and a fail-closed ingest gate | **Accepted → PE-6b, ST-175a**; the DoR line is added by BA-6 |
| SEC-3 | Licence checks over weights and datasets | **Accepted → ST-175b** |
| SEC-4 | R-05, R-11, DC-4, DC-1 as Sprint 6 tickets | **Accepted**: SEC-R05, SEC-R11 (P2); DC-4 and DC-1 decided in SEC-6 |
| SEC-5 | Re-ask P19 with a dated default; no deployment beyond localhost | **Accepted → EM-ESC-06** |
| SEC-6 | Reconcile SEC-S5-TM-01/02 before the Sprint 5 close | **Accepted (rule)**: part of the drain, before VERIFY-05 |

### sre-devops-engineer
| # | Change | Decision |
|---|---|---|
| SRE-1 | Close Sprint 5 first | **Accepted (rule)**: E1 |
| SRE-2 | Scheduled runs part of CI FIRST | **Accepted → CI-SCHEDULED-RED** (`ci_fix`) |
| SRE-3 | Disk budget for video | **Accepted → OPS-DISK-06** |
| SRE-4 | Cost per PR as a CI artefact (CI minutes from the actions API) | **Deferred**: `flow_metrics.py` already reports CI minutes per PR (1295.9 min in Sprint 5); the per-PR artefact is reviewed at RETRO-06 (engineering-manager) |
| SRE-5 | Every new gate gets a ticket | **Accepted**: same as PE-3. CI-VIDEO-JOB and OBS-VIDEO are **Rejected for this sprint**: no video stage is built in Sprint 6, so a video CI job would run nothing (reconsider at S8 planning when P11 footage exists) |

### pickleball-domain-coach
| # | Change | Decision |
|---|---|---|
| COACH-1 | Provenance on every value, library version and lock; "provisional reference" copy | **Accepted → ST-170a, COACH-6c**; FR-170.R5 |
| COACH-2 | Operational definitions before build, with the BA | **Accepted → COACH-6a** (wave 1), BA-6 |
| COACH-3 | Ranking ADR, not a stretched catalogue v0.1 | **Accepted → PE-6a** (ADR 0061), assumption A4 |
| COACH-4 | Level-banded references; pro-only = direction | **Accepted**: FR-172.R3, assumption A2 |
| COACH-5 | Reproduction script output with every domain rule | **Accepted → COACH-6b** (`pattern_example.py --check`) |
| COACH-6 | Extend drill coverage to the new targets | **Accepted → ST-173b, ST-173c** |

**Totals:** 69 change items from 12 roles, each with a decision: 65 accepted as a ticket or a rule (QA-2 in part, EM-6 with a note), 5 of them also carrying a PO question routed through EM-ESC-06 (EM-3, PE-2, PM-2, PD-3, SEC-5); 3 deferred with an owner and a date (PD-2, FE-7, SRE-4); 1 rejected for this sprint with a reason (SRE-5: its "gate per ticket" part is already PE-3; the video CI job and OBS-VIDEO it proposes are rejected because no video stage is built this sprint).

## 3. Lessons stated at kickoff (each maps to a ticket or rule)

| Lesson | Root cause | Sprint 6 ticket or rule |
|---|---|---|
| A task with no slot in the workflow does not run (retro 3 M2/M6/M13, retro 4 M5/M7) | rules without workflow steps | every gate a ticket; DR-06 decider steps; QA-WIP-GATE |
| Starting the next phase before the build merged throws work away (retro 4 M1) | phases on a schedule, not a condition | E1; VERIFY-06 after the last build merge |
| A method without a live dry-run measures nothing (retro 4 M2, M10, M12) | harness against stubs | scorecard §6, planted failures, QA-PIN-06 |
| An author-found gap is a finding (retro 4 M3) | decisions files not joined to the ledger | FR-173.R1/R3, DoD gap row |
| Size waivers when slicing follows the build (retro 3 M11, retro 4 M4) | slicing after code | one rule per ticket at planning |
| CI depends on a session (retro 4 M6); scheduled reds unseen | notice skipped on push | CI-SCHEDULED-RED |
| Agent text is not PO text (retro 3 M7) | no separation rule | addendum quote vs "not a PO decision" note |
| Design review never held three sprints running | decider cells depend on other roles' commits | DR-06 steps |
| Copy ahead of evidence (QA-PD5-F6) | copy from intent, not measurement | copy register source column; FR-170.R5 |
| Approved PRs go stale (#218) | nobody owns mergeability after APPROVE | §3.6 item 3 |
| Comparison rules without worked numbers (ADR 0060 first draft) | no numeric examples | every FR-172 rule has numeric Examples |
| Coach rule stated from counting, not from the code (COACH-5) | no reproduction script | COACH-6b |
| Read paths re-projected per request (#232) | read cost untested | NFR-010.12 |

## 4. Risks raised (consolidated) → sprint-06 §10.

## 5. Open PO questions carried into EM-ESC-06

1. **P21:** confirm Sprint 6 = video analysis and the Go port in Sprint 7 (options: port first; tag-based slice first then port (default); strangler port alongside), with the Python growth each option causes.
2. **"..."** in the PO's list: what else besides training and pro matches?
3. **P22:** may the reference library cite published secondary statistics (default: yes, only when the citation resolves, labelled "published source")?
4. Should players ever run Full Tag on their own videos (FR-150 says labeller-only; default: no, A3)?
5. **P11** footage with rights and consent; **P15** coach verification; **P16** legal review incl. pose data and derived statistics; **P7** and **P19** re-asked (need-by dates passed); **D1** DR-04 hold or waiver and the PD-DR04-01..03 tickets.
