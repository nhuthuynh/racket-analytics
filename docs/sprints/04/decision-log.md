# Sprint 4 decision log

Small decisions, one dated row each (who, decision, evidence, reasoning). Append only; do not rewrite other rows. Significant decisions go to `docs/decisions/` as ADRs.

In Sprint 4 each ticket wrote its own small decisions in `decisions/<TICKET-ID>.md`, so that parallel PRs did not conflict (sprint-04 header). Only RETRO-04 consolidates them. To keep each decision in one place, this file does not copy their rows. It gives (1) an index of the per-ticket files and (2) the sprint-level decisions of the engineering-manager at the close.

## 1. Index of the per-ticket decision files (59 files; rows = dated rows in the file)

| File | PR | Rows |
|---|---|---|
| [C4-CA](decisions/C4-CA.md) | #95 | 5 |
| [C4-G12](decisions/C4-G12.md) | #92 | 4 |
| [C4-LOCUST](decisions/C4-LOCUST.md) | #96 | 10 |
| [C4-RECON](decisions/C4-RECON.md) | #98 | 14 |
| [C4-RED](decisions/C4-RED.md) | #97 | 4 |
| [C4-TAC5](decisions/C4-TAC5.md) | #94 | 10 |
| [CI-CERTIFI-ADVISORY](decisions/CI-CERTIFI-ADVISORY.md) | #148 | 0 |
| [CI-DAILY-AUDIT](decisions/CI-DAILY-AUDIT.md) | #150 | 10 |
| [CI-DRAFT-SKIP](decisions/CI-DRAFT-SKIP.md) | #122 | 4 |
| [CI-INFRA-BUDGET](decisions/CI-INFRA-BUDGET.md) | #158 | 0 |
| [CI-OBJSTORE-PORT-RACE](decisions/CI-OBJSTORE-PORT-RACE.md) | #155 | 8 |
| [CI-OTEL-ADVISORY](decisions/CI-OTEL-ADVISORY.md) | #149 | 0 |
| [CI-SIGNIN-HYDRATION](decisions/CI-SIGNIN-HYDRATION.md) | #106 | 4 |
| [CI-SIZE-PROD-ONLY](decisions/CI-SIZE-PROD-ONLY.md) | #151 | 10 |
| [COACH-4](decisions/COACH-4.md) | #91 | 8 |
| [PD-4](decisions/PD-4.md) | #88 | 15 |
| [PD-4b](decisions/PD-4b.md) | #114 | 7 |
| [PE-4](decisions/PE-4.md) | #89 | 18 |
| [PLAN-04](decisions/PLAN-04.md) | #87 | 13 |
| [PM-4](decisions/PM-4.md) | #93 | 7 |
| [QA-HARNESS-4a](decisions/QA-HARNESS-4a.md) | #103 | 15 |
| [QA-HARNESS-4b](decisions/QA-HARNESS-4b.md) | #105 | 16 |
| [SEC-4](decisions/SEC-4.md) | #90 | 7 |
| [SMOKE-04](decisions/SMOKE-04.md) | #159 (folded into RETRO-04) | 4 |
| [ST-055](decisions/ST-055.md) | #100 | 16 |
| [ST-056](decisions/ST-056.md) | #102 | 17 |
| [ST-057](decisions/ST-057.md) | #108 | 11 |
| [ST-058a](decisions/ST-058a.md) | #101 | 6 |
| [ST-058b](decisions/ST-058b.md) | #107 | 8 |
| [ST-058c](decisions/ST-058c.md) | #110 | 12 |
| [ST-059](decisions/ST-059.md) | #112 | 9 |
| [ST-060](decisions/ST-060.md) | #113 | 10 |
| [ST-061a](decisions/ST-061a.md) | #109 | 11 |
| [ST-061b](decisions/ST-061b.md) | #111 | 25 |
| [ST-062-part2](decisions/ST-062-part2.md) | #128 | 15 |
| [ST-062](decisions/ST-062.md) | #124 | 9 |
| [ST-063a](decisions/ST-063a.md) | #123 | 12 |
| [ST-063b-part2-part2](decisions/ST-063b-part2-part2.md) | #132 | 3 |
| [ST-063b-part2](decisions/ST-063b-part2.md) | #129 | 3 |
| [ST-063b](decisions/ST-063b.md) | #125 | 12 |
| [ST-063c-outbox-ui](decisions/ST-063c-outbox-ui.md) | #146 | 8 |
| [ST-063c-part2-part2](decisions/ST-063c-part2-part2.md) | #141 | 9 |
| [ST-063c-part2](decisions/ST-063c-part2.md) | #140 | 8 |
| [ST-063c-swap-ui](decisions/ST-063c-swap-ui.md) | #145 | 8 |
| [ST-063c](decisions/ST-063c.md) | #139 | 6 |
| [ST-064](decisions/ST-064.md) | #126 | 5 |
| [ST-065](decisions/ST-065.md) | #152 | 11 |
| [ST-066](decisions/ST-066.md) | #147 | 4 |
| [ST-067](decisions/ST-067.md) | #99 | 5 |
| [ST-068a](decisions/ST-068a.md) | #127 | 14 |
| [ST-068b](decisions/ST-068b.md) | #153 | 10 |
| [ST-069](decisions/ST-069.md) | #131 | 12 |
| [ST-070](decisions/ST-070.md) | #133 | 10 |
| [ST-071](decisions/ST-071.md) | #154 | 13 |
| [ST-072a](decisions/ST-072a.md) | #130 | 9 |
| [ST-072b-part2](decisions/ST-072b-part2.md) | #157 | 4 |
| [ST-072b](decisions/ST-072b.md) | #156 | 10 |
| [ST-073](decisions/ST-073.md) | #104 | 11 |
| [VERIFY-04-r3](decisions/VERIFY-04-r3.md) | #160 (folded into RETRO-04) | 15 |

