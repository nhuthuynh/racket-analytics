# Sprint 4 progress

- **Owner:** engineering-manager. Machine-readable status: [`status.json`](status.json) (ADR 0010 units; `implemented_units` and `dod_done_units` tracked separately).
- **Plan:** [`../sprint-04.md`](../sprint-04.md). **Goal scorecard:** [`goal-scorecard.md`](goal-scorecard.md). **Report:** [`sprint-report.md`](sprint-report.md). **Retro:** [`../../retros/2026-12-11-sprint-04.md`](../../retros/2026-12-11-sprint-04.md).
- **Delivery:** one PR per ticket into `main` (ADR 0039), merged only by the gated merge step through `merge_ready.py` (ADR 0050). No sprint branch. This file was created by RETRO-04 at the close (ticket PRs do not edit it).

## Timeline (UTC; from GitHub REST and the decision files)

| Date | What happened | Evidence |
|---|---|---|
| 2026-10-17 | Planning (PLAN-04 #87, merged 11:22). CI green on `main` (run 39015002522). Gate tickets PE-4, SEC-4, COACH-4, PM-4, C4-G12 and the carry-over C4-* merged by 14:52. First build wave: ST-055..ST-058c, ST-061a, ST-067, ST-073, QA-HARNESS-4a/b, CI-SIGNIN-HYDRATION, C4-RED (the `Red:` check). 23 merges | #87, #89-#110 |
| 2026-10-18 | PD-4 (00:47), ST-059, ST-060, PD-4b, CI-DRAFT-SKIP; plan API ST-061b; plan UI ST-063a/b; done/swap API ST-062 (+ part 2); privacy and quota APIs ST-068a, ST-069, ST-070, ST-072a; `make demo` plan ST-064. 20 merges. Verification rounds 1 (`3c4be05`, 1/12) and 2 (`09d279d`, 2/12) ran early and were closed unmerged with their smoke and FIX PRs (retro M1) | #88, #111-#114, #122-#133, #139-#141; closed #115-#121, #134-#138 |
| 2026-10-19 | ST-063c slices rebuilt red-first after the `Red:` check failed the split PRs (#142, #143): swap UI #145, outbox UI #146. ST-066 opened | #145, #146 |
| 2026-10-19 → 10-28 | No agent session. `main` scheduled CI red from 2026-10-21 (certifi advisory; fixed by #148 on 10-22) and again 2026-10-23..28 (opentelemetry-api, next advisories) | `actions/runs` schedule failures (report §4) |
| 2026-10-28 | PO: PR size counts production code only (ADR 0054) | `po-input-2026-10-05.md` addendum |
| 2026-10-29 | CI-OTEL-ADVISORY #149 (`main` green again 09:07); CI-DAILY-AUDIT #150; CI-OBJSTORE-PORT-RACE #155; CI-SIZE-PROD-ONLY #151; CI-INFRA-BUDGET #158; ST-066, ST-068b, ST-071, ST-072b (+ part 2); ST-065 (#152, last ticket, 17:48). SMOKE-04 (#159) and VERIFY-04-r3 (#160) at `b9d0dc3`: met 2 of 12. RETRO-04 | #147-#160 |

## Close status (2026-10-29, `b9d0dc3`)

| Item | Result | Evidence |
|---|---|---|
| Goal | **Not met**: 2 of 12 live (G04-04, G04-06) | `goal-scorecard.md` §2 |
| Units | 48 committed / 48 implemented / 35 DoD-done | `status.json` totals |
| PRs | 57 merged, all with both verdicts on the merged head and `ci-gate` green | `merged_verdict.py` rc 0 ×57 |
| Open blocker/major | 13 (EM-PR27-01 + 12 Sprint 4) | `open_defects.py docs/sprints/03/review-rounds.md docs/sprints/04/review-rounds.md` → rc 1, `open 13` |
| CI on `main` | green | run 40924867330 |
| Next | Retro action C2: fix wave for the 13 majors, then VERIFY-04-r4 under ADR 0055 | retro §8 |
