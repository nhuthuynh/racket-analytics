# Sprint 4 decision log

Small decisions, one dated row each (who, decision, evidence, reasoning). Append only; do not rewrite other rows. Significant decisions go to `docs/decisions/` as ADRs.

In Sprint 4 each ticket wrote its own small decisions in `decisions/<TICKET-ID>.md`, so that parallel PRs did not conflict (sprint-04 header). Only RETRO-04 consolidates them. To keep each decision in one place, this file does not copy their rows. It gives (1) an index of the per-ticket files and (2) the sprint-level decisions of the engineering-manager at the close.

## 1. Index of the per-ticket decision files (77 files; rows = dated rows in the file)

| File | PR | Rows |
|---|---|---|
| [ADR-0053-0049](decisions/ADR-0053-0049.md) | #171 | 8 |
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
| [EM-PR27-01](decisions/EM-PR27-01.md) | #170 | 3 |
| [EM-RETRO04-02](decisions/EM-RETRO04-02.md) | #176 | 8 |
| [FIX-04-4a](decisions/FIX-04-4a.md) | #179 | 4 |
| [PD-4](decisions/PD-4.md) | #88 | 15 |
| [PD-4b](decisions/PD-4b.md) | #114 | 7 |
| [PE-4](decisions/PE-4.md) | #89 | 18 |
| [PLAN-04](decisions/PLAN-04.md) | #87 | 13 |
| [PM-4](decisions/PM-4.md) | #93 | 7 |
| [QA-HARNESS-4a](decisions/QA-HARNESS-4a.md) | #103 | 15 |
| [QA-HARNESS-4b](decisions/QA-HARNESS-4b.md) | #105 | 16 |
| [QA-VERIFY04R3-01](decisions/QA-VERIFY04R3-01.md) | #166 | 20 |
| [QA-VERIFY04R3-02-08](decisions/QA-VERIFY04R3-02-08.md) | #165 | 5 |
| [QA-VERIFY04R3-03](decisions/QA-VERIFY04R3-03.md) | #163 | 9 |
| [QA-VERIFY04R3-04](decisions/QA-VERIFY04R3-04.md) | #168 | 7 |
| [QA-VERIFY04R3-05-06](decisions/QA-VERIFY04R3-05-06.md) | #164 | 6 |
| [QA-VERIFY04R3-07](decisions/QA-VERIFY04R3-07.md) | #172 | 7 |
| [QA-VERIFY04R3-09](decisions/QA-VERIFY04R3-09.md) | #169 | 11 |
| [RETRO-04](decisions/RETRO-04.md) | #161, #175 and this PR (third close) | 29 |
| [SEC-4](decisions/SEC-4.md) | #90 | 7 |
| [SMOKE-04](decisions/SMOKE-04.md) | #159 (folded into RETRO-04) | 4 |
| [SMOKE-04-r2](decisions/SMOKE-04-r2.md) | #174 (folded into RETRO-04, second close) | 5 |
| [SMOKE-04-r3](decisions/SMOKE-04-r3.md) | #177 (folded into RETRO-04, third close) | 6 |
| [SRE-VERIFY04R3-01](decisions/SRE-VERIFY04R3-01.md) | #167 | 6 |
| [SRE-VERIFY04R3-02](decisions/SRE-VERIFY04R3-02.md) | #162 | 5 |
| [SRE-VERIFY04R3-03](decisions/SRE-VERIFY04R3-03.md) | #173 | 11 |
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
| [ST-062](decisions/ST-062.md) | #124 | 9 |
| [ST-062-part2](decisions/ST-062-part2.md) | #128 | 15 |
| [ST-063a](decisions/ST-063a.md) | #123 | 12 |
| [ST-063b](decisions/ST-063b.md) | #125 | 12 |
| [ST-063b-part2](decisions/ST-063b-part2.md) | #129 | 3 |
| [ST-063b-part2-part2](decisions/ST-063b-part2-part2.md) | #132 | 3 |
| [ST-063c](decisions/ST-063c.md) | #139 | 6 |
| [ST-063c-outbox-ui](decisions/ST-063c-outbox-ui.md) | #146 | 8 |
| [ST-063c-part2](decisions/ST-063c-part2.md) | #140 | 8 |
| [ST-063c-part2-part2](decisions/ST-063c-part2-part2.md) | #141 | 9 |
| [ST-063c-swap-ui](decisions/ST-063c-swap-ui.md) | #145 | 8 |
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
| [ST-072b](decisions/ST-072b.md) | #156 | 10 |
| [ST-072b-part2](decisions/ST-072b-part2.md) | #157 | 4 |
| [ST-073](decisions/ST-073.md) | #104 | 11 |
| [VERIFY-04-r3](decisions/VERIFY-04-r3.md) | #160 (folded into RETRO-04) | 15 |
| [VERIFY-04-r4](decisions/VERIFY-04-r4.md) | #178 (folded into RETRO-04, third close) | 15 |