Count: `ls docs/sprints/04/decisions | wc -l` → 60 with `RETRO-04.md`. ST-063c-part2-part2-part2 (#142, #144) has no file on `main` (its branches were never merged); its rebuild, #145, refers to it in `ST-063c-swap-ui.md`.

## 2. Sprint-level decisions at the close (engineering-manager, RETRO-04)

| Date | Who | Decision | Evidence | Reasoning |
|---|---|---|---|---|
| 2026-10-29 | engineering-manager | **The Sprint 4 goal is not met: 2 of 12 metrics met live** (G04-04, G04-06). VERIFY-04-r3 is the measurement of record; SMOKE-04 agrees on every row they share | `goal-scorecard.md` §2; `smoke.md` | PO standing rule: a goal is met only when measured live |
| 2026-10-29 | engineering-manager | **SMOKE-04 (#159) and VERIFY-04-r3 (#160) are folded into RETRO-04 by merging their branches unchanged** (`6f7a711`, `823d70f`), then both PRs are closed with a pointer | `git merge-base --is-ancestor origin/s04/verify-04-r3 HEAD` → rc 0 (same for the smoke branch) | ADR 0050 rule 4: the results reach `main` before the next round. Merging the commits keeps the verifiers' authorship and avoids two reviews of evidence that does not change |
| 2026-10-29 | engineering-manager | **Ledger triage rule (judgment): a finding that by itself keeps a goal row at "no" is major**, whether the cause is product, content, harness, method or configuration. 12 Sprint 4 majors and 2 minors are written | `review-rounds.md` "Ticket RETRO-04"; `open_defects.py` both ledgers → `open 13` | Counting harness defects as minor would report the goal as nearly met while it is not shown. The principal-engineer may re-triage |
| 2026-10-29 | engineering-manager | **PD-R1S3-01 group Fixed** in the Sprint 3 ledger (the chair's DR-03 "Held" record, C4-G12 #92). EM-PR27-01 stays Open | `sed -n 292p docs/design/flows-sprint-03.md`; `merged_verdict.py --pr 27 …` rc 1 | The fix exists; the EM row was missing. The PR #27 verdict needs the senior-backend-engineer |
| 2026-10-29 | engineering-manager | **DoD-done counts a ticket only if no open major is traced to it:** 35 of 48 units | `sprint-report.md` §3 | A merged ticket whose behaviour fails live does not meet the sprint's "done" (judgment) |
| 2026-10-29 | engineering-manager | **ADR 0055 accepted** (verification only after the build is merged; live dry-run per method in its own configuration; evidence PRs never closed unmerged; env-to-Compose parity) | retro 4 M1, M2 | Repeated miss (retro 3 M9); 5 of 10 misses (and part of G04-11) were method or configuration defects |
| 2026-10-29 | engineering-manager | **Retro file name `docs/retros/2026-12-11-sprint-04.md`**, not `docs/retros/sprint-04.md` as the ticket brief says | sprint-04 header and §13; `ls docs/retros` | Matches the plan and retros 0-3 (judgment) |
| 2026-10-29 | engineering-manager | **Load factor stays 0.8.** Implemented ratio 1.00; DoD-done 0.73. Sprint 5 reserves about 12 units for the fix wave (retro C2) before any feature | `status.json` totals | ADR 0010; the misses are fix work, not lost capacity |