Count: `ls docs/sprints/04/decisions | wc -l` → 60 with `RETRO-04.md` at the first close; **73** at the second close (2026-10-30), after the 12 fix-wave files and `SMOKE-04-r2.md`. **77** at the third close (2026-10-30), after `EM-RETRO04-02.md`, `FIX-04-4a.md`, `SMOKE-04-r3.md` and `VERIFY-04-r4.md`. ST-063c-part2-part2-part2 (#142, #144) has no file on `main` (its branches were never merged); its rebuild, #145, refers to it in `ST-063c-swap-ui.md`.

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

## 3. Sprint-level decisions at the second close (engineering-manager, RETRO-04, 2026-10-30, at `origin/main` `d48f19a3`)

| Date | Who | Decision | Evidence | Reasoning |
|---|---|---|---|---|
| 2026-10-30 | engineering-manager | **The goal of record stays "not met, 2 of 12"** although SMOKE-04-r2 is green at `d48f19a3` | `smoke.md` top section; no VERIFY PR at `d48f19a3` (`list_pull_requests state=all`, #174 is the last) | PO rule: a goal counts only when a verifier measures it live with the full method. A smoke runs one pass (ADR 0055) |
| 2026-10-30 | engineering-manager | **SMOKE-04-r2 (#174) is folded into RETRO-04**: its branch is merged into this PR unchanged (`6184b023`), and #174 is closed with a pointer | `git merge-base --is-ancestor origin/s04/smoke-04-r2-integration-smoke-of-main-d48f19a HEAD` → rc 0 | ADR 0055 rule 3: evidence lands on `main`. One review instead of two for evidence that does not change |
| 2026-10-30 | engineering-manager | **Fixed rows written for SRE-VERIFY04R3-02, QA-VERIFY04R3-04, -05, -06 and EM-RETRO04-01.** Their fixes merged (#162, #168, #164; #144 closed) without a closing row. SRE-VERIFY04R3-02 carries the residual "config level only" | `open_defects.py` both ledgers: open 4 → 0; `reconcile_due.py … --base HEAD` → 0 due | ADR 0037 rule 1. The evidence is the fix PR's own live dry-run plus SMOKE-04-r2 |
| 2026-10-30 | engineering-manager | **DoD-done is 48 of 48 units (1.00) at the second close**, from 35 at the first. Every major traced to a ticket in report §3 is Fixed | `status.json` `totals`, `second_close.first_close` | Same rule as the first close, applied to the ledger now (judgment) |
| 2026-10-30 | engineering-manager | **No new ADR.** Retro action D3 (run `reconcile_due.py` in `pr-policy` on each ticket PR) enforces ADR 0033 rule 1. L17 (close after the fix wave and VERIFY) is an ordering choice for the Sprint 5 plan | retro §10 | A check that enforces an existing rule needs no new decision record (judgment) |
| 2026-10-30 | engineering-manager | **Not decided here:** the G04-05 (e) TCR row stays with the senior-qa-engineer (retro D2). No PR is merged and no label is set | `test-change-requests.md` row 21 "pending (senior-qa-engineer)" | Separation of duties (orchestrator, 2026-10-09); ADR 0014 |
| 2026-10-30 | engineering-manager | **Review round 1 of PR #175: QA-RETRO04R2-01 accepted; ledger row EM-RETRO04-02 (major, Open, senior-qa-engineer) written.** TCR row 20 (the E2E-04-04 change merged in #166) has no QA decision. Open blocker/major is now 1 | `open_defects.py` both ledgers → rc 1, `open 1`; `decisions/RETRO-04.md` "Review round 1" | An accepted test changed on `main` without a QA decision (ADR 0014). Only QA decides the row (retro D2) |
| 2026-10-30 | engineering-manager | **Review round 1 of PR #175: QA-RETRO04R2-02 accepted; the G04-03 (c) method line of TCR row 23 is applied to `goal-scorecard.md` §4** (`HYPOTHESIS_PROFILE=ci uv run pytest -q -m plan_property --hypothesis-show-statistics`) | dry run → `1000 passing, 0 failing`, `1 passed`; default profile → `100 passing` | Since #173 the default profile draws 100 examples, under the ≥ 1,000 target; TCR row 23 assigned the edit to this consolidation |

## 4. Sprint-level decisions at the third close (engineering-manager, RETRO-04, 2026-10-30, at `origin/main` `22ca756c`)

| Date | Who | Decision | Evidence | Reasoning |
|---|---|---|---|---|
| 2026-10-30 | engineering-manager | **Third close: VERIFY-04-r4 (#178) is the measurement of record: 11 of 12, the Sprint 4 goal is not met.** FIX-04-4a's live 388.1 s for G04-11 (d) is shown in the report but not counted as "met": the G04-11 row stays VERIFY's to re-measure (retro E1, VERIFY-04-r5) | `goal-scorecard.md` §2 (VERIFY-04-r4); `decisions/FIX-04-4a.md` row 4 | PO rule: a goal counts only when measured live by the verification round; the EM does not score rows (separation of duties) |
| 2026-10-30 | engineering-manager | **VERIFY-04-r4 (#178) and SMOKE-04-r3 (#177) folded into RETRO-04** by merging their branches unchanged (`379ee61e`, `ae3f5926`); both PRs closed with a pointer | `git merge-base --is-ancestor origin/s04/verify-04-r4-sprint-4-goal-verification-round-4 HEAD` → rc 0; same for the SMOKE-04-r3 branch | ADR 0055 rule 3 |
| 2026-10-30 | engineering-manager | **Ledger: QA-VERIFY04R4-01 (alias VERIFY04R4-01) written Open, then Fixed by FIX-04-4a (#179);** round-1 minors and nits of #175 Fixed. Open blocker/major stays 0 | `open_defects.py` both ledgers → rc 0, `open 0`; with the Fixed row removed → `open 1` | ADR 0037 rule 1; the alias is needed for `measurelib._FINDING_ID` (retro M15) |
| 2026-10-30 | engineering-manager | **TCR row 21's scoped G04-05 (e) method applied to `goal-scorecard.md` §4** (accepted in #176; VERIFY-04-r4 asked the consolidation to apply it) | scoped command at `22ca756c` → empty, rc 0 | Same as TCR row 23 at the second close: the consolidation applies accepted method rows |
| 2026-10-30 | engineering-manager | **No new ADR** for E3-E5 (tooling for ADR 0037/0033 rules, ADR 0055 rule 2, Sprint 5 order). E5 becomes an ADR if a sprint needs more than one close again | retro §11 "Process changes" | Judgment: the rules exist, the gap is enforcement |

